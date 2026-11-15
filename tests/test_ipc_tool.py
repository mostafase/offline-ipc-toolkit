"""Tests for tools/ipc_tool.py (standard library unittest; no network).

Run: python3 -m unittest tests/test_ipc_tool.py -v

The backup fixtures are produced by the JavaScript core inside ipc-kit.html
(tools/make_sample_data.js), so these tests also prove that the browser app
and the desktop tool agree on checksums and validation rules.
"""
import contextlib
import copy
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import ipc_tool  # noqa: E402

SAMPLE = os.path.join(ROOT, "sample-data", "practice-backup.json")
UNICODE = os.path.join(HERE, "fixtures", "unicode-backup.json")
REPORT_A = os.path.join(ROOT, "sample-data", "practice-report-hand-hygiene.csv")
REPORT_B = os.path.join(HERE, "fixtures", "second-report-hand-hygiene.csv")


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def run_check(obj_or_bytes):
    raw = obj_or_bytes if isinstance(obj_or_bytes, bytes) else json.dumps(obj_or_bytes, ensure_ascii=False).encode("utf-8")
    return ipc_tool.parse_backup(raw)


def resign(b):
    b["checksum"] = ipc_tool.checksum(b["data"])
    return b


class BackupChecks(unittest.TestCase):
    def test_js_backup_is_valid_in_python(self):
        ok, errs, b = run_check(load(SAMPLE))
        self.assertTrue(ok, errs)
        self.assertEqual(b["mode"], "practice")

    def test_unicode_checksum_matches_js(self):
        b = load(UNICODE)
        self.assertEqual(ipc_tool.checksum(b["data"]), b["checksum"])
        ok, errs, _ = run_check(b)
        self.assertTrue(ok, errs)

    def test_tampered_count_fails_checksum(self):
        b = load(SAMPLE)
        b["data"]["hh"]["entries"][0]["rub"] += 1
        ok, errs, _ = run_check(b)
        self.assertFalse(ok)
        self.assertTrue(any(e.startswith("checksum") for e in errs), errs)

    def test_extra_identifier_field_refused_even_with_good_checksum(self):
        b = load(SAMPLE)
        b["data"]["hh"]["entries"][0]["staffName"] = "Fictional Person"
        ok, errs, _ = run_check(resign(b))
        self.assertFalse(ok)
        self.assertIn('hh.entries[0]: unexpected field "staffName"', errs)

    def test_note_field_on_stock_refused(self):
        b = load(SAMPLE)
        b["data"]["stock"]["txns"][0]["note"] = "free text"
        ok, errs, _ = run_check(resign(b))
        self.assertFalse(ok)
        self.assertTrue(any('unexpected field "note"' in e for e in errs), errs)

    def test_newer_version_refused(self):
        b = load(SAMPLE)
        b["formatVersion"] = 2
        ok, errs, _ = run_check(b)
        self.assertFalse(ok)
        self.assertTrue(errs[0].startswith("newer_version"))

    def test_not_json_and_not_backup(self):
        self.assertEqual(run_check(b"")[1], ["empty"])
        self.assertEqual(run_check(b"{oops")[1], ["not_json"])
        self.assertEqual(run_check({"hello": 1})[1], ["not_backup"])
        self.assertEqual(run_check(b'{"format":"ipc-starter-kit-backup","formatVersion":NaN}')[1], ["not_json"])

    def test_negative_stock_refused(self):
        b = load(SAMPLE)
        d = b["data"]
        item = d["stock"]["items"][3]           # chlorine: already at zero in the sample
        d["stock"]["txns"].append({"id": "t900", "itemId": item["id"], "date": "2026-11-06", "type": "issue",
                                   "qty": 1, "batch": "CL-0412", "expiry": "2027-05-26", "reason": "", "area": ""})
        d["meta"]["nextId"] = 901
        ok, errs, _ = run_check(resign(b))
        self.assertFalse(ok)
        self.assertTrue(any("txn_insufficient" in e for e in errs), errs)

    def test_inconsistent_moment_counts_refused(self):
        b = load(SAMPLE)
        e = b["data"]["hh"]["entries"][0]
        e["act"][0] = e["ind"][0] + 1
        ok, errs, _ = run_check(resign(b))
        self.assertFalse(ok)
        self.assertTrue(any("hh_act_gt_ind" in x for x in errs), errs)

    def test_boolean_is_not_a_count(self):
        b = load(SAMPLE)
        b["data"]["hh"]["entries"][2]["missed"] = True
        ok, errs, _ = run_check(resign(b))
        self.assertFalse(ok)

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory(dir=os.path.join(HERE, ".work") if os.path.isdir(os.path.join(HERE, ".work")) else None) as tmp:
            bad = os.path.join(tmp, "bad.json")
            with open(bad, "w") as fh:
                fh.write("not a backup")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(ipc_tool.main(["check-backup", SAMPLE]), 0)
                self.assertEqual(ipc_tool.main(["check-backup", SAMPLE, bad]), 1)
            self.assertIn("VALID    " + SAMPLE, out.getvalue())
            self.assertIn("INVALID  " + bad, out.getvalue())


class CombineReports(unittest.TestCase):
    def test_sum_counts_then_recalculate(self):
        rows = ipc_tool.read_hh_csv(REPORT_B)
        table = ipc_tool.combine(rows, "all", 200)
        total = table[1]
        # 9 of 10 and 10 of 30 combine to 19 of 40 = 47.5%, not the 61.7% average of percentages.
        self.assertEqual(total[3], 40)
        self.assertEqual(total[7], 19)
        self.assertEqual(total[8], "47.5")
        self.assertEqual(total[9], "yes")
        self.assertEqual(ipc_tool.fmt_pct(19, 40), "48%")

    def test_combine_two_facilities_by_area(self):
        rows = ipc_tool.read_hh_csv(REPORT_A) + ipc_tool.read_hh_csv(REPORT_B)
        table = {r[1]: r for r in ipc_tool.combine(rows, "area", 200)[1:]}
        opd = table["OPD"]
        self.assertEqual(opd[3], 12 + 100 + 30 + 10)
        self.assertEqual(opd[7], 9 + 70 + 10 + 9)
        # Moment columns only include rows that had moment data (112 opportunities).
        self.assertEqual(opd[10], 112)
        self.assertEqual(table["WARD-A"][11], "")     # no moment data at all -> blank, not 0

    def test_file_total_row_is_not_double_counted(self):
        rows = ipc_tool.read_hh_csv(REPORT_A)
        self.assertNotIn("ALL", [r["period"] for r in rows])
        self.assertEqual(sum(r["opportunities"] for r in rows), 244)

    def test_zero_and_rounding_display(self):
        self.assertEqual(ipc_tool.fmt_pct(0, 0), "No observations")
        self.assertEqual(ipc_tool.fmt_pct(8, 10), "80%")
        self.assertEqual(ipc_tool.fmt_pct(999, 1000), ">99%")
        self.assertEqual(ipc_tool.fmt_pct(1, 1000), "<1%")

    def test_rejects_foreign_csv(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, dir=HERE) as fh:
            fh.write("name,score\nA,1\n")
            name = fh.name
        try:
            with self.assertRaises(ValueError):
                ipc_tool.read_hh_csv(name)
        finally:
            os.remove(name)


class NoNetwork(unittest.TestCase):
    def test_tool_imports_no_network_modules(self):
        with open(os.path.join(ROOT, "tools", "ipc_tool.py"), encoding="utf-8") as fh:
            src = fh.read()
        for mod in ("socket", "urllib", "http", "requests", "ftplib", "smtplib"):
            self.assertNotRegex(src, r"^\s*(import|from)\s+%s\b" % mod)

    def test_runs_as_a_script(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "ipc_tool.py"), "--version"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        self.assertIn("1.0.0", r.stdout)


if __name__ == "__main__":
    unittest.main()
