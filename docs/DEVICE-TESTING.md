# Device Testing & Opening Guide (`docs/DEVICE-TESTING.md`)

The matrix records results from the original package. Re-run the workflow on the revised package before rollout. For the restore check, use a practice backup in Practice mode and a real-mode backup made with fictional test data in Real mode.



The IPC Starter Kit (`ipc-kit.html`, v1.0.0) is a single-file offline web application that stores records in your browser's local storage (`localStorage`) on that specific device. Because browsers handle `file://` URLs differently across operating systems, always check each device before using it for real facility records.

---

## 1. Tested Combinations

| Device | OS | Browser + version | Open from local file | Save/reload | Backup download | Restore | Print | Result |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Desktop / Laptop PC | Linux (`x86_64`) | Mozilla Firefox 158.0.1 (headless BiDi) | PASS (`file://` from unzipped `ipc-starter-kit-v1.0.0-offline.zip`) | PASS (`localStorage` persisted across full browser quit & reopen) | PASS (`Blob` JSON & UTF-8 BOM CSV download + text fallback) | PASS (valid + earlier `sample-data/practice-backup.json` & UTF-8 backups restored; corrupt, tampered & unexpected-field files rejected intact) | PASS (`@media print` & single-page `field-kit` sheets verified 1 page each via PDF print) | **PASS — Verified** (`tests/test_browser_e2e.py`, incl. all 6 UN languages & Arabic `dir="rtl"`) |
| Desktop / Laptop PC | Windows 10/11 & macOS | Chrome, Edge, Firefox, Safari | — | — | — | — | — | **NOT TESTED** in this build environment (verify locally using Section 2A & Section 3; on macOS prefer Chrome/Firefox over Safari) |
| Android phone/tablet | Android (LineageOS / Chromium WebView "Jelly") | Default LineageOS Browser (Jelly) / `content://` file opener | Partial (`content://` opens single file; `file://` & relative links blocked) | Check with **Settings > Check this device** | Fallback (`blob:` downloads blocked silently; auto-opens **Copy text** box) | Paste text / chosen file | WebView blocks `window.print()` button (use **Clean print view** + menu `⋮ → Share / Print`) | **PARTIAL (WebView limits)** — Built-in Printable Kit & guides open inside `ipc-kit.html`, but Android WebView silently ignores JS Print & `blob:` Save buttons; use **Clean print view** + `⋮`, **Copy text**, or switch to **Firefox for Android** / **Chrome** |
| Android phone/tablet | Android (other browsers: Firefox / Chrome app dir) | Firefox for Android / Chrome | — | — | — | — | — | **NOT TESTED** in this build environment (test locally using Section 2B & Section 3, or use paper forms) |
| iPhone | iOS | Safari / iOS browsers | — | — | — | — | — | **iPhone – NOT TESTED** (no physical device available; Safari blocks local file storage – use paper forms) |
| iPad | iPadOS | Safari / iPadOS browsers | — | — | — | — | — | **iPad – NOT TESTED** (no physical device available; Safari blocks local file storage – use paper forms) |

**Release v1.0.0 Review Record (Who Tested What):**
- **Automated + Clean-Package Agent Review (Desktop Linux, Firefox 158.0.1):** Ran from a clean extraction of `ipc-starter-kit-v1.0.0-offline.zip` following the public `README.md` / `START-HERE.html` quick-start steps offline over `file://`; executed unit, Python helper, and BiDi browser E2E suites (covering all 6 UN languages `en`, `ar` RTL, `zh`, `fr`, `ru`, `es`, plus simulated `; wv)` Android WebView UI checks) and PDF print page-count checks across printable sheets.
- **User Field Reports (Android, LineageOS default browser Jelly):**
  1. Opening `START-HERE.html` or cross-file links (`field-kit/*.html`) failed with **`ERR_FILE_NOT_FOUND`** because WebView blocks `file://` and Android `content://` URIs block sibling links. Resolved by embedding all 8 printable sheets & guides directly inside `ipc-kit.html` plus single-file `field-kit/ALL-PRINTABLE-SHEETS.html`.
  2. Opening the built-in Printable Kit inside `ipc-kit.html` succeeded in LineageOS Jelly, **but tapping `Print / Save PDF` or `Download standalone HTML` did nothing**: Android System WebView leaves JS `window.print()` disconnected and ignores `<a download href="blob:...">` without throwing. Updated `ipc-kit.html` to detect WebView (`; wv)`), report download/print accurately in **Check this device**, auto-open copyable text boxes with a **Copy text** button, and provide **Clean print view** + browser menu (`⋮ → Share or Print`) instructions.
- **Independent Human Second Reviewer:** **NOT YET COMPLETED** for working desktop/Android browser setups (recommended during facility pilot using Section 3 below and `field-kit/ipc-lead-review-and-pilot-checklist.html` before real clinical rollout).

---

## 2. How to Open `ipc-kit.html` by Platform

### A. Windows, macOS, and Linux (Recommended)
1. **Extract (Unzip) first — never run inside a `.zip` preview:**
   - **Windows 10/11:** Right-click `ipc-starter-kit-v1.0.0-offline.zip` → **Extract All…** into a fixed local folder such as `C:\ipc-starter-kit\` (not on a temporary Desktop copy or inside a cloud-synced OneDrive folder unless approved).
   - **macOS:** Double-click the `.zip` archive in Finder and move the extracted `ipc-starter-kit` folder into a fixed location such as your Home folder (`~/ipc-starter-kit/`).
   - **Linux:** Unzip into `~/ipc-starter-kit/` (`unzip ipc-starter-kit-v1.0.0-offline.zip`).
2. **Choose the right desktop browser:**
   - **Windows & Linux:** Double-click `ipc-kit.html`, or drag it into **Firefox**, **Chrome**, or **Edge**.
   - **macOS (Important Safari Note):** Recent **macOS Safari** restricts `file://` storage or treats each local HTML load separately unless special developer settings are enabled. **Use Chrome, Firefox, or Edge on macOS** for reliable local saving, and confirm persistence by closing and reopening the browser (Section 3).
3. **Bookmark & keep the file in ONE fixed folder:** Press `Ctrl+D` (`Cmd+D` on macOS). Browsers link `localStorage` data to the exact file path and browser profile: moving, renaming, or switching browsers shows an empty dataset.
4. **Opening CSV reports in Microsoft Excel / LibreOffice:** Downloaded CSV reports automatically include a **UTF-8 BOM** (`\uFEFF`) so Windows Excel opens Arabic (`ar`), Chinese (`zh`), Russian (`ru`), French (`fr`), and Spanish (`es`) item names cleanly when double-clicked (macOS Numbers and LibreOffice Calc also open them in UTF-8).
5. **Optional desktop helper (`tools/ipc_tool.py`):**
   - **Windows:** Open Command Prompt / PowerShell in the `ipc-starter-kit` folder and run `py -3 tools\ipc_tool.py check-backup sample-data\practice-backup.json` (or `python ...`).
   - **macOS / Linux:** Open Terminal in the `ipc-starter-kit` folder and run `python3 tools/ipc_tool.py check-backup sample-data/practice-backup.json`.

### B. Android & LineageOS Phones and Tablets (Fixing `ERR_FILE_NOT_FOUND` & Jelly Print/Save Limits)
On Android 10+ and LineageOS, stock WebView browsers (including freshly installed **LineageOS Browser / Jelly**) and Android **`content://` / Scoped Storage** have two separate OS limits:

1. **Unzip first & check the folder name:** Extract `ipc-starter-kit-v1.0.0-offline.zip` into internal storage (note the Android folder path is singular **`Download`**, not `Downloads`: e.g. `/storage/emulated/0/Download/ipc-starter-kit/`). Never open HTML files inside a `.zip` preview.
2. **Open `ipc-kit.html` directly (built-in Printable Kit avoids cross-file `ERR_FILE_NOT_FOUND`):** When a file manager opens any HTML page via a `content://` URI, Android grants permission to only that single file—tapping relative links to sibling files (`START-HERE.html` or `field-kit/index.html`) triggers `ERR_FILE_NOT_FOUND`. Because **all 8 printable field-kit sheets, the Evidence Register, and the Guides are built right inside `ipc-kit.html`**, they open offline without leaving the app (outside the app, you can also open **`field-kit/ALL-PRINTABLE-SHEETS.html`** directly from Files).
3. **If you use LineageOS Browser (Jelly) / Android WebView (`Print` or `Save` button does nothing):** Stock Android System WebView does **not** wire web-page `window.print()` buttons or `blob:` file downloads to Android's Print/Download services—so tapping `Print / Save PDF` or `Download` inside Jelly silently does nothing:
   - **To print / save PDF / screenshot from Jelly:** Tap **Clean print view** (available in Printable Kit and Reports) so only the clean form appears, then open Jelly's top-right menu (**`⋮`**) → **Share** (choose **Print** / PDF if listed by your Android print service) or take a screenshot.
   - **To copy HTML, CSV, or backups:** Tap **Show HTML text**, **Download** (automatically opens the text box on WebView), or **Show backup text**, then tap **Copy text** and paste into a local note/editor.
   - **For full one-tap Print/PDF & file downloads (Recommended):** Open `ipc-kit.html` in **Firefox for Android** or **Google Chrome** instead of Jelly, and allow **Files and media** permission under **Android Settings > Apps > [Browser]** if prompted.
4. **If Chrome/Firefox show `ERR_FILE_NOT_FOUND` on `/storage/emulated/0/Download/...`:** Android Scoped Storage blocks shared-storage `file:///` paths in many newer browsers. Use one of these options:
   - **Option 1 — Browser's own folder (Chrome):** Copy the extracted `ipc-starter-kit/` folder into Chrome's own directory (`/storage/emulated/0/Android/data/com.android.chrome/files/Download/ipc-starter-kit/`) and open `file:///storage/emulated/0/Android/data/com.android.chrome/files/Download/ipc-starter-kit/ipc-kit.html` in Chrome.
   - **Option 2 — Localhost (100% offline, best storage reliability):** If Termux or an offline local static HTTP server app is installed, run a read-only local server inside the extracted folder (for example in Termux: `python3 -m http.server 8000`) and open `http://127.0.0.1:8000/START-HERE.html` in Firefox or Chrome.
5. **Run Settings > Check this device immediately:** Even if `ipc-kit.html` opens via a `content://` URI from a file manager, browsers often block or erase `localStorage` when closed (`Saving in this browser: does NOT work`). On WebView, `File download` and `Printing` will also report `does NOT work` as a reminder to use fallbacks or Firefox/Chrome.
6. **Paper fallback:** If **Check this device** reports saving failed or data disappears after closing the browser, **print from a desktop computer (or use Clean print view / Chrome / Firefox on Android)** and enter paper totals on a verified computer.

### C. iPhone and iPad (iOS / iPadOS)
1. Tap-previewing `ipc-kit.html` inside the iOS **Files** app opens a read-only preview that **does not** run the app properly or keep saved data.
2. **Safari on iOS/iPadOS** normally cannot open local `file://` HTML files with persistent storage.
3. **Recommendation:** Treat iPhone and iPad as **unsupported for direct offline browser use** unless your local pilot verifies a working method on your specific devices. **Use the printable paper forms in `field-kit/`** for ward observations and stock counts.

---

## 3. 10-Minute Field Test Protocol (Run Before Real Use)

Any IPC focal person or tester can verify a device in **10 minutes** using this step-by-step protocol:

1. **Turn on Airplane Mode / disconnect from Wi-Fi and mobile data** to confirm 100% offline operation.
2. **Open `ipc-kit.html`** from its permanent folder on the device.
3. **Run the built-in self-test:** Go to **Settings > Check this device**. Confirm that saving, downloading, and file reading pass, and copy the output line for the log below.
4. **Start the 5-minute practice run:** On **Home**, click **Try a 5-minute practice run**. Verify the top header shows the yellow badge `PRACTICE – fictional data`.
5. **Tally hand hygiene:** In **Hand hygiene > Tally**, select a month and area code, click **Start**, and record 3 opportunities (including one where you tick two moments at the same time, such as Moment 4 and Moment 1). Click **Finish session and add to totals** and check that the result shows `X of Y opportunities, Z%`.
6. **Record a stock issue:** In **Stock > Record**, record one **Issue** and check **Stock > Status** to confirm the earliest-expiring usable batch (`Use first`) was reduced and alerts update.
7. **Download a backup file:** In **Backup**, click **Download backup file** (or **Show backup text** if downloads are blocked) and confirm `ipc-kit-backup_YYYY-MM-DD_HHMM_v1.json` (with `PRACTICE` in the filename) is saved.
8. **Close and reopen the browser:** Completely quit the browser, reopen `ipc-kit.html` from the bookmark/folder, and confirm your practice session and stock entry are still there and the header shows `✔ Saved on this device HH:MM`.
9. **Test valid restore:** In **Backup > Restore from backup**, select the backup file you just downloaded. Confirm the check passes, data restores cleanly, and **Undo restore** is offered.
10. **Test invalid restore rejection:** Try restoring a non-backup file (for example, `README.md` or a broken text file). Confirm the app reports an error and **nothing in your current data is replaced**.
11. **Test printing:** Open **Reports > Print report** (and open `field-kit/hand-hygiene-observation-sheet.html`) and press `Ctrl+P` / `Cmd+P` to verify clean layout on A4 or US Letter.

### Copyable Device Test Log Table

Copy or print this table into your facility's IPC binder (`field-kit/ipc-lead-review-and-pilot-checklist.html`):

| Date (YYYY-MM-DD) | Device label (no personal names) | OS & Browser version | `Settings > Check this device` output | Reload kept data? (Y/N) | Valid backup restored? (Y/N) | Invalid file rejected safely? (Y/N) | Print OK? (Y/N) | Approved for real use? (Y/N) | Checked by role |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| | | | | | | | | | |
| | | | | | | | | | |
| | | | | | | | | | |

---

## 4. Known Limits & How to Avoid Data Loss

- **Clearing browser data deletes local records:** Running *"Clear browsing data / cookies and site data"* in the browser erases `localStorage`. Always download a backup file every week and before any browser maintenance.
- **Private / Incognito windows do not keep data:** Never use Private or Incognito mode for real data—everything entered is erased as soon as the window closes.
- **One browser per device:** Data saved in Firefox is not visible in Chrome or Edge on the same computer. Pick one browser, bookmark `ipc-kit.html`, and always use that browser.
- **Moving the file shows empty data:** Many browsers tie `file://` storage to the exact folder path. If you move `ipc-kit.html` to a new folder or a new computer and see an empty dataset, use **Backup > Restore from backup** to load your latest `.json` backup file.
- **Optional desktop helper for checking backups and combining CSV reports:** On computers with Python 3 installed, you can also verify backup files and combine multi-area/multi-month CSV exports from a terminal:
  - `python3 tools/ipc_tool.py check-backup FILE`
  - `python3 tools/ipc_tool.py combine-reports A.csv B.csv --by area|period|all`
