#!/usr/bin/env python3
"""End-to-end offline browser test for ipc-kit.html using Firefox WebDriver BiDi.

Launches headless Firefox against the local file:// URL with no network server,
drives the real DOM via WebDriver BiDi over a local WebSocket (stdlib only),
and verifies:
  1. Fresh offline launch from file://
  2. 5-minute practice questions (overlapping moments, missed action, small sample)
  3. Zero observations ("No observations")
  4. Tally screen with overlapping moments (M1+M4 = 1 opportunity), missed action,
     "8 of 10 opportunities, 80%", and combining with paper entry by summing counts
  5. Stock workflow: receipts, FEFO earliest-expiry first, expiring-soon alert,
     reorder point alert, expired stock excluded from usable totals, stockout,
     physical count, and coded adjustment
  6. Backup creation, browser reopen persistence, invalid backup leaving existing
     data intact, and valid backup full restore
"""

import base64
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
HTML_PATH = os.path.join(ROOT, "ipc-kit.html")
WORK_DIR = os.path.join(HERE, ".work")


class BiDiClient:
    """Minimal WebDriver BiDi client using only the Python standard library."""

    def __init__(self, port):
        self.sock = socket.create_connection(("127.0.0.1", port), timeout=15)
        self.sock.settimeout(15)
        req = (
            "GET /session HTTP/1.1\r\n"
            "Host: 127.0.0.1:%d\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n" % port
        )
        self.sock.sendall(req.encode("ascii"))
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise RuntimeError("WebSocket handshake failed")
            buf += chunk
        self._buf = buf.split(b"\r\n\r\n", 1)[1]
        self._next_id = 1

    def _recv_exact(self, n):
        while len(self._buf) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise RuntimeError("Socket closed while reading frame")
            self._buf += chunk
        out, self._buf = self._buf[:n], self._buf[n:]
        return out

    def _read_frame(self):
        b1, b2 = self._recv_exact(2)
        opcode = b1 & 0x0F
        masked = (b2 & 0x80) != 0
        length = b2 & 0x7F
        if length == 126:
            length = struct.unpack(">H", self._recv_exact(2))[0]
        elif length == 127:
            length = struct.unpack(">Q", self._recv_exact(8))[0]
        mask = self._recv_exact(4) if masked else b""
        payload = self._recv_exact(length)
        if masked:
            payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        if opcode == 0x8:
            raise RuntimeError("WebSocket closed by browser")
        return payload.decode("utf-8", errors="replace")

    def _send_frame(self, text):
        data = text.encode("utf-8")
        header = bytearray([0x81])
        mask = b"\x12\x34\x56\x78"
        n = len(data)
        if n < 126:
            header.append(0x80 | n)
        elif n < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack(">H", n))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack(">Q", n))
        header.extend(mask)
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        self.sock.sendall(bytes(header) + masked)

    def call(self, method, params):
        cid = self._next_id
        self._next_id += 1
        self._send_frame(json.dumps({"id": cid, "method": method, "params": params}))
        while True:
            msg = json.loads(self._read_frame())
            if msg.get("id") == cid:
                if msg.get("type") == "error" or "error" in msg:
                    raise RuntimeError("BiDi error in %s: %s" % (method, msg))
                return msg.get("result", {})

    def eval_js(self, context_id, expression):
        res = self.call("script.evaluate", {
            "expression": expression,
            "target": {"context": context_id},
            "awaitPromise": True,
            "resultOwnership": "none"
        })
        if res.get("type") == "exception":
            raise RuntimeError("JS exception: %s" % json.dumps(res.get("exceptionDetails")))
        return self._decode_value(res.get("result", {}))

    def _decode_value(self, v):
        t = v.get("type")
        if t in ("undefined", "null"):
            return None
        if t in ("string", "number", "boolean"):
            return v.get("value")
        if t == "array":
            return [self._decode_value(x) for x in v.get("value", [])]
        if t == "object":
            return {k: self._decode_value(val) for k, val in v.get("value", [])}
        return v

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


class BrowserSession:
    def __init__(self, profile_dir, home_dir, port=9229):
        self.profile_dir = profile_dir
        self.home_dir = home_dir
        self.port = port
        self.proc = None
        self.bidi = None
        self.context = None

    def start(self):
        os.makedirs(self.profile_dir, exist_ok=True)
        os.makedirs(self.home_dir, exist_ok=True)
        env = os.environ.copy()
        env["HOME"] = self.home_dir
        cmd = [
            "firefox", "-headless", "-no-remote",
            "-profile", self.profile_dir,
            "--remote-debugging-port=%d" % self.port,
            "about:blank"
        ]
        self.proc = subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.time() + 20
        last_err = None
        while time.time() < deadline:
            try:
                self.bidi = BiDiClient(self.port)
                break
            except Exception as e:
                last_err = e
                time.sleep(0.4)
        if not self.bidi:
            self.stop()
            raise RuntimeError("Could not connect to Firefox BiDi: %s" % last_err)
        self.bidi.call("session.new", {"capabilities": {}})
        tree = self.bidi.call("browsingContext.getTree", {})
        self.context = tree["contexts"][0]["context"]

    def navigate_file(self, path):
        url = "file://" + os.path.abspath(path)
        self.bidi.call("browsingContext.navigate", {
            "context": self.context,
            "url": url,
            "wait": "complete"
        })

    def js(self, code):
        return self.bidi.eval_js(self.context, code)

    def stop(self):
        if self.bidi:
            try:
                self.bidi.call("browser.close", {})
            except Exception:
                pass
            self.bidi.close()
            self.bidi = None
        if self.proc:
            try:
                self.proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
            self.proc = None


class EndToEndBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prof = os.path.join(WORK_DIR, "e2e_prof")
        cls.home = os.path.join(WORK_DIR, "e2e_home")
        shutil.rmtree(cls.prof, ignore_errors=True)
        shutil.rmtree(cls.home, ignore_errors=True)

    def test_full_offline_workflow_and_reopen(self):
        # --- Session 1: fresh offline launch from file:// ---
        b = BrowserSession(self.prof, self.home, port=9231)
        try:
            b.start()
            b.navigate_file(HTML_PATH)

            # Pin test date so expiry calculations are deterministic
            b.js("window.__IPC_TEST_TODAY = '2026-11-07';")

            # 1. Verify Welcome screen on fresh launch & strict CSP
            info = b.js("""({
              protocol: location.protocol,
              hasWelcome: !!document.getElementById('btnStartPractice') && !!document.getElementById('btnStartReal'),
              csp: document.querySelector('meta[http-equiv="Content-Security-Policy"]').content
            })""")
            self.assertEqual(info["protocol"], "file:")
            self.assertTrue(info["hasWelcome"])
            self.assertIn("default-src 'none'", info["csp"])
            self.assertIn("connect-src 'none'", info["csp"])

            # 2. Start 5-minute practice run (fictional data)
            b.js("document.getElementById('btnStartPractice').click();")
            p_state = b.js("""({
              mode: window.__IPCApp.state.mode,
              badge: document.getElementById('modeBadge').textContent,
              saveOk: document.getElementById('saveStatus').classList.contains('ok'),
              items: window.__IPCApp.state.data.stock.items.length
            })""")
            self.assertEqual(p_state["mode"], "practice")
            self.assertIn("PRACTICE", p_state["badge"])
            self.assertTrue(p_state["saveOk"])
            self.assertEqual(p_state["items"], 5)

            # Complete all 6 practice questions and verify unanswered guard + score summary
            pq_res = b.js("""(() => {
              document.querySelector('[data-tab="hh"]').click();
              document.querySelector('[data-hhsub="practice"]').click();
              document.querySelector('.btn-pq-check[data-qid="1"]').click();
              const emptyErr = document.getElementById('pqErr1') ? document.getElementById('pqErr1').textContent : '';
              const stillUnchecked = !(window.__IPCApp.state.pqAnswers[1] && window.__IPCApp.state.pqAnswers[1].checked);
              const answers = [
                {id: 1, m: [1, 4], o: 'rub'},
                {id: 2, m: [2], o: 'missed'},
                {id: 3, m: [3], o: 'wash'},
                {id: 4, m: [5], o: 'missed'},
                {id: 5, mc: 'b'},
                {id: 6, mc: 'b'}
              ];
              for (const a of answers) {
                if (a.m) {
                  for (const m of a.m) {
                    const cb = document.querySelector(`.pq-m[data-qid="${a.id}"][value="${m}"]`);
                    cb.checked = true; cb.dispatchEvent(new Event('change'));
                  }
                  const rb = document.querySelector(`.pq-out[data-qid="${a.id}"][value="${a.o}"]`);
                  rb.checked = true; rb.dispatchEvent(new Event('change'));
                } else {
                  const rb = document.querySelector(`.pq-mc[data-qid="${a.id}"][value="${a.mc}"]`);
                  rb.checked = true; rb.dispatchEvent(new Event('change'));
                }
                document.querySelector(`.btn-pq-check[data-qid="${a.id}"]`).click();
              }
              return {
                emptyErr,
                stillUnchecked,
                scoreBar: document.getElementById('pqScoreBar') ? document.getElementById('pqScoreBar').textContent : '',
                quizDone: window.__IPCApp.state.practiceProgress.quizDone,
                allOk: Object.values(window.__IPCApp.state.pqAnswers).every(x => x.ok)
              };
            })()""")
            self.assertIn("Choose an answer first", pq_res["emptyErr"])
            self.assertTrue(pq_res["stillUnchecked"])
            self.assertIn("Score: 6 of 6", pq_res["scoreBar"])
            self.assertTrue(pq_res["quizDone"])
            self.assertTrue(pq_res["allOk"])

            # 3. Switch to Real Data mode, verify zero observations ("No observations")
            real_init = b.js("""(() => {
              document.querySelector('[data-tab="settings"]').click();
              document.getElementById('btnSwitchMode').click();
              // Add approved area codes OPD and MAT
              const addArea = (code) => {
                document.getElementById('newAreaCode').value = code;
                document.getElementById('btnAddArea').click();
              };
              addArea('OPD');
              addArea('MAT');
              document.querySelector('[data-tab="home"]').click();
              const homeZero = document.getElementById('homeHHResult').textContent;
              document.querySelector('[data-tab="hh"]').click();
              document.querySelector('[data-hhsub="results"]').click();
              const resZero = document.getElementById('hhOverallResult').textContent;
              return {
                mode: window.__IPCApp.state.mode,
                badge: document.getElementById('modeBadge').textContent,
                homeZero,
                resZero
              };
            })()""")
            self.assertEqual(real_init["mode"], "real")
            self.assertIn("REAL DATA", real_init["badge"])
            self.assertEqual(real_init["homeZero"], "No observations")
            self.assertEqual(real_init["resZero"], "No observations")

            # 4. Hand Hygiene Tally: overlapping moments (M1+M4 = 1 opportunity),
            #    missed action, and "8 of 10 opportunities, 80%"
            tally_res = b.js("""(() => {
              document.querySelector('[data-hhsub="tally"]').click();
              document.getElementById('tallyPeriod').value = '2026-11';
              document.getElementById('tallyArea').value = 'OPD';
              document.getElementById('btnStartTally').click();

              // Outcome without moment -> refused with message
              document.querySelector('.outcome.rub').click();
              const errNoMoment = document.getElementById('tallyMsg').textContent;

              // Opportunity 1: overlapping moments M1 and M4 with Hand rub -> 1 opportunity!
              document.querySelector('.moment[data-moment="1"]').click();
              document.querySelector('.moment[data-moment="4"]').click();
              document.querySelector('.outcome.rub').click();
              const afterOverlap = {
                text: document.getElementById('tallyRunningResult').textContent,
                ind: window.__IPCApp.state.data.hh.draft.ind.slice(),
                act: window.__IPCApp.state.data.hh.draft.act.slice()
              };

              // Opportunity 2: Moment 2 Missed
              document.querySelector('.moment[data-moment="2"]').click();
              document.querySelector('.outcome.missed').click();

              // Opportunities 3..9: 7 actions (5 rub, 2 wash)
              for (let i = 0; i < 5; i++) {
                document.querySelector('.moment[data-moment="1"]').click();
                document.querySelector('.outcome.rub').click();
              }
              for (let i = 0; i < 2; i++) {
                document.querySelector('.moment[data-moment="3"]').click();
                document.querySelector('.outcome.wash').click();
              }
              // Opportunity 10: Moment 5 Missed -> total 8 actions of 10 opportunities (80%)
              document.querySelector('.moment[data-moment="5"]').click();
              document.querySelector('.outcome.missed').click();

              const running10 = document.getElementById('tallyRunningResult').textContent;
              const counts10 = document.getElementById('tallyRunningCounts').textContent;
              document.getElementById('btnFinishTally').click();
              const overallAfterTally = document.getElementById('hhOverallResult').textContent;
              return { errNoMoment, afterOverlap, running10, counts10, overallAfterTally };
            })()""")
            self.assertTrue(len(tally_res["errNoMoment"]) > 0)
            self.assertEqual(tally_res["afterOverlap"]["text"], "1 of 1 opportunity, 100%")
            self.assertEqual(tally_res["afterOverlap"]["ind"], [1, 0, 0, 1, 0])
            self.assertEqual(tally_res["afterOverlap"]["act"], [1, 0, 0, 1, 0])
            self.assertEqual(tally_res["running10"], "8 of 10 opportunities, 80%")
            self.assertIn("Hand rub 6", tally_res["counts10"])
            self.assertIn("Handwash 2", tally_res["counts10"])
            self.assertIn("Missed 2", tally_res["counts10"])
            self.assertEqual(tally_res["overallAfterTally"], "8 of 10 opportunities, 80%")

            # 5. Paper totals entry & combining sessions by summing counts first:
            #    Session 1 = 8 of 10 (80%), Session 2 = 11 of 30 (6 rub, 5 wash, 19 missed)
            #    Combined = 19 of 40 opportunities, 48% (NOT average of 80% and 37% = 58%)
            paper_res = b.js("""(() => {
              document.querySelector('[data-hhsub="paper"]').click();
              document.getElementById('paperPeriod').value = '2026-11';
              document.getElementById('paperArea').value = 'OPD';
              document.getElementById('paperRub').value = '6';
              document.getElementById('paperWash').value = '5';
              document.getElementById('paperMissed').value = '19';
              document.getElementById('paperRub').dispatchEvent(new Event('input'));
              const calcPreview = document.getElementById('paperOppCalc').textContent;
              document.getElementById('btnSavePaper').click();
              return {
                calcPreview,
                combined: document.getElementById('hhOverallResult').textContent
              };
            })()""")
            self.assertIn("30", paper_res["calcPreview"])
            self.assertEqual(paper_res["combined"], "19 of 40 opportunities, 48%")

            # 6. Stock workflow: add item, receipts, FEFO earliest-expiring usable batch first,
            #    reorder point alert, expired batch exclusion, stockout, physical count, adjustment
            stock_res = b.js("""(() => {
              document.querySelector('[data-tab="stock"]').click();
              document.querySelector('[data-stsub="items"]').click();
              // Use preset 0: Alcohol-based hand rub, bottle (500 mL), reorder 10, tracksExpiry true
              document.querySelector('.btn-preset[data-idx="0"]').click();
              document.getElementById('btnSaveItem').click();

              // Record two receipts: HR-LATE (2027-06-01, qty 8) and HR-SOON (2026-12-01, qty 6)
              document.querySelector('[data-stsub="record"]').click();
              document.querySelector('[data-txntype="receipt"]').click();
              document.getElementById('txnDate').value = '2026-11-01';
              document.getElementById('txnQty').value = '8';
              document.getElementById('txnBatch').value = 'HR-LATE';
              document.getElementById('txnExpiry').value = '2027-06-01';
              document.getElementById('btnSaveTxn').click();

              document.querySelector('[data-stsub="record"]').click();
              document.querySelector('[data-txntype="receipt"]').click();
              document.getElementById('txnDate').value = '2026-11-02';
              document.getElementById('txnQty').value = '6';
              document.getElementById('txnBatch').value = 'HR-SOON';
              document.getElementById('txnExpiry').value = '2026-12-01';
              document.getElementById('btnSaveTxn').click();

              // Check status: usable = 14, earliest = HR-SOON, expiringSoon = 1
              const cardTextBeforeIssue = document.querySelector('[data-itemcard]').textContent;

              // Issue 5 bottles -> FEFO takes from HR-SOON first, leaving 9 usable (<= reorder point 10 -> low)
              document.querySelector('[data-stsub="record"]').click();
              document.querySelector('[data-txntype="issue"]').click();
              document.getElementById('txnDate').value = '2026-11-05';
              document.getElementById('txnQty').value = '5';
              document.getElementById('txnArea').value = 'OPD';
              document.getElementById('txnQty').dispatchEvent(new Event('input'));
              const issuePreview = document.getElementById('issuePlanPreview').textContent;
              document.getElementById('btnSaveTxn').click();

              const lowChip = document.getElementById('chipLow').textContent;

              // Also add an earlier batch that expired yesterday (2026-11-06, qty 4)
              document.querySelector('[data-stsub="record"]').click();
              document.querySelector('[data-txntype="receipt"]').click();
              document.getElementById('txnDate').value = '2026-09-01';
              document.getElementById('txnQty').value = '4';
              document.getElementById('txnBatch').value = 'HR-EXP';
              document.getElementById('txnExpiry').value = '2026-11-06';
              document.getElementById('btnSaveTxn').click();

              // Issue remaining 9 usable bottles -> usable = 0 (STOCKOUT) even though 4 expired are still on the shelf
              document.querySelector('[data-stsub="record"]').click();
              document.querySelector('[data-txntype="issue"]').click();
              document.getElementById('txnDate').value = '2026-11-07';
              document.getElementById('txnQty').value = '9';
              document.getElementById('btnSaveTxn').click();

              const stockoutChip = document.getElementById('chipStockout').textContent;
              const expiredChip = document.getElementById('chipExpired').textContent;
              const cardAtStockout = document.querySelector('[data-itemcard]').textContent;

              // Remove the 4 expired bottles using an Adjustment (reason = expired)
              document.querySelector('[data-stsub="record"]').click();
              document.querySelector('[data-txntype="adjust"]').click();
              document.getElementById('txnDate').value = '2026-11-07';
              document.getElementById('txnReason').value = 'expired';
              document.getElementById('txnQty').value = '4';
              document.getElementById('btnSaveTxn').click();

              // Receive a fresh batch (qty 12) and record a Physical Count of 11
              document.querySelector('[data-stsub="record"]').click();
              document.querySelector('[data-txntype="receipt"]').click();
              document.getElementById('txnDate').value = '2026-11-07';
              document.getElementById('txnQty').value = '12';
              document.getElementById('txnBatch').value = 'HR-FRESH';
              document.getElementById('txnExpiry').value = '2027-09-01';
              document.getElementById('btnSaveTxn').click();

              document.querySelector('[data-stsub="record"]').click();
              document.querySelector('[data-txntype="count"]').click();
              document.getElementById('txnDate').value = '2026-11-07';
              document.getElementById('txnQty').value = '11';
              document.getElementById('btnSaveTxn').click();

              const finalCard = document.querySelector('[data-itemcard]').textContent;
              return {
                cardTextBeforeIssue, issuePreview, lowChip,
                stockoutChip, expiredChip, cardAtStockout, finalCard
              };
            })()""")
            self.assertIn("Usable: 14 bottle (500 mL)", stock_res["cardTextBeforeIssue"])
            self.assertIn("Use first: HR-SOON", stock_res["cardTextBeforeIssue"])
            self.assertIn("HR-SOON (2026-12-01): 5", stock_res["issuePreview"])
            self.assertIn("1", stock_res["lowChip"])
            self.assertIn("Stockouts: 1", stock_res["stockoutChip"])
            self.assertIn("Expired stock to remove: 1", stock_res["expiredChip"])
            self.assertIn("Usable: 0 bottle (500 mL)", stock_res["cardAtStockout"])
            self.assertIn("Expired: 4 bottle (500 mL)", stock_res["cardAtStockout"])
            self.assertIn("Usable: 11 bottle (500 mL)", stock_res["finalCard"])

            # 7. Create backup and reports, and run device self-check
            bk_info = b.js("""(() => {
              document.querySelector('[data-tab="reports"]').click();
              document.getElementById('btnDownloadHHCSV').click();
              const hhCsv = window.__IPCApp.state.lastCsvText;
              document.getElementById('btnDownloadStockCSV').click();
              const stCsv = window.__IPCApp.state.lastCsvText;

              document.querySelector('[data-tab="backup"]').click();
              document.getElementById('btnDownloadBackup').click();
              const backupJson = window.__IPCApp.state.lastBackupJson;
              const backupName = window.__IPCApp.state.lastBackupFilename;

              document.querySelector('[data-tab="settings"]').click();
              document.getElementById('btnCheckDevice').click();
              const deviceReport = window.__IPCApp.state.deviceCheckReport;
              return { hhCsv, stCsv, backupJson, backupName, deviceReport };
            })()""")
            self.assertIn("2026-11,OPD,2,40,12,7,21,19,47.5,yes", bk_info["hhCsv"])
            self.assertIn("Alcohol-based hand rub,bottle (500 mL),11,ok", bk_info["stCsv"])
            self.assertTrue(bk_info["backupName"].startswith("ipc-kit-backup_"))
            self.assertIn("Saving in this browser: works", bk_info["deviceReport"])

            saved_backup_json = bk_info["backupJson"]
        finally:
            b.stop()

        # --- Session 2: Reopen browser on the SAME profile to verify offline persistence,
        #     test invalid backup rejection, and test valid backup restore ---
        b2 = BrowserSession(self.prof, self.home, port=9232)
        try:
            b2.start()
            b2.navigate_file(HTML_PATH)
            b2.js("window.__IPC_TEST_TODAY = '2026-11-07';")

            reopen_state = b2.js("""({
              mode: window.__IPCApp.state.mode,
              entries: window.__IPCApp.state.data.hh.entries.length,
              items: window.__IPCApp.state.data.stock.items.length,
              txns: window.__IPCApp.state.data.stock.txns.length
            })""")
            self.assertEqual(reopen_state["mode"], "real")
            self.assertEqual(reopen_state["entries"], 2)
            self.assertEqual(reopen_state["items"], 1)
            self.assertEqual(reopen_state["txns"], 9)

            # Test invalid backups: (a) not JSON, (b) tampered checksum, (c) injected PHI field
            tampered_obj = json.loads(saved_backup_json)
            tampered_obj["data"]["hh"]["entries"][0]["rub"] = 999
            tampered_json = json.dumps(tampered_obj)

            phi_obj = json.loads(saved_backup_json)
            phi_obj["data"]["hh"]["entries"][0]["patientName"] = "Jane Doe"
            phi_json = json.dumps(phi_obj)

            inv_res = b2.js("""((tampered, phi) => {
              document.querySelector('[data-tab="backup"]').click();
              const tryRestore = (txt) => {
                document.getElementById('backupTextIn').value = txt;
                document.getElementById('btnCheckBackup').click();
                const errBox = document.getElementById('restoreErrorBox');
                const confirmBtn = document.getElementById('btnConfirmRestore');
                return {
                  rejected: !!errBox && !confirmBtn,
                  msg: errBox ? errBox.textContent : '',
                  entriesStill: window.__IPCApp.state.data.hh.entries.length,
                  rubStill: window.__IPCApp.state.data.hh.entries[0].rub
                };
              };
              return {
                corrupt: tryRestore('{broken json'),
                tampered: tryRestore(tampered),
                phi: tryRestore(phi)
              };
            })(%s, %s)""" % (json.dumps(tampered_json), json.dumps(phi_json)))

            for k in ("corrupt", "tampered", "phi"):
                self.assertTrue(inv_res[k]["rejected"], k)
                self.assertIn("Your current data has NOT been changed", inv_res[k]["msg"])
                self.assertEqual(inv_res[k]["entriesStill"], 2)
                self.assertEqual(inv_res[k]["rubStill"], 6)

            # Erase real data (must type ERASE), then restore from the valid backup (with confirm modal)
            restore_res = b2.js("""((validJson) => {
              document.querySelector('[data-tab="settings"]').click();
              const rmBtnRect = document.querySelector('.btn-rm-area').getBoundingClientRect();
              document.getElementById('btnEraseReal').click();
              const modalYes = document.getElementById('modalYes');
              const modalIn = document.getElementById('modalWordInput');
              const disabledInitially = modalYes.disabled;
              modalIn.value = 'WRONG'; modalIn.dispatchEvent(new Event('input'));
              const disabledOnWrong = modalYes.disabled;
              modalIn.value = 'ERASE'; modalIn.dispatchEvent(new Event('input'));
              const enabledOnErase = !modalYes.disabled;
              modalYes.click();
              const afterEraseEntries = window.__IPCApp.state.data.hh.entries.length;

              document.querySelector('[data-tab="backup"]').click();
              document.getElementById('backupTextIn').value = validJson;
              document.getElementById('btnCheckBackup').click();
              const validBox = !!document.getElementById('restoreValidBox');
              document.getElementById('btnConfirmRestore').click();
              const confirmRestoreOpened = !!document.getElementById('modalYes');
              document.getElementById('modalYes').click();
              return {
                rmBtnHeight: rmBtnRect.height,
                disabledInitially,
                disabledOnWrong,
                enabledOnErase,
                afterEraseEntries,
                validBox,
                confirmRestoreOpened,
                restoredEntries: window.__IPCApp.state.data.hh.entries.length,
                restoredItems: window.__IPCApp.state.stock ? 0 : window.__IPCApp.state.data.stock.items.length,
                restoredTxns: window.__IPCApp.state.data.stock.txns.length,
                hasUndo: !!document.getElementById('btnUndoRestore')
              };
            })(%s)""" % json.dumps(saved_backup_json))

            self.assertGreaterEqual(restore_res["rmBtnHeight"], 44)
            self.assertTrue(restore_res["disabledInitially"])
            self.assertTrue(restore_res["disabledOnWrong"])
            self.assertTrue(restore_res["enabledOnErase"])
            self.assertEqual(restore_res["afterEraseEntries"], 0)
            self.assertTrue(restore_res["validBox"])
            self.assertTrue(restore_res["confirmRestoreOpened"])
            self.assertEqual(restore_res["restoredEntries"], 2)
            self.assertEqual(restore_res["restoredItems"], 1)
            self.assertEqual(restore_res["restoredTxns"], 9)
            self.assertTrue(restore_res["hasUndo"])
        finally:
            b2.stop()

    def test_fresh_copy_earlier_backup_combined_metrics_and_field_kit(self):
        prof3 = os.path.join(WORK_DIR, "e2e_prof_fresh")
        home3 = os.path.join(WORK_DIR, "e2e_home_fresh")
        shutil.rmtree(prof3, ignore_errors=True)
        shutil.rmtree(home3, ignore_errors=True)
        b3 = BrowserSession(prof3, home3, port=9233)
        try:
            b3.start()
            # 1. Start from START-HERE.html and follow the app link
            start_path = os.path.join(ROOT, "START-HERE.html")
            b3.navigate_file(start_path)
            app_href = b3.js("document.querySelector('a[href=\"ipc-kit.html\"]').getAttribute('href')")
            self.assertEqual(app_href, "ipc-kit.html")
            b3.navigate_file(HTML_PATH)
            b3.js("window.__IPC_TEST_TODAY = '2026-11-07';")

            # Set up real data: test 2/2 + 6/8 -> 8 of 10 (80%), and 6 units (4 expired) -> 2 usable,
            # plus correction adjustment Remove from stock
            combo = b3.js("""(() => {
              document.getElementById('btnStartReal').click();
              document.getElementById('newAreaCode').value = 'OPD';
              document.getElementById('btnAddArea').click();

              document.querySelector('[data-tab="hh"]').click();
              document.querySelector('[data-hhsub="tally"]').click();
              document.getElementById('tallyPeriod').value = '2026-11';
              document.getElementById('tallyArea').value = 'OPD';
              document.getElementById('btnStartTally').click();
              for (let i = 0; i < 2; i++) {
                document.querySelector('.moment[data-moment="1"]').click();
                document.querySelector('.outcome.rub').click();
              }
              document.getElementById('btnFinishTally').click();

              document.querySelector('[data-hhsub="paper"]').click();
              document.getElementById('paperPeriod').value = '2026-11';
              document.getElementById('paperArea').value = 'OPD';
              document.getElementById('paperRub').value = '4';
              document.getElementById('paperWash').value = '2';
              document.getElementById('paperMissed').value = '2';
              document.getElementById('btnSavePaper').click();
              const hhCombined = document.getElementById('hhOverallResult').textContent;

              // Stock: 4 expired + 2 valid = 6 on hand, 2 usable; then correction remove 1 -> 1 usable
              document.querySelector('[data-tab="stock"]').click();
              document.querySelector('[data-stsub="items"]').click();
              document.querySelector('.btn-preset[data-idx="0"]').click();
              document.getElementById('btnSaveItem').click();

              document.querySelector('[data-stsub="record"]').click();
              document.querySelector('[data-txntype="receipt"]').click();
              document.getElementById('txnDate').value = '2026-09-01';
              document.getElementById('txnQty').value = '4';
              document.getElementById('txnBatch').value = 'EXP-4';
              document.getElementById('txnExpiry').value = '2026-11-06';
              document.getElementById('btnSaveTxn').click();

              document.querySelector('[data-stsub="record"]').click();
              document.querySelector('[data-txntype="receipt"]').click();
              document.getElementById('txnDate').value = '2026-10-01';
              document.getElementById('txnQty').value = '2';
              document.getElementById('txnBatch').value = 'OK-2';
              document.getElementById('txnExpiry').value = '2027-06-01';
              document.getElementById('btnSaveTxn').click();
              const cardBeforeCorr = document.querySelector('[data-itemcard]').textContent;

              document.querySelector('[data-stsub="record"]').click();
              document.querySelector('[data-txntype="adjust"]').click();
              document.getElementById('txnDate').value = '2026-11-07';
              document.getElementById('txnReason').value = 'correction';
              document.getElementById('txnReason').dispatchEvent(new Event('change'));
              document.getElementById('txnDirection').value = 'remove';
              document.getElementById('txnQty').value = '1';
              // Pick OK-2 (index 1)
              document.getElementById('txnBatchPick').value = '1';
              document.getElementById('txnBatchPick').dispatchEvent(new Event('change'));
              document.getElementById('btnSaveTxn').click();
              const cardAfterCorr = document.querySelector('[data-itemcard]').textContent;

              return { hhCombined, cardBeforeCorr, cardAfterCorr };
            })()""")
            self.assertEqual(combo["hhCombined"], "8 of 10 opportunities, 80%")
            self.assertIn("Usable: 2 bottle (500 mL)", combo["cardBeforeCorr"])
            self.assertIn("Expired: 4 bottle (500 mL)", combo["cardBeforeCorr"])
            self.assertIn("Usable: 1 bottle (500 mL)", combo["cardAfterCorr"])

            # 2. Restore earlier supported backups (sample-data/practice-backup.json & unicode fixture)
            with open(os.path.join(ROOT, "sample-data", "practice-backup.json"), encoding="utf-8") as fh:
                sample_json = fh.read()
            with open(os.path.join(HERE, "fixtures", "unicode-backup.json"), encoding="utf-8") as fh:
                unicode_json = fh.read()

            early_res = b3.js("""((sampleTxt, uniTxt) => {
              document.querySelector('[data-tab="backup"]').click();
              document.getElementById('backupTextIn').value = sampleTxt;
              document.getElementById('btnCheckBackup').click();
              const wrongModeBlocked = !!document.getElementById('restoreValidBox') &&
                !document.getElementById('btnConfirmRestore');
              window.__IPCApp.setMode('practice', false);
              document.querySelector('[data-tab="backup"]').click();
              document.getElementById('backupTextIn').value = sampleTxt;
              document.getElementById('btnCheckBackup').click();
              const sampleValid = !!document.getElementById('restoreValidBox');
              document.getElementById('btnConfirmRestore').click();
              document.getElementById('modalYes').click();
              const afterSampleItems = window.__IPCApp.state.data.stock.items.length;

              document.getElementById('backupTextIn').value = uniTxt;
              document.getElementById('btnCheckBackup').click();
              const uniValid = !!document.getElementById('restoreValidBox');
              document.getElementById('btnConfirmRestore').click();
              document.getElementById('modalYes').click();
              window.__IPCApp.setMode('real', false);
              const realEntries = window.__IPCApp.state.data.hh.entries.length;
              window.__IPCApp.setMode('practice', false);
              return {
                wrongModeBlocked, realEntries, sampleValid,
                afterSampleItems,
                uniValid,
                uniFacility: window.__IPCApp.state.data.settings.facilityLabel
              };
            })(%s, %s)""" % (json.dumps(sample_json), json.dumps(unicode_json)))
            self.assertTrue(early_res["wrongModeBlocked"])
            self.assertEqual(early_res["realEntries"], 2)
            self.assertTrue(early_res["sampleValid"])
            self.assertEqual(early_res["afterSampleItems"], 5)
            self.assertTrue(early_res["uniValid"])
            self.assertEqual(early_res["uniFacility"], "Clinique Été – démo")

            # 3. Verify printable field-kit pages and evidence register offline + print layout page counts
            for rel, max_pages in [
                ("field-kit/quick-start.html", 1),
                ("field-kit/hand-hygiene-observation-sheet.html", 1),
                ("field-kit/readiness-checklist.html", 1),
                ("field-kit/index.html", 2),
                ("evidence/evidence-register.html", 10),
            ]:
                b3.navigate_file(os.path.join(ROOT, rel))
                meta_info = b3.js("""({
                  csp: document.querySelector('meta[http-equiv="Content-Security-Policy"]').content,
                  scripts: document.querySelectorAll('script').length,
                  title: document.title
                })""")
                self.assertIn("default-src 'none'", meta_info["csp"], rel)
                self.assertEqual(meta_info["scripts"], 0, rel)
                self.assertTrue(len(meta_info["title"]) > 0, rel)
                pdf_res = b3.bidi.call("browsingContext.print", {
                    "context": b3.context,
                    "page": {"width": 21.0, "height": 29.7},
                    "margin": {"top": 1.2, "bottom": 1.2, "left": 1.2, "right": 1.2}
                })
                pdf_bytes = base64.b64decode(pdf_res["data"])
                import re
                pages = len(re.findall(br"/Type\s*/Page\b(?!s)", pdf_bytes))
                self.assertGreaterEqual(pages, 1, rel)
                self.assertLessEqual(pages, max_pages, "%s overflowed to %d pages (expected <= %d)" % (rel, pages, max_pages))

            # 4. Verify single-file ALL-PRINTABLE-SHEETS.html (zero scripts, same-page anchors)
            b3.navigate_file(os.path.join(ROOT, "field-kit", "ALL-PRINTABLE-SHEETS.html"))
            all_info = b3.js("""(() => {
              const anchors = Array.from(document.querySelectorAll('.toc-page a[href^="#"]'))
                .map(a => a.getAttribute('href').slice(1));
              const resolved = anchors.filter(id => !!document.getElementById(id));
              return {
                csp: document.querySelector('meta[http-equiv="Content-Security-Policy"]').content,
                scripts: document.querySelectorAll('script').length,
                anchorCount: anchors.length,
                resolvedCount: resolved.length
              };
            })()""")
            self.assertIn("default-src 'none'", all_info["csp"])
            self.assertEqual(all_info["scripts"], 0)
            self.assertEqual(all_info["anchorCount"], 8)
            self.assertEqual(all_info["resolvedCount"], 8)

            # 5. Verify built-in Printable Kit & Guides inside ipc-kit.html (works without cross-file navigation)
            b3.navigate_file(HTML_PATH)
            kit_flow = b3.js("""(() => {
              document.getElementById('btnHomeGoKit').click();
              const stayedUrl1 = location.href.endsWith('ipc-kit.html');
              const indexH1 = document.querySelector('#kitDocRender h1').textContent;
              // Click link inside field-kit/index.html -> intercepted in-app to quick-start
              document.querySelector('#kitDocRender a[href="quick-start.html"]').click();
              const stayedUrl2 = location.href.endsWith('ipc-kit.html');
              const quickId = window.__IPCApp.state.kitDoc;
              // Open All 8 sheets pack
              const sel = document.getElementById('kitDocSelect');
              sel.value = 'field-kit/ALL-PRINTABLE-SHEETS.html';
              sel.dispatchEvent(new Event('change'));
              const packSections = document.querySelectorAll('#kitDocRender section[id^="sheet-"]').length;
              // Open Evidence Register and click CSV download link
              sel.value = 'evidence/evidence-register.html';
              sel.dispatchEvent(new Event('change'));
              document.querySelector('#kitDocRender a[href="evidence-register.csv"]').click();
              const csvToast = document.getElementById('toast').textContent;
              // Open Markdown Device Testing Guide
              sel.value = 'docs/DEVICE-TESTING.md';
              sel.dispatchEvent(new Event('change'));
              const mdHasErr = document.getElementById('kitDocRender').textContent.includes('ERR_FILE_NOT_FOUND');
              // EN/FR parity check
              const enKeys = Object.keys(window.IPC_STRINGS.en);
              const missingFr = enKeys.filter(k => !(k in window.IPC_STRINGS.fr));
              return { stayedUrl1, indexH1, stayedUrl2, quickId, packSections, csvToast, mdHasErr, enCount: enKeys.length, missingFr };
            })()""")
            self.assertTrue(kit_flow["stayedUrl1"])
            self.assertIn("Printable Field Kit Index", kit_flow["indexH1"])
            self.assertTrue(kit_flow["stayedUrl2"])
            self.assertEqual(kit_flow["quickId"], "field-kit/quick-start.html")
            self.assertEqual(kit_flow["packSections"], 8)
            self.assertIn("evidence-register.csv", kit_flow["csvToast"])
            self.assertTrue(kit_flow["mdHasErr"])
            self.assertEqual(kit_flow["missingFr"], [])

            # Verify printing the 1-page sheets FROM INSIDE ipc-kit.html stays <= 1 page each
            import re
            for doc_id in [
                "field-kit/quick-start.html",
                "field-kit/hand-hygiene-observation-sheet.html",
                "field-kit/readiness-checklist.html",
            ]:
                b3.js("""((id) => {
                  const sel = document.getElementById('kitDocSelect');
                  sel.value = id;
                  sel.dispatchEvent(new Event('change'));
                })(%s)""" % json.dumps(doc_id))
                pdf_res = b3.bidi.call("browsingContext.print", {
                    "context": b3.context,
                    "page": {"width": 21.0, "height": 29.7},
                    "margin": {"top": 1.2, "bottom": 1.2, "left": 1.2, "right": 1.2}
                })
                pdf_bytes = base64.b64decode(pdf_res["data"])
                pages = len(re.findall(br"/Type\s*/Page\b(?!s)", pdf_bytes))
                self.assertEqual(pages, 1, "In-app print of %s produced %d pages (expected 1)" % (doc_id, pages))

            # Click Home tab -> leaves kit viewer cleanly
            left_kit = b3.js("""(() => {
              document.querySelector('[data-tab="home"]').click();
              return {
                kitDoc: window.__IPCApp.state.kitDoc,
                hasHomeBtn: !!document.getElementById('btnHomeGoKit')
              };
            })()""")
            self.assertIsNone(left_kit["kitDoc"])
            self.assertTrue(left_kit["hasHomeBtn"])

            # Simulate LineageOS Jelly (Android System WebView '; wv)') and verify fallbacks & Clean print view
            wv_res = b3.js("""(() => {
              const origDesc = Object.getOwnPropertyDescriptor(Navigator.prototype, 'userAgent')
                || Object.getOwnPropertyDescriptor(navigator, 'userAgent');
              Object.defineProperty(navigator, 'userAgent', {
                value: 'Mozilla/5.0 (Linux; Android 14; LineageOS; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/124.0.0.0 Mobile Safari/537.36',
                configurable: true
              });
              let printCalls = 0;
              const origPrint = window.print;
              window.print = function () { printCalls++; };
              try {
                // 1) Settings -> Check this device reports WebView download/print failure + Copy button (FR then switch to EN)
                document.querySelector('[data-tab="settings"]').click();
                document.getElementById('btnCheckDevice').click();
                const deviceTextFr = document.getElementById('deviceCheckOut').value;
                document.getElementById('setLang').value = 'en';
                document.getElementById('btnSaveSettings').click();
                document.getElementById('btnCheckDevice').click();
                const deviceText = document.getElementById('deviceCheckOut').value;
                const hasDeviceCopy = !!document.getElementById('btnDeviceCopy');
                document.getElementById('btnDeviceCopy').click();

                // 2) Backup -> Download triggers copyable text fallback immediately instead of fake download toast
                document.querySelector('[data-tab="backup"]').click();
                document.getElementById('btnDownloadBackup').click();
                const backupFallback = !!(document.getElementById('backupTextOut') && document.getElementById('btnBackupCopy'));
                document.getElementById('btnBackupCopy').click();
                const backupToast = document.getElementById('toast').textContent;

                // 3) Reports -> WebView banner, CSV copy fallback, Print warning, Clean print view toggle
                document.querySelector('[data-tab="reports"]').click();
                const hasRepBanner = !!document.getElementById('repWvBanner');
                document.getElementById('btnDownloadHHCSV').click();
                const repCsvFallback = !!(document.getElementById('repCsvFallbackOut') && document.getElementById('btnRepCsvCopy'));
                document.getElementById('btnRepCsvCopy').click();
                document.getElementById('btnPrintReport').click();
                const hasRepPrintWarn = !!document.getElementById('repPrintWarn');
                document.getElementById('btnRepCleanView').click();
                const repCleanActive = document.body.classList.contains('clean-print-mode') && !!document.getElementById('btnExitRepClean');
                document.getElementById('btnExitRepClean').click();
                const repCleanExited = !document.body.classList.contains('clean-print-mode');

                // 4) Printable Kit -> WebView banner, hidden standalone link, Print warning, Download -> HTML Copy fallback, Clean print view
                document.querySelector('[data-tab="home"]').click();
                document.getElementById('btnHomeGoKit').click();
                const sel = document.getElementById('kitDocSelect');
                sel.value = 'field-kit/quick-start.html';
                sel.dispatchEvent(new Event('change'));
                const hasKitBanner = !!document.getElementById('kitWvBanner');
                const noStandaloneBtn = !document.getElementById('btnKitStandalone');
                document.getElementById('btnKitPrint').click();
                const hasKitPrintWarn = !!document.getElementById('kitPrintWarn');
                document.getElementById('btnKitDownload').click();
                const kitFallbackHtml = document.getElementById('kitFallbackOut') ? document.getElementById('kitFallbackOut').value : '';
                const hasKitCopy = !!document.getElementById('btnKitCopy');
                document.getElementById('btnKitCopy').click();
                document.getElementById('btnKitCleanView').click();
                const kitCleanActive = document.body.classList.contains('clean-print-mode') && !!document.getElementById('btnExitCleanView');
                // Exiting back clears clean-print-mode
                document.getElementById('btnKitBack').click();
                const kitCleanClearedOnBack = !document.body.classList.contains('clean-print-mode');

                return {
                  printCalls, deviceTextFr, deviceText, hasDeviceCopy, backupFallback, backupToast,
                  hasRepBanner, repCsvFallback, hasRepPrintWarn, repCleanActive, repCleanExited,
                  hasKitBanner, noStandaloneBtn, hasKitPrintWarn, hasKitCopy,
                  kitFallbackHasHtml: kitFallbackHtml.includes('<!DOCTYPE html>') && kitFallbackHtml.includes('Privacy Rule'),
                  kitCleanActive, kitCleanClearedOnBack
                };
              } finally {
                window.print = origPrint;
                if (origDesc) Object.defineProperty(navigator, 'userAgent', origDesc);
              }
            })()""")
            self.assertEqual(wv_res["printCalls"], 2)
            self.assertIn("Téléchargement de fichier: ne fonctionne PAS", wv_res["deviceTextFr"])
            self.assertIn("Impression: ne fonctionne PAS", wv_res["deviceTextFr"])
            self.assertIn("WebView Android détecté", wv_res["deviceTextFr"])
            self.assertIn("File download: does NOT work", wv_res["deviceText"])
            self.assertIn("Printing: does NOT work", wv_res["deviceText"])
            self.assertIn("Android WebView detected", wv_res["deviceText"])
            self.assertTrue(wv_res["hasDeviceCopy"])
            self.assertTrue(wv_res["backupFallback"])
            self.assertTrue(wv_res["hasRepBanner"])
            self.assertTrue(wv_res["repCsvFallback"])
            self.assertTrue(wv_res["hasRepPrintWarn"])
            self.assertTrue(wv_res["repCleanActive"])
            self.assertTrue(wv_res["repCleanExited"])
            self.assertTrue(wv_res["hasKitBanner"])
            self.assertTrue(wv_res["noStandaloneBtn"])
            self.assertTrue(wv_res["hasKitPrintWarn"])
            self.assertTrue(wv_res["hasKitCopy"])
            self.assertTrue(wv_res["kitFallbackHasHtml"])
            self.assertTrue(wv_res["kitCleanActive"])
            self.assertTrue(wv_res["kitCleanClearedOnBack"])

            # Verify all 6 UN languages, Arabic RTL layout, Stock Issue validation order, and UTF-8 BOM CSV download
            multi_res = b3.js("""(() => {
              const langs = Object.keys(window.IPC_STRINGS);
              const langStates = {};
              document.querySelector('[data-tab="settings"]').click();
              for (const code of ['ar', 'zh', 'ru', 'es', 'fr', 'en']) {
                document.getElementById('setLang').value = code;
                document.getElementById('btnSaveSettings').click();
                langStates[code] = {
                  htmlLang: document.documentElement.lang,
                  htmlDir: document.documentElement.dir,
                  homeTab: document.querySelector('[data-tab="home"]').textContent,
                  brandDir: getComputedStyle(document.querySelector('header .brand')).direction
                };
              }
              // Arabic RTL check including LTR-preserved textareas and embedded sheet preview
              document.getElementById('setLang').value = 'ar';
              document.getElementById('btnSaveSettings').click();
              document.querySelector('[data-tab="backup"]').click();
              const bkDir = document.getElementById('backupTextIn').getAttribute('dir');
              document.querySelector('[data-tab="home"]').click();
              document.getElementById('btnHomeGoKit').click();
              const fkDir = getComputedStyle(document.querySelector('#kitDocRender .fk-doc')).direction;
              document.getElementById('btnKitBack').click();
              document.querySelector('[data-tab="settings"]').click();
              document.getElementById('setLang').value = 'en';
              document.getElementById('btnSaveSettings').click();

              // Stock > Record > Issue: empty / 0 / future date show exact field errors before 'Not enough stock'
              document.querySelector('[data-tab="stock"]').click();
              document.querySelector('[data-stsub="record"]').click();
              document.querySelector('[data-txntype="issue"]').click();
              document.getElementById('txnQty').value = '';
              document.getElementById('btnSaveTxn').click();
              const errEmptyQty = document.getElementById('txnErr').textContent;
              document.getElementById('txnQty').value = '0';
              document.getElementById('btnSaveTxn').click();
              const errZeroQty = document.getElementById('txnErr').textContent;
              document.getElementById('txnQty').value = '1';
              document.getElementById('txnDate').value = '0000-01-01';
              document.getElementById('btnSaveTxn').click();
              const errBadDate = document.getElementById('txnErr').textContent;

              // Capture Blob payload on Reports -> Download HH CSV (expects UTF-8 BOM \\uFEFF)
              document.querySelector('[data-tab="reports"]').click();
              const OrigBlob = window.Blob;
              let blobText = '';
              window.Blob = function (parts, opts) {
                if (opts && String(opts.type || '').includes('text/csv') && Array.isArray(parts)) {
                  blobText = String(parts[0] || '');
                }
                return new OrigBlob(parts, opts);
              };
              try {
                document.getElementById('btnDownloadHHCSV').click();
              } finally {
                window.Blob = OrigBlob;
              }
              return { langs, langStates, bkDir, fkDir, errEmptyQty, errZeroQty, errBadDate, blobText };
            })()""")
            self.assertEqual(sorted(multi_res["langs"]), ["ar", "en", "es", "fr", "ru", "zh"])
            self.assertEqual(multi_res["langStates"]["ar"]["htmlLang"], "ar")
            self.assertEqual(multi_res["langStates"]["ar"]["htmlDir"], "rtl")
            self.assertEqual(multi_res["langStates"]["ar"]["brandDir"], "rtl")
            self.assertEqual(multi_res["langStates"]["ar"]["homeTab"], "الرئيسية")
            self.assertEqual(multi_res["langStates"]["zh"]["htmlDir"], "ltr")
            self.assertEqual(multi_res["langStates"]["zh"]["homeTab"], "首页")
            self.assertEqual(multi_res["langStates"]["ru"]["homeTab"], "Главная")
            self.assertEqual(multi_res["langStates"]["es"]["homeTab"], "Inicio")
            self.assertEqual(multi_res["bkDir"], "ltr")
            self.assertEqual(multi_res["fkDir"], "ltr")
            self.assertIn("valid quantity", multi_res["errEmptyQty"])
            self.assertIn("valid quantity", multi_res["errZeroQty"])
            self.assertIn("valid date", multi_res["errBadDate"])
            self.assertTrue(multi_res["blobText"].startswith("\uFEFFperiod,area,"))
            # Verify BOM-prefixed CSV is cleanly parsed by ipc_tool.py combine-reports
            os.makedirs(WORK_DIR, exist_ok=True)
            bom_csv_path = os.path.join(WORK_DIR, "bom-hh-export.csv")
            with open(bom_csv_path, "w", encoding="utf-8", newline="") as tf:
                tf.write(multi_res["blobText"])
            try:
                comb = subprocess.run(
                    [sys.executable, os.path.join(ROOT, "tools", "ipc_tool.py"), "combine-reports", bom_csv_path, "--by", "all"],
                    capture_output=True, text=True, check=True
                )
                self.assertIn("period,area,", comb.stdout)
                self.assertIn("ALL,ALL,", comb.stdout)
            finally:
                if os.path.exists(bom_csv_path):
                    os.unlink(bom_csv_path)
        finally:
            b3.stop()


if __name__ == "__main__":
    unittest.main()
