# IPC Starter Kit (v1.0.0)

An offline infection prevention and control (IPC) starter kit for clinics and hospitals. It includes hand hygiene observation, supply stock monitoring, and printable forms. The app runs from a local HTML file, with six interface languages including Arabic. See the [device matrix](docs/DEVICE-TESTING.md) before entering facility data.

**For IPC education and quality improvement.** Keep protected health information and personal identifiers out of the kit. See the [intended use, privacy guidance, and disclaimer](DISCLAIMER.md).

**Project owner:** [@mostafase](https://github.com/mostafase). Free to download for noncommercial use, with source available. The code uses **PolyForm Noncommercial 1.0.0** and original documentation and training materials use **CC BY-NC-SA 4.0**. See the [license summary](LICENSE.md).

## Commercial waiver requests

Private clinics, for-profit hospitals, and commercial partners can request a **free or low-cost commercial waiver** for uses that help healthcare teams, especially in low-resource settings. Examples include internal use at a clinic, staff training, or distribution to partner facilities.

[Open a licensing request on GitHub](https://github.com/mostafase/offline-ipc-toolkit/issues/new?title=Commercial%20waiver%20request). Include your organization type, intended use, whether you plan to redistribute or charge for any part of it, and how it will help healthcare teams. Keep the request brief and leave patient, staff, and facility records out of public issues. Any exception is subject to written approval from the project owner.

## 1. Quick Start (5 Minutes, Airplane Mode)

1. **Download** the offline release archive `offline-ipc-toolkit-v1.0.0-noncommercial.zip` (no internet access or installation is needed after downloading).
2. **Unzip into ONE permanent folder first** (never run `ipc-kit.html` from inside a `.zip` preview):
   - **Windows 10/11:** Right-click the `.zip` → **Extract All…** into a fixed local folder such as `C:\ipc-starter-kit\`. Open `START-HERE.html` or `ipc-kit.html` in Edge, Chrome, or Firefox.
   - **macOS:** Extract in Finder into `~/ipc-starter-kit/`. **Use Chrome, Firefox, or Edge on macOS** rather than Safari, because recent macOS Safari restricts persistent local `file://` storage across restarts.
   - **Linux:** Extract into `~/ipc-starter-kit/` and open in Firefox or Chromium/Chrome.
   - **Android / LineageOS:** Unzip into internal storage (e.g. `/storage/emulated/0/Download/ipc-starter-kit/`), open `ipc-kit.html` directly in **Firefox for Android** or **Chrome** (all printable sheets & guides work inside `ipc-kit.html`), or see [`docs/DEVICE-TESTING.md`](docs/DEVICE-TESTING.md) Section 2B for WebView / `content://` workarounds.
   - **iPhone / iPad or unsupported phones:** Use the printable paper forms in [`field-kit/index.html`](field-kit/index.html) and enter paper totals on a desktop PC.
3. **Complete a 5-minute practice run:** on first launch, choose your preferred UN language (default English, plus `العربية`, `中文`, `Français`, `Русский`, `Español`) and click **Try a 5-minute practice run** (fictional data kept separate from real facility records):
   - **Step 1 (~2 min):** Answer the 6 practice questions covering overlapping hand hygiene moments, a missed action with gloves, and how to interpret a small sample.
   - **Step 2 (~1 min):** Tally 3 hand hygiene opportunities (including one where two moments occur simultaneously).
   - **Step 3 (~30 s):** Finish the session and read the combined adherence result (`X of Y opportunities, Z%`).
   - **Step 4 (~1 min):** Record one stock issue and inspect the stockout, reorder point, and expiry alerts.
   - **Step 5 (~30 s):** Download a versioned local backup file (`ipc-kit-backup_PRACTICE_YYYY-MM-DD_HHMM_v1.json`).

---

## 2. What Is Included

| Path | Description |
| :--- | :--- |
| [`START-HERE.html`](START-HERE.html) | One-page offline entry point linking the app, printable field kit, and guides |
| [`ipc-kit.html`](ipc-kit.html) | Self-contained, single-file offline web application (HTML + CSS + JS, strict CSP blocking all network access, **6 UN languages** incl. Arabic RTL, UTF-8 BOM CSV export, built-in printable kit & guides) |
| [`field-kit/index.html`](field-kit/index.html) | Printable implementation kit (A4 & US Letter, black-and-white friendly, no scripts) |
| [`field-kit/ALL-PRINTABLE-SHEETS.html`](field-kit/ALL-PRINTABLE-SHEETS.html) | All 8 printable sheets combined into a single self-contained file (same-page links; works over Android `content://`) |
| [`field-kit/quick-start.html`](field-kit/quick-start.html) | One-page quick start for observers, storekeepers, and IPC focal persons |
| [`field-kit/hand-hygiene-observation-sheet.html`](field-kit/hand-hygiene-observation-sheet.html) | One-page 20-opportunity tally sheet and session totals box |
| [`field-kit/stock-card-and-count-sheet.html`](field-kit/stock-card-and-count-sheet.html) | Printable stock card (page 1) and physical count sheet (page 2) |
| [`field-kit/readiness-checklist.html`](field-kit/readiness-checklist.html) | One-page IPC & WASH readiness checklist (water, soap, hand rub, cleaning supplies, waste & sharps) |
| [`field-kit/review-routine-and-action-log.html`](field-kit/review-routine-and-action-log.html) | 30-minute monthly review routine for the IPC lead and role-based corrective action log |
| [`field-kit/practice-scenarios.html`](field-kit/practice-scenarios.html) | Printable 6-scenario training exercise and answer key |
| [`field-kit/data-handling-plan.html`](field-kit/data-handling-plan.html) | Fill-in facility data-handling, backup, retention, and privacy plan |
| [`field-kit/ipc-lead-review-and-pilot-checklist.html`](field-kit/ipc-lead-review-and-pilot-checklist.html) | Pre-deployment local IPC lead review and 2–4 week pilot checklist |
| [`evidence/evidence-register.html`](evidence/evidence-register.html) & [`.csv`](evidence/evidence-register.csv) | Offline evidence register linking metrics, checklist items, and training claims to sources and separating facility choices |
| [`docs/DEVICE-TESTING.md`](docs/DEVICE-TESTING.md) | Tested device/browser matrix, Windows/macOS/Linux/Android/iOS opening instructions, and 10-minute field test protocol |
| [`docs/TRANSLATING.md`](docs/TRANSLATING.md) | Guide to reviewing the 6 built-in UN languages (`en`, `ar` RTL, `zh`, `fr`, `ru`, `es`) and adding local languages |
| [`sample-data/`](sample-data/) | Synthetic (fictional) sample backup JSON and aggregate hand hygiene & stock CSV reports |
| [`tools/ipc_tool.py`](tools/ipc_tool.py) | Optional Python 3 (standard library only) desktop helper to verify backups and combine CSV reports |
| [`tests/`](tests/) | Automated unit tests (`test_core.js`, `test_ipc_tool.py`) and headless Firefox BiDi E2E suite (`test_browser_e2e.py`) |
| [`RELEASE-NOTES.md`](RELEASE-NOTES.md) | `v1.0.0` release summary, review fixes, verification scope, and device/rollout status |
| [`LICENSE.md`](LICENSE.md) | License summary and links to the code and content terms |

---

## 3. Core Rules Implemented

### Tool 1: Hand Hygiene Observation
- **Tally & Paper Entry:** Observers can record live observations on the quick tally screen or enter session totals from [`field-kit/hand-hygiene-observation-sheet.html`](field-kit/hand-hygiene-observation-sheet.html).
- **Simultaneous Moments = One Opportunity:** Observers tick all applicable WHO hand hygiene moments (`M1`–`M5`) and tap one outcome (`Hand rub`, `Handwash`, or `Missed`). When multiple moments occur together (for example, `M4` after touching Patient A and `M1` before touching Patient B), they count as **one opportunity** in the overall denominator while recording each moment's indication.
- **Adherence Calculation & Display:**
  $$\text{Observed adherence (\%)} = 100 \times \frac{\text{actions performed (hand rub + handwash)}}{\text{observed opportunities}}$$
  - Always displays underlying counts alongside the percentage (for example, `8 of 10 opportunities, 80%`).
  - Displays `No observations` when the denominator is zero (`0` opportunities).
  - Never rounds an imperfect result to `100%` (shows `>99%`) or a non-zero result to `0%` (shows `<1%`).
- **Combining Sessions:** Sessions are combined by **summing their counts first** before calculating the percentage (never by averaging session percentages).
- **Small-Sample Warning:** Groups with fewer than the locally configured threshold (default `200` opportunities, configurable in **Settings**) are flagged `Small sample – interpret with care`.
- **Grouped Storage Only:** Saves only grouped counts by month (`YYYY-MM`) and facility-approved area code (for example, `OPD`, `MAT`, `WARD-A`).

### Tool 2: IPC Supply Stock Monitoring
- **Consistent Unit per Item:** Each supply item has one unit (such as `bottle (500 mL)` or `box (100 gloves)`), which is locked once any transaction is recorded.
- **Transactions:** Supports `Receipt`, `Issue`, `Physical count` (which sets the batch balance to the counted quantity), and `Adjustment` (using coded reasons: `expired`, `damaged`, `lost`, `transfer_out`, `found`, `transfer_in`, `correction`).
- **FEFO & Expiry Exclusion:**
  - Expired batches (`expiry < today`) are **excluded from usable stock totals** and flagged for removal (`Expired: X unit – not usable`). An item whose only remaining batches are expired is reported as a `STOCKOUT` (`0` usable).
  - Usable batches are ordered by **earliest expiry date first** (`Use first`, First-to-Expire, First-Out / FEFO), and stock issues draw from the earliest-expiring usable batch available on the issue date. Enter the expiry shown on the label for every new batch.
- **Configurable Alerts:** Facility-level default expiry alert window (default `90` days) and per-item reorder points and alert windows are configurable by the facility.

---

## 4. Offline Use, Privacy, and Security Safeguards

### Data the kit is designed to handle
- **Strict Data Model:** Neither the web app nor the printable forms contain fields for patient names, staff names, observer names, individual IDs, clinical details, dates/times of individual patient encounters, photos, or free-text observation notes.
- **Schema Allowlist Enforcement:** Both `ipc-kit.html` and `tools/ipc_tool.py` enforce an exact property allowlist (`keysExactly`) and CRC32 checksum when validating backups. Any backup file that is corrupted, fails checksum verification, or contains an unexpected property (such as `"staffName"` or `"note"`) is **rejected before any data is replaced**, leaving existing data intact. CRC32 checks for accidental corruption. Permitted text fields such as facility labels, item names, and batch codes still require care. Keep identifiers out of them.
- **Separate Review Requirement for Any Future PHI Workflow:** This starter kit is designed exclusively for aggregate IPC programme monitoring without personal identifiers. **Any future workflow that introduces Protected Health Information (PHI) or personally identifiable staff/patient data is out of scope for this kit and must undergo a separate, deployment-specific privacy and security review** (including administrative, physical, and technical safeguards; see [HHS HIPAA Security Rule guidance](https://www.hhs.gov/hipaa/for-professionals/security/laws-regulations/index.html)).

### Local Operational Safeguards
Facilities must complete and sign [`field-kit/data-handling-plan.html`](field-kit/data-handling-plan.html) before entering real data:
1. **Save Status & Browser Storage:** The header shows `✔ Saved on this device HH:MM` after every change, or a red warning if browser storage is blocked. Because `localStorage` is tied to one browser profile and file path on one device, keep `ipc-kit.html` in a single fixed folder and do not use private/incognito windows or "clear browsing data".
2. **Approved Storage & Backup Locations:** Make a versioned local backup (`Backup > Download backup file`) at least weekly and store backup files only in the facility's approved location (such as a locked facility computer or an encrypted USB drive kept in a locked cabinet).
3. **Device Locks:** Require a screen lock (PIN or password) on every computer, tablet, or phone used with the kit.
4. **Cloud-Sync Settings:** Disable automatic cloud sync (OneDrive, Google Drive, iCloud, Dropbox) on the browser's `Downloads` folder and the backup folder unless that cloud service is explicitly approved by the facility. Do not send backup JSON files over unapproved email or messaging apps.
5. **Retention:** Define a local retention schedule in the data-handling plan for old backup files and paper tally sheets.
6. **Review of Small Groups Before Sharing:** Before exporting or sharing aggregate CSV/printed reports outside the IPC team, review any period/area with a small number of observations (`< 200` opportunities by default) to avoid over-interpreting small denominators. Assess identification risk separately for all reports, including whether the recipient could link them with other information. The 200-opportunity flag is a sampling cue.

---

## 5. Device & Browser Verification Summary

The device matrix records verification from the original build. Repeat end-to-end checks on the revised package before rollout. Full opening instructions and the 10-minute field test protocol are in [`docs/DEVICE-TESTING.md`](docs/DEVICE-TESTING.md).

| Platform | Tested Setup | Status | Notes |
| :--- | :--- | :--- | :--- |
| **Desktop Linux** | Linux (`x86_64`) + **Mozilla Firefox 158.0.1** (`file://`) | **VERIFIED (PASS)** | Fresh offline launch from unzipped release package, all **6 UN languages** (`en`, `ar` RTL, `zh`, `fr`, `ru`, `es`), 5-minute practice run, overlapping moments, `2/2 + 6/8 -> 8/10 (80%)`, zero observations (`No observations`), `6 on hand / 4 expired -> 2 usable`, stockouts & FEFO/adjustments, UTF-8 BOM CSV export, `localStorage` persistence across full browser quit & reopen, valid + earlier backup restore, invalid backup rejection, and printable field-kit PDF checks verified via `tests/test_browser_e2e.py`. |
| **Desktop Windows / macOS** | Chrome, Edge, Firefox, Safari | **Needs local verification** | On **macOS**, prefer Chrome/Firefox/Edge over Safari for persistent `file://` storage; run **Settings > Check this device** and the 10-minute protocol in `docs/DEVICE-TESTING.md`. |
| **Android / LineageOS** | LineageOS Browser (Jelly) / `content://` / Scoped Storage | **WebView limits (`ERR_FILE_NOT_FOUND` + blocked Print/Save) + built-in fallbacks** | Built-in Printable Kit & guides open directly inside `ipc-kit.html` without cross-file `ERR_FILE_NOT_FOUND` links (and `field-kit/ALL-PRINTABLE-SHEETS.html` works standalone). In **LineageOS Browser (Jelly)** and stock Android WebView, JS `window.print()` and `blob:` Save buttons are silent no-ops by OS design: the app detects WebView, auto-opens copyable text boxes with **Copy text**, and provides **Clean print view** for browser menu (`⋮ → Share / Print`). Use **Firefox for Android** or **Chrome** for direct Print/PDF & file downloads (`docs/DEVICE-TESTING.md` Section 2B). |
| **iPhone / iPad** | iOS / iPadOS Files preview & Safari | **Needs local verification (use paper fallback)** | iOS Files preview and Safari normally do not support persistent storage for local `file://` HTML files; use the printable forms in `field-kit/` and enter totals on a desktop computer. |

---

## 6. Optional Python Desktop Helper & Automated Tests

The app itself requires only a web browser. For desktop workflows where Python 3.8+ is available (standard library only, no third-party packages), [`tools/ipc_tool.py`](tools/ipc_tool.py) provides two read-only commands (use `py -3` or `python` on Windows, `python3` on macOS/Linux):

```bash
# 1. Verify one or more backup files before relying on them
python3 tools/ipc_tool.py check-backup sample-data/practice-backup.json

# 2. Combine hand hygiene CSV reports from multiple areas, months, or facilities
#    (sums underlying counts first, then recalculates adherence %, handles UTF-8 BOM cleanly)
python3 tools/ipc_tool.py combine-reports \
  sample-data/practice-report-hand-hygiene.csv \
  tests/fixtures/second-report-hand-hygiene.csv \
  --by area
```

### Running the Automated Test Suite
```bash
# Core calculation, validation, and 6-UN-language parity unit tests (29 tests, Node 18+)
node tests/test_core.js

# Python desktop helper & cross-language checksum tests (18 tests, Python 3 stdlib)
python3 -m unittest tests/test_ipc_tool.py -v

# End-to-end headless Firefox BiDi browser test over file:// (2 test suites, Python 3 stdlib + Firefox)
python3 -m unittest tests/test_browser_e2e.py -v
```

---

## 7. Evidence Register, Reuse Terms, and Licensing

- **Offline Evidence Register:** See [`evidence/evidence-register.html`](evidence/evidence-register.html) and [`evidence/evidence-register.csv`](evidence/evidence-register.csv). Facility-configurable parameters (`HH-07`, `ST-08`, `ST-09`) and kit design choices are explicitly separated from published WHO/USAID/HHS guidance. Because source PDFs could not be fetched in the offline build environment, section citations for published guidance are marked **`Not yet verified against source text – check during local IPC lead review`** and must be checked using [`field-kit/ipc-lead-review-and-pilot-checklist.html`](field-kit/ipc-lead-review-and-pilot-checklist.html) before clinical rollout.
- **Clinical Translation Review:** Built-in non-English UI packs (**Arabic `ar`**, **Chinese `zh`**, **French `fr`**, **Russian `ru`**, and **Spanish `es`**) are draft reference translations and must be reviewed by a fluent local clinical reviewer before use in patient care areas ([`docs/TRANSLATING.md`](docs/TRANSLATING.md)).
- **No Third-Party Content Bundled:** All training scenarios, checklists, and UI text use original wording. No third-party graphics or copyrighted excerpts are bundled.
- **Project licenses:**
  - Original software and source code (`ipc-kit.html`, `tools/`, `tests/`): **[PolyForm Noncommercial 1.0.0](LICENSE)**.
  - Original training materials, printable field kit sheets, and documentation (`field-kit/`, `evidence/`, `docs/`, `README.md`, `START-HERE.html`): **[Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)](LICENSE-CONTENT.md)**.
