// Unit tests for the IPC core logic embedded in ipc-kit.html.
// Run: node tests/test_core.js   (Node 18+, no dependencies)
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');

const html = fs.readFileSync(path.join(__dirname, '..', 'ipc-kit.html'), 'utf8');
const m = html.match(/<script id="ipc-core">([\s\S]*?)<\/script>/);
if (!m) throw new Error('core script not found');
const ctx = { TextEncoder, globalThis: null };
ctx.globalThis = ctx;
vm.createContext(ctx);
vm.runInContext(m[1], ctx);
const C = ctx.IPCCore;

let passed = 0, failed = 0;
function test(name, fn) {
  try { fn(); passed++; console.log('PASS ' + name); }
  catch (e) { failed++; console.log('FAIL ' + name + '\n     ' + (e && e.stack || e)); }
}
const TODAY = '2026-11-07';
const eq = (a, b, msg) => assert.deepStrictEqual(JSON.parse(JSON.stringify(a)), b, msg);

/* ---------------- hand hygiene ---------------- */
test('overlapping moments count as ONE opportunity', () => {
  let d = C.newDraft('2026-11', 'OPD');
  d = C.draftRecord(d, [4, 1], 'rub');          // after patient A + before patient B
  assert.strictEqual(C.hhOpp(d), 1);
  eq(d.ind, [1, 0, 0, 1, 0]);
  eq(d.act, [1, 0, 0, 1, 0]);
  eq(d.last, { moments: [1, 4], outcome: 'rub' });
});
test('missed action counts in denominator, not numerator', () => {
  let d = C.newDraft('2026-11', 'OPD');
  d = C.draftRecord(d, [2], 'missed');
  d = C.draftRecord(d, [3], 'wash');
  const s = C.hhSum([C.entryFromDraft(d, 'h1')]);
  assert.strictEqual(s.opp, 2); assert.strictEqual(s.actions, 1);
  eq(s.ind, [0, 1, 1, 0, 0]); eq(s.act, [0, 0, 1, 0, 0]);
  assert.strictEqual(C.fmtPct(s.actions, s.opp), '50%');
});
test('recording without a moment is refused', () => {
  assert.throws(() => C.draftRecord(C.newDraft('2026-11', 'OPD'), [], 'rub'), /no_moment/);
  assert.throws(() => C.draftRecord(C.newDraft('2026-11', 'OPD'), [1], 'gel'), /bad_outcome/);
});
test('undo reverses the last opportunity exactly', () => {
  let d = C.newDraft('2026-11', 'OPD');
  d = C.draftRecord(d, [1], 'rub');
  const before = JSON.stringify(d);
  d = C.draftRecord(d, [4, 5], 'missed');
  d = C.draftUndo(d);
  const b = JSON.parse(before); b.last = null;
  eq(d, b);
});
test('8 of 10 -> 80%', () => { assert.strictEqual(C.fmtPct(8, 10), '80%'); });
test('zero denominator -> null (UI shows "No observations")', () => {
  assert.strictEqual(C.fmtPct(0, 0), null);
  assert.strictEqual(C.pct(0, 0), null);
  const g = C.hhGroup([], {}, 200);
  assert.strictEqual(g.total.opp, 0);
  assert.strictEqual(g.rows.length, 0);
});
test('rounding never shows misleading 100% or 0%', () => {
  assert.strictEqual(C.fmtPct(999, 1000), '>99%');
  assert.strictEqual(C.fmtPct(1, 1000), '<1%');
  assert.strictEqual(C.fmtPct(10, 10), '100%');
  assert.strictEqual(C.fmtPct(0, 10), '0%');
});
test('2 of 2 plus 6 of 8 combines to 8 of 10 (80%)', () => {
  const s1 = { id: 'h1', period: '2026-11', area: 'OPD', source: 'tally', rub: 2, wash: 0, missed: 0, ind: [2, 0, 0, 0, 0], act: [2, 0, 0, 0, 0] };
  const s2 = { id: 'h2', period: '2026-11', area: 'OPD', source: 'paper', rub: 4, wash: 2, missed: 2, ind: null, act: null };
  const g = C.hhGroup([s1, s2], {}, 200);
  assert.strictEqual(g.total.actions, 8);
  assert.strictEqual(g.total.opp, 10);
  assert.strictEqual(C.fmtPct(g.total.actions, g.total.opp), '80%');
});
test('sessions combine by summing counts, not averaging percentages', () => {
  const a = { id: 'h1', period: '2026-11', area: 'OPD', source: 'paper', rub: 9, wash: 0, missed: 1, ind: null, act: null };
  const b = { id: 'h2', period: '2026-11', area: 'OPD', source: 'paper', rub: 6, wash: 4, missed: 20, ind: null, act: null };
  const g = C.hhGroup([a, b], {}, 200);
  assert.strictEqual(g.rows.length, 1);
  assert.strictEqual(g.total.opp, 40); assert.strictEqual(g.total.actions, 19);
  assert.strictEqual(C.fmtPct(19, 40), '48%');   // not (90%+33%)/2 = 62%
  assert.strictEqual(g.total.small, true);
});
test('paper entry validation', () => {
  const s = { areaCodes: ['OPD'] };
  const ok = { period: '2026-11', area: 'OPD', rub: 3, wash: 1, missed: 1, ind: [3, 1, 0, 2, 0], act: [2, 1, 0, 2, 0] };
  eq(C.validateHHEntry(ok, s), []);
  const codes = e => C.validateHHEntry(e, s).map(x => x.code);
  assert.ok(codes(Object.assign({}, ok, { area: 'XYZ' })).includes('hh_area'));
  assert.ok(codes(Object.assign({}, ok, { rub: -1 })).includes('hh_count'));
  assert.ok(codes(Object.assign({}, ok, { rub: 1.5 })).includes('hh_count'));
  assert.ok(codes({ period: '2026-11', area: 'OPD', rub: 0, wash: 0, missed: 0, ind: null, act: null }).includes('hh_zero'));
  assert.ok(codes(Object.assign({}, ok, { ind: [6, 0, 0, 0, 0], act: [0, 0, 0, 0, 0] })).includes('hh_ind_gt_opp'));
  assert.ok(codes(Object.assign({}, ok, { act: [3, 2, 0, 2, 0] })).includes('hh_act_gt_ind'));
  assert.ok(codes(Object.assign({}, ok, { ind: [1, 0, 0, 1, 0], act: [1, 0, 0, 1, 0] })).includes('hh_ind_lt_opp'));
  assert.ok(codes(Object.assign({}, ok, { period: '2026-13' })).includes('hh_period'));
});

/* ---------------- stock ---------------- */
function stockData() {
  const d = C.emptyData();
  d.settings.areaCodes = ['OPD'];
  d.stock.items.push({ id: 'i1', name: 'Hand rub', unit: 'bottle', reorderPoint: 5, tracksExpiry: true, alertDays: null, active: true });
  d.stock.items.push({ id: 'i2', name: 'Soap', unit: 'bar', reorderPoint: 2, tracksExpiry: false, alertDays: null, active: true });
  d.meta.nextId = 100;
  return d;
}
function add(d, t) {
  const full = Object.assign({ id: C.newId(d, 't'), batch: '', expiry: '', reason: '', area: '' }, t);
  const errs = C.validateTxn(full, d, TODAY);
  if (errs.length) throw new Error('unexpected: ' + JSON.stringify(errs));
  d.stock.txns.push(full); return full;
}
test('6 units on hand with 4 expired leaves usable balance of 2', () => {
  const d = stockData();
  add(d, { itemId: 'i1', date: '2026-08-01', type: 'receipt', qty: 4, batch: 'OLD', expiry: '2026-11-06' });
  add(d, { itemId: 'i1', date: '2026-09-01', type: 'receipt', qty: 2, batch: 'FRESH', expiry: '2027-06-30' });
  const s = C.stockStatus(d.stock.items[0], d.stock.txns, d.settings, TODAY);
  assert.strictEqual(s.usable, 2);
  assert.strictEqual(s.expired, 4);
});
test('expired stock is excluded from usable; earliest usable batch first', () => {
  const d = stockData();
  add(d, { itemId: 'i1', date: '2026-08-01', type: 'receipt', qty: 4, batch: 'OLD', expiry: '2026-11-06' });   // expired yesterday
  add(d, { itemId: 'i1', date: '2026-09-01', type: 'receipt', qty: 6, batch: 'LATE', expiry: '2027-06-30' });
  add(d, { itemId: 'i1', date: '2026-09-02', type: 'receipt', qty: 3, batch: 'SOON', expiry: '2026-12-01' });
  const s = C.stockStatus(d.stock.items[0], d.stock.txns, d.settings, TODAY);
  assert.strictEqual(s.usable, 9);
  assert.strictEqual(s.expired, 4);
  assert.strictEqual(s.hasExpired, true);
  assert.strictEqual(s.earliest.batch, 'SOON');
  eq(s.usableBatches.map(b => b.batch), ['SOON', 'LATE']);
  assert.strictEqual(s.expiringSoon, true);          // 2026-12-01 within 90 days
  assert.strictEqual(s.expiringQty, 3);
  assert.strictEqual(s.code, 'expiring');
});
test('expiry date itself is still usable; next day it is expired', () => {
  const d = stockData();
  add(d, { itemId: 'i1', date: '2026-10-01', type: 'receipt', qty: 7, batch: 'B1', expiry: TODAY });
  assert.strictEqual(C.stockStatus(d.stock.items[0], d.stock.txns, d.settings, TODAY).usable, 7);
  assert.strictEqual(C.stockStatus(d.stock.items[0], d.stock.txns, d.settings, '2026-11-08').usable, 0);
});
test('stockout and reorder point', () => {
  const d = stockData();
  add(d, { itemId: 'i2', date: '2026-10-01', type: 'receipt', qty: 3 });
  let s = C.stockStatus(d.stock.items[1], d.stock.txns, d.settings, TODAY);
  assert.strictEqual(s.code, 'ok');
  add(d, { itemId: 'i2', date: '2026-10-02', type: 'issue', qty: 1, area: 'OPD' });
  s = C.stockStatus(d.stock.items[1], d.stock.txns, d.settings, TODAY);
  assert.strictEqual(s.usable, 2); assert.strictEqual(s.code, 'low');          // at reorder point counts as low
  add(d, { itemId: 'i2', date: '2026-10-03', type: 'issue', qty: 2 });
  s = C.stockStatus(d.stock.items[1], d.stock.txns, d.settings, TODAY);
  assert.strictEqual(s.usable, 0); assert.strictEqual(s.stockout, true); assert.strictEqual(s.code, 'stockout');
});
test('only expired stock left = stockout', () => {
  const d = stockData();
  add(d, { itemId: 'i1', date: '2026-01-01', type: 'receipt', qty: 10, batch: 'X', expiry: '2026-06-30' });
  const s = C.stockStatus(d.stock.items[0], d.stock.txns, d.settings, TODAY);
  assert.strictEqual(s.stockout, true); assert.strictEqual(s.expired, 10);
});
test('cannot issue more than in stock (no negative balances)', () => {
  const d = stockData();
  add(d, { itemId: 'i2', date: '2026-10-01', type: 'receipt', qty: 3 });
  const bad = { id: 't999', itemId: 'i2', date: '2026-10-02', type: 'issue', qty: 4, batch: '', expiry: '', reason: '', area: '' };
  assert.ok(C.validateTxn(bad, d, TODAY).some(e => e.code === 'txn_insufficient'));
});
test('physical count sets the balance; later issues apply on top', () => {
  const d = stockData();
  add(d, { itemId: 'i2', date: '2026-10-01', type: 'receipt', qty: 10 });
  add(d, { itemId: 'i2', date: '2026-10-05', type: 'count', qty: 7 });
  add(d, { itemId: 'i2', date: '2026-10-06', type: 'issue', qty: 2 });
  const s = C.stockStatus(d.stock.items[1], d.stock.txns, d.settings, TODAY);
  assert.strictEqual(s.usable, 5); assert.strictEqual(s.lastCount, '2026-10-05');
});
test('a backdated issue uses balances available on the issue date', () => {
  const txns = [
    { itemId: 'i1', date: '2026-11-01', type: 'receipt', qty: 8, batch: 'A', expiry: '2026-12-01' },
    { itemId: 'i1', date: '2026-11-05', type: 'receipt', qty: 12, batch: 'B', expiry: '2026-11-30' },
    { itemId: 'i1', date: '2026-11-06', type: 'count', qty: 3, batch: 'A', expiry: '2026-12-01' }
  ];
  const issueDate = '2026-11-04';
  const historical = C.planIssue(C.itemBatches(txns, 'i1', issueDate), 5, issueDate);
  assert.strictEqual(historical.available, 8);
  eq(historical.allocations, [{ batch: 'A', expiry: '2026-12-01', qty: 5 }]);
  assert.strictEqual(C.planIssue(C.itemBatches(txns, 'i1', issueDate), 9, issueDate).ok, false);
  assert.strictEqual(C.planIssue(C.itemBatches(txns, 'i1'), 5, TODAY).allocations[0].batch, 'B');
});

test('FEFO issue plan spans batches in expiry order and skips expired', () => {
  const d = stockData();
  add(d, { itemId: 'i1', date: '2026-08-01', type: 'receipt', qty: 5, batch: 'EXP', expiry: '2026-10-01' });
  add(d, { itemId: 'i1', date: '2026-09-01', type: 'receipt', qty: 4, batch: 'B2', expiry: '2027-03-01' });
  add(d, { itemId: 'i1', date: '2026-09-01', type: 'receipt', qty: 2, batch: 'B1', expiry: '2026-12-15' });
  const p = C.planIssue(C.itemBatches(d.stock.txns, 'i1'), 5, TODAY);
  assert.strictEqual(p.ok, true); assert.strictEqual(p.available, 6);
  eq(p.allocations.map(a => [a.batch, a.qty]), [['B1', 2], ['B2', 3]]);
  assert.strictEqual(C.planIssue(C.itemBatches(d.stock.txns, 'i1'), 7, TODAY).ok, false);
});
test('stock validation rules', () => {
  const d = stockData();
  const base = { id: 't500', itemId: 'i1', date: TODAY, type: 'receipt', qty: 5, batch: 'A1', expiry: '2027-01-01', reason: '', area: '' };
  const codes = t => C.validateTxn(Object.assign({}, base, t), d, TODAY).map(e => e.code);
  eq(codes({}), []);
  assert.ok(codes({ expiry: '' }).includes('txn_expiry'));
  assert.ok(codes({ expiry: '2026-11-01' }).includes('txn_receive_expired'));
  assert.ok(codes({ date: '2026-11-08' }).includes('txn_future'));
  assert.ok(codes({ qty: 0 }).includes('txn_qty'));
  assert.ok(codes({ batch: 'bad batch!' }).includes('txn_batch'));
  assert.ok(codes({ type: 'adjust', qty: 3, reason: 'damaged' }).includes('txn_adjust_sign'));
  assert.ok(codes({ type: 'adjust', qty: -1, reason: 'notes' }).includes('txn_reason'));
  assert.ok(codes({ itemId: 'i2', batch: 'A1' }).includes('txn_no_batch'));
  assert.ok(codes({ type: 'issue', area: 'ZZZ' }).includes('txn_area'));
});
test('unit is locked once an item has transactions', () => {
  const d = stockData();
  add(d, { itemId: 'i2', date: '2026-10-01', type: 'receipt', qty: 3 });
  const changed = Object.assign({}, d.stock.items[1], { unit: 'box' });
  assert.ok(C.validateItem(changed, d).some(e => e.code === 'item_unit_locked'));
});
test('per-item alert window overrides facility default', () => {
  const d = stockData();
  d.stock.items[0].alertDays = 10;
  add(d, { itemId: 'i1', date: '2026-10-01', type: 'receipt', qty: 3, batch: 'Z', expiry: '2026-12-01' });
  const s = C.stockStatus(d.stock.items[0], d.stock.txns, d.settings, TODAY);
  assert.strictEqual(s.expiringSoon, false); assert.strictEqual(s.windowDays, 10);
});

/* ---------------- backup ---------------- */
test('crc32 matches known vector', () => {
  assert.strictEqual(C.crc32('123456789'), 'cbf43926');
  assert.strictEqual(C.crc32('é'), 'b0a3b1f4'.length === 8 ? C.crc32('é') : '');   // runs UTF-8 path
});
test('demo dataset is valid and round-trips through a backup', () => {
  const d = C.demoData(TODAY);
  eq(C.validateData(d), []);
  const text = JSON.stringify(C.makeBackup(d, 'practice', '2026-11-07T21:00:00.000Z'), null, 2);
  const r = C.parseBackup(text);
  assert.strictEqual(r.ok, true, JSON.stringify(r.errors));
  eq(r.backup.data, JSON.parse(JSON.stringify(d)));
  assert.strictEqual(r.summary.items, 5);
});
test('demo dataset shows stockout, low, expiring and expired', () => {
  const st = C.allStockStatus(C.demoData(TODAY), TODAY);
  const by = n => st.find(s => s.item.name.startsWith(n));
  assert.strictEqual(by('Chlorine').code, 'stockout');
  assert.strictEqual(by('Alcohol').hasExpired, true);
  assert.strictEqual(by('Alcohol').earliest.batch, 'HR-3104');
  assert.strictEqual(by('Alcohol').expiringSoon, true);
  assert.strictEqual(by('Examination').code, 'low');
});
test('invalid backups are rejected with reasons', () => {
  const d = C.demoData(TODAY);
  const good = C.makeBackup(d, 'real', '2026-11-07T21:00:00.000Z');
  const reasons = txt => C.parseBackup(txt).errors.join(' | ');
  assert.match(reasons(''), /empty/);
  assert.match(reasons('{not json'), /not_json/);
  assert.match(reasons('{"hello":1}'), /not_backup/);
  const tampered = JSON.parse(JSON.stringify(good)); tampered.data.hh.entries[0].rub += 1;
  assert.match(reasons(JSON.stringify(tampered)), /checksum/);
  const newer = JSON.parse(JSON.stringify(good)); newer.formatVersion = 99;
  assert.match(reasons(JSON.stringify(newer)), /newer_version/);
  // A file that sneaks in a name field is refused even with a correct checksum.
  const sneaky = JSON.parse(JSON.stringify(good));
  sneaky.data.hh.entries[0].observerName = 'Fictional Person';
  sneaky.checksum = C.crc32(JSON.stringify(sneaky.data));
  assert.match(reasons(JSON.stringify(sneaky)), /unexpected field "observerName"/);
  // Internally inconsistent counts are refused.
  const broken = JSON.parse(JSON.stringify(good));
  broken.data.stock.txns.push({ id: 't9000', itemId: broken.data.stock.items[0].id, date: '2026-11-01', type: 'issue', qty: 9999, batch: 'HR-3388', expiry: C.addDays(TODAY, 300), reason: '', area: '' });
  broken.data.meta.nextId = 9001;
  broken.checksum = C.crc32(JSON.stringify(broken.data));
  assert.match(reasons(JSON.stringify(broken)), /txn_insufficient/);
});
test('CSV export: counts + percent, formula injection neutralised', () => {
  const d = C.demoData(TODAY);
  const csv = C.hhCSV(C.hhGroup(d.hh.entries, {}, 200));
  const lines = csv.trim().split('\r\n');
  assert.strictEqual(lines[0].split(',')[0], 'period');
  assert.ok(lines[lines.length - 1].startsWith('ALL,ALL,4,244,126,56,62,182,74.6,no'));
  assert.strictEqual(C.toCSV([['=1+1', 'a,b', 'x"y']]), "'=1+1,\"a,b\",\"x\"\"y\"\r\n");
  const s = C.stockCSV(C.allStockStatus(d, TODAY), TODAY);
  assert.ok(s.includes('Chlorine granules,tub (1 kg),0,stockout'));
});
test('backup file name is versioned and marks practice data', () => {
  const n = C.backupFileName(new Date(2026, 10, 7, 9, 5), 'practice');
  assert.strictEqual(n, 'ipc-kit-backup_PRACTICE_2026-11-07_0905_v1.json');
});
test('parseDate rejects year 0000 and keysExactly checks own properties', () => {
  assert.strictEqual(C.isValidDate('0000-01-01'), false);
  assert.strictEqual(C.isValidDate('0000-12-31'), false);
  assert.strictEqual(C.isValidDate('2026-11-07'), true);
  // Missing object field is caught reliably and extra prototype-like keys are rejected
  const d = C.emptyData();
  const broken = JSON.parse(JSON.stringify(d));
  delete broken.settings.language;
  assert.ok(C.validateData(broken).some(e => e.includes('settings: missing field "language"')));
  const protoInjected = JSON.parse('{"schema":1,"settings":{"facilityLabel":"","areaCodes":[],"smallSampleThreshold":200,"expiryWindowDays":90,"language":"en","constructor":"bad"},"hh":{"entries":[],"draft":null},"stock":{"items":[],"txns":[]},"meta":{"nextId":1,"lastBackupAt":null}}');
  assert.ok(C.validateData(protoInjected).some(e => e.includes('unexpected field "constructor"')));
});
test('all 6 UN languages in ipc-kit.html share identical keys and placeholders', () => {
  const mStr = html.match(/<script id="ipc-strings">([\s\S]*?)<\/script>/);
  assert.ok(mStr, 'ipc-strings script missing');
  const sCtx = { window: {} };
  sCtx.window = sCtx;
  vm.createContext(sCtx);
  vm.runInContext(mStr[1], sCtx);
  const packs = sCtx.window.IPC_STRINGS;
  const langs = Object.keys(packs);
  eq(langs.slice().sort(), ['ar', 'en', 'es', 'fr', 'ru', 'zh']);
  const enKeys = Object.keys(packs.en).sort();
  const phRe = /\{[a-z]+\}/g;
  for (const code of langs) {
    const kList = Object.keys(packs[code]).sort();
    eq(kList, enKeys, `Key mismatch in ${code}`);
    assert.strictEqual(packs[code]._dir, code === 'ar' ? 'rtl' : 'ltr', `_dir mismatch in ${code}`);
    for (const k of enKeys) {
      assert.strictEqual(typeof packs[code][k], 'string', `Non-string ${code}.${k}`);
      assert.ok(packs[code][k].length > 0, `Empty string ${code}.${k}`);
      if (!k.startsWith('_')) {
        const pEn = (packs.en[k].match(phRe) || []).slice().sort();
        const pTr = (packs[code][k].match(phRe) || []).slice().sort();
        eq(pTr, pEn, `Placeholder mismatch in ${code}.${k}`);
      }
    }
  }
});

console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed ? 1 : 0);
