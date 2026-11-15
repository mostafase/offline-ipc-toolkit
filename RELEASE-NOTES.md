# Release Notes — IPC Starter Kit `v1.0.0`

- **Release Tag:** `v1.0.0`
- **Offline Package Asset:** `offline-ipc-toolkit-v1.0.0-noncommercial.zip`
- **Code License:** PolyForm Noncommercial 1.0.0 (`LICENSE`)
- **Documentation & Printable Training Materials License:** Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0) (`LICENSE-CONTENT.md`)

---

## Review copy

Project owner [@mostafase](https://github.com/mostafase) reported that the toolkit worked on Android and Windows. See the [license summary](LICENSE.md) and [dependency review](docs/DEPENDENCY-REVIEW.md) for this package.

This copy adds the intended-use and privacy disclaimer. Restores now require the backup and app to be in the same mode. New expiry-tracked batches require the label date, and backdated stock issues use available balances on the issue date. The verification below describes the original package. Repeat browser and target-device checks before rollout.

## What Is Included

1. **`START-HERE.html`** — Offline entry page linking the application, quick start, printable sheets, and documentation.
2. **`ipc-kit.html`** — Single-file, 100% offline web application (HTML + CSS + JS with strict `Content-Security-Policy` blocking all network requests) featuring:
   - **Hand Hygiene Observation Tool:** Live tally screen (simultaneous WHO moments = 1 opportunity, `rub`/`wash`/`missed` outcomes, undo), paper totals entry, grouped monthly/area results with underlying counts (`X of Y opportunities, Z%`, `No observations` at zero, small-sample flagging), and a 6-question fictional practice quiz.
   - **IPC Supply Stock Monitoring Tool:** Consistent locked item units, receipts, FEFO issues (earliest-expiring usable batch first), physical counts, coded adjustments (`expired`, `damaged`, `lost`, `transfer_out`, `found`, `transfer_in`, `correction`), expiry exclusion from usable totals, configurable reorder points, and configurable alert windows.
   - **Offline Reporting & Recovery:** Printable reports, formula-injection-neutralised CSV exports with small-group review reminders, CRC32-verified schema-allowlisted `.json` backups (`formatVersion: 1`), safety-copy `Undo restore`, and clipboard text backup/restore fallback.
3. **`field-kit/`** — 8 black-and-white printable sheets (A4 & US Letter, zero scripts) plus `field-kit/index.html`, covering quick start, hand hygiene observation, stock card & physical count, IPC & WASH readiness, monthly review & role-based action log, fictional practice scenarios, facility data-handling plan, and local IPC lead review & pilot checklist.
4. **`evidence/`** — Offline evidence register (`evidence-register.html` & `.csv`) linking metrics, rules, and checklist items to published guidance while visually separating facility-configurable parameters and kit design choices.
5. **`docs/`** — Device opening & 10-minute field testing guide (`DEVICE-TESTING.md`) and translation guide (`TRANSLATING.md`).
6. **`sample-data/` & `tools/ipc_tool.py`** — Synthetic practice backup & aggregate CSV exports plus optional Python 3 (standard library only) desktop verification/report-combining helper.

---

## Release Review Fixes Included in `v1.0.0`

- **Destructive Action & Restore Safeguards (`ipc-kit.html`):**
  - Implemented typed confirmation (`ERASE`) inside `confirmModal` for **Settings > Erase all real data on this device** (`#modalWordInput` keeps confirm disabled until `ERASE` is entered).
  - Added a confirmation modal (`bk_replace_confirm`) before overwriting browser data on backup restore, complementing the automatic safety copy (`Undo restore`).
  - Added explicit `triggerDownload()` failure handling on backup & CSV report downloads so blocked browser downloads automatically open the copyable text fallback instead of showing a misleading success message.
- **Touch Usability & Form Clarity (`ipc-kit.html`):**
  - Enlarged undersized tap targets (area code remove button from `28px` to `44x44px`, and practice Go buttons, session delete buttons, and stock preset/edit buttons to `>=48px`).
  - Added an **Add or remove** direction selector on stock **Adjustment** (`correction` reason), synced the FEFO issue preview with the selected `#txnDate`, and synced physical count quantity when switching batches.
  - Added a check guard (`Choose an answer first`) and live score summary banner (`Score: s of 6`) on the 6-question practice quiz, `placeholder="YYYY-MM"` hints on all month inputs, and active filter summaries in Reports & print view.
- **Documentation, Package Accuracy & Android / LineageOS `content://` Fix (`ipc-kit.html`, `field-kit/`, `START-HERE.html`, `docs/`):**
  - Embedded all 8 printable sheets, `field-kit/index.html`, Combined All-Sheets pack, `evidence/evidence-register.html` (+ `.csv` download), `docs/DEVICE-TESTING.md`, and `docs/TRANSLATING.md` directly inside `ipc-kit.html` via reproducible offline builder `tools/sync_embedded_kit.py` so every sheet opens without cross-file `ERR_FILE_NOT_FOUND` links on Android `content://` URIs.
  - Added Android System WebView (LineageOS **Jelly**) detection and fallbacks across Printable Kit, Reports, Backup, and Settings (`isAndroidWebView()`): because WebView silently ignores JS `window.print()` and `blob:` downloads, `ipc-kit.html` now flags Print/Download honestly in **Check this device**, auto-opens copyable text fallbacks with one-tap **Copy text** buttons (plus **Show HTML text**), and provides **Clean print view** for browser menu (`⋮ → Share / Print`) or screenshots.
  - Added `field-kit/ALL-PRINTABLE-SHEETS.html`, a single zero-script printable file containing all 8 sheets with same-page `#anchor` navigation.
  - Updated `docs/TRANSLATING.md` to match the actual `window.IPC_STRINGS` structure, automatic Settings language selector population, and `{placeholder}` tokens (`{a}`, `{o}`, `{p}`, `{n}`, `{q}`, `{u}`, etc.).
  - Made `README.md` Quick Start concrete (`Download` -> `Unzip` -> `Open` -> `5-Minute Practice Run`) and updated Android / LineageOS guidance in `START-HERE.html`, `field-kit/quick-start.html`, `field-kit/index.html`, and `docs/DEVICE-TESTING.md`.
  - Fixed a spacing typo (`orIPC` -> `or IPC`) in `field-kit/index.html`.

- **Desktop Browser, Core Logic & Multilingual (All 6 UN Languages) Polish (`ipc-kit.html`, `docs/`, `README.md`, `START-HERE.html`, `.gitignore`):**
  - Added full built-in translations for **Arabic (`ar` with RTL layout mirroring)**, **Chinese (`zh`)**, **Russian (`ru`)**, and **Spanish (`es`)** alongside **English (`en`)** and **French (`fr`)** (`405` UI keys per pack with verified key and `{placeholder}` parity). Added `[dir="rtl"]` CSS mirroring while keeping JSON/CSV text boxes (`dir="ltr"`) and embedded English paper sheets legible.
  - Prepended UTF-8 BOM (`\uFEFF`) on CSV downloads in `exportCSV()` so Windows and macOS Excel open Arabic, Chinese, Russian, French, and Spanish characters cleanly without encoding garbling.
  - Hardened core & form validation: `parseDate()` rejects year `0000` (matching Python `date.fromisoformat`), `keysExactly()` uses `Object.prototype.hasOwnProperty.call`, and **Stock > Record > Issue** validates non-empty/valid dates, non-future dates, and positive integer quantities before FEFO batch allocation so invalid input reports exact field errors instead of "Not enough stock".
  - Added Windows / macOS (`Safari` local-file storage caveat, `Chrome/Firefox/Edge` recommendation, `py -3` CLI usage) / Linux / Android guidance and a root `.gitignore` ahead of GitHub publication.

---

## Verification Summary

All checks were executed offline after final edits against both the working tree and a clean extraction of `ipc-starter-kit-v1.0.0-offline.zip`:

- `node tests/test_core.js` — Core calculation, `2/2 + 6/8 -> 8 of 10 (80%)`, `6 on hand / 4 expired -> 2 usable`, year `0000`/prototype key validation, CSV safety, and CRC32 backup tests.
- `python3 -m unittest tests/test_ipc_tool.py -v` — Cross-language UTF-8/CRC32 parity, backup schema rejection, CSV aggregation, and zero-network-import tests.
- `python3 -m unittest tests/test_browser_e2e.py -v` — Headless Mozilla Firefox 158.0.1 WebDriver BiDi end-to-end verification over `file://` (including full key/placeholder parity across all 6 UN languages, Arabic `dir="rtl"` & stock/HH UI rendering, UTF-8 BOM CSV export + `ipc_tool.py` aggregation, Stock Issue validation ordering, opening & printing built-in field-kit sheets inside `ipc-kit.html`, simulated `; wv)` Android WebView detection/Clean print view/Copy fallback checks, verifying `field-kit/ALL-PRINTABLE-SHEETS.html` zero-script CSP, invalid backup rejection, earlier `v1` backup restore, typed `ERASE` guard, tap target height check, strict CSP & zero-script field-kit checks, and A4 PDF print pagination checks).
- Static release hygiene scan confirming zero broken relative HTML links, zero external runtime requests (`src`/`href`/`url`), zero real facility data, and zero credentials or local filesystem paths.

---

## Device Verification Status & Known Limits

| Platform | Status | Guidance |
| :--- | :--- | :--- |
| **Desktop Linux (Firefox 158.0.1, `file://`)** | **Verified (PASS)** | Automated BiDi E2E + clean unzipped package run |
| **Desktop Windows / macOS (Chrome, Edge, Firefox, Safari)** | **Needs local verification** | Follow `docs/DEVICE-TESTING.md` Section 2A & 3 (prefer Chrome/Firefox/Edge over Safari on macOS for persistent `file://` storage) |
| **Android / LineageOS (WebView "Jelly" / Chrome / Firefox)** | **WebView limits (`content://`, blocked Print/Save) + built-in fallbacks** | Built-in Printable Kit & guides open directly inside `ipc-kit.html`, and `field-kit/ALL-PRINTABLE-SHEETS.html` works standalone. Stock WebView (Jelly) silently blocks JS `window.print()` and `blob:` downloads: `ipc-kit.html` now provides **Clean print view** (for browser `⋮ → Share / Print`) and **Copy text** fallbacks; use **Firefox for Android** or **Chrome** for one-tap Print/PDF & downloads (`docs/DEVICE-TESTING.md` Section 2B) |
| **iPhone / iPad (iOS / iPadOS)** | **Needs local verification (use paper fallback)** | Safari and Files preview generally do not support persistent local `file://` storage; use `field-kit/` printable sheets |

**Important Notes & Remaining Pre-Rollout Steps:**
1. **Unverified External Citations:** Because this starter kit was built offline without downloading copyrighted WHO/USAID/HHS PDFs, published guidance rows in `evidence/evidence-register.html` are honestly marked `Not yet verified against source text – check during local IPC lead review` and must be checked using `field-kit/ipc-lead-review-and-pilot-checklist.html`.
2. **UN Language Clinical Review:** All five built-in non-English UN language packs (`ar`, `zh`, `fr`, `ru`, `es`) are draft reference translations and must be reviewed by a fluent local clinical reviewer prior to clinical deployment (`docs/TRANSLATING.md`); the standalone `field-kit/` HTML sheets remain English until locally translated.
3. **Human Second Reviewer & Hardware Pilot:** Only automated Firefox BiDi / agent verification on Desktop Linux has run so far; an independent human second reviewer on clinic target devices (Windows/macOS/Android) is still needed before clinical launch.
4. **Privacy / HIPAA Boundary:** Keep PHI and personal identifiers out of all fields, backups, and exports. The kit makes no claim of HIPAA certification or compliance. Any future workflow that introduces PHI is out of scope and requires a separate, deployment-specific privacy and security review (`LICENSE-CONTENT.md`, `field-kit/data-handling-plan.html`).
5. **No Third-Party Content Bundled:** Original wording throughout; cited third-party WHO, UNICEF, USAID, and HHS works are cited by reference only and excluded from the [project licenses](LICENSE.md).
