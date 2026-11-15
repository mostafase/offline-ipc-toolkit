// Generates the synthetic (fictional) sample data shipped in sample-data/.
// It runs the SAME core code that is embedded in ipc-kit.html, so the samples
// always match the app's real formats. Node is a developer tool only; the app
// itself needs nothing but a browser.
//
// Run: node tools/make_sample_data.js
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'ipc-kit.html'), 'utf8');
const m = html.match(/<script id="ipc-core">([\s\S]*?)<\/script>/);
if (!m) throw new Error('core script not found in ipc-kit.html');
const ctx = { TextEncoder };
ctx.globalThis = ctx;
vm.createContext(ctx);
vm.runInContext(m[1], ctx);
const C = ctx.IPCCore;

// Fixed dates so the files are reproducible. All data is fictional.
const TODAY = '2026-11-07';
const CREATED = '2026-11-07T09:05:00.000Z';

function write(rel, text) {
  const p = path.join(ROOT, rel);
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, text);
  console.log('wrote ' + rel + ' (' + Buffer.byteLength(text) + ' bytes)');
}
function plain(o) { return JSON.parse(JSON.stringify(o)); }   // leave the vm realm

// 1. Practice backup (what "Download backup file" produces in practice mode).
const demo = plain(C.demoData(TODAY));
const errs = C.validateData(demo);
if (errs.length) throw new Error('demo data invalid: ' + errs.join('; '));
write('sample-data/practice-backup.json', JSON.stringify(C.makeBackup(demo, 'practice', CREATED), null, 2) + '\n');

// 2. Aggregate report exports (what "Download report (CSV)" produces).
const group = C.hhGroup(demo.hh.entries, {}, demo.settings.smallSampleThreshold);
write('sample-data/practice-report-hand-hygiene.csv', C.hhCSV(group));
write('sample-data/practice-report-stock.csv', C.stockCSV(C.allStockStatus(demo, TODAY), TODAY));

// 3. Test fixture: non-ASCII text, to prove the JS and Python checksums agree on UTF-8.
const uni = plain(C.demoData(TODAY));
uni.settings.facilityLabel = 'Clinique Été – démo';
uni.settings.language = 'fr';
uni.stock.items[1].name = 'Savon liquide (flacon) — démo';
write('tests/fixtures/unicode-backup.json', JSON.stringify(C.makeBackup(uni, 'practice', CREATED), null, 2) + '\n');

// 4. Test fixture: a second facility's report, for the combine-reports test.
const other = plain(C.emptyData());
other.settings.areaCodes = ['OPD'];
other.hh.entries.push({ id: 'h1', period: '2026-10', area: 'OPD', source: 'paper', rub: 9, wash: 0, missed: 1, ind: null, act: null });
other.hh.entries.push({ id: 'h2', period: '2026-11', area: 'OPD', source: 'paper', rub: 6, wash: 4, missed: 20, ind: null, act: null });
other.meta.nextId = 3;
write('tests/fixtures/second-report-hand-hygiene.csv', C.hhCSV(C.hhGroup(other.hh.entries, {}, 200)));
