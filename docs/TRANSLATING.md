# Translation Guide (`docs/TRANSLATING.md`)

The IPC Starter Kit (`ipc-kit.html` and the printable sheets in `field-kit/`) is written in plain, short, idiom-free English (target reading age ~12) so that local teams can translate it accurately into other languages.

> **Important clinical review notice:** The kit includes all **6 official UN languages** (`en`, `ar`, `zh`, `fr`, `ru`, `es`). All non-English built-in translations (**Arabic / العربية**, **Chinese / 中文**, **French / Français**, **Russian / Русский**, and **Spanish / Español**) are draft reference translations and **need review by a fluent local clinical reviewer** before use in patient care areas. The same rule applies to any new language added locally.

---

## 1. How Strings Are Organised in `ipc-kit.html`

Inside `ipc-kit.html` (in `<script id="ipc-strings">`), all user-interface text is stored in a single JavaScript object named `window.IPC_STRINGS`, keyed by language code:

- `window.IPC_STRINGS.en` is the **master English dictionary** (`ltr`). Every screen label, button, alert, practice scenario, and report heading has a stable key in `en`.
- Five built-in UN translation blocks match every key and placeholder in `en`:
  - `fr`: **Français** (`_dir: 'ltr'`)
  - `ar`: **العربية** (`_dir: 'rtl'` — automatically switches `<html dir="rtl">` and mirrors navigation, cards, tables, and moment rows while keeping JSON/CSV text boxes and English paper sheets LTR)
  - `es`: **Español** (`_dir: 'ltr'`)
  - `ru`: **Русский** (`_dir: 'ltr'`)
  - `zh`: **中文** (`_dir: 'ltr'`)
- Each language block starts with `_name` (the display name shown in **Settings > Language**) and `_dir` (`'ltr'` or `'rtl'`).
- **Automatic fallback to English:** When the app looks up a translation key in the active language, any key that is missing or empty automatically falls back to `window.IPC_STRINGS.en`. This guarantees the app will never show blank buttons or crash if a translation is only partly finished.

---

## 2. How to Add or Edit a Language in `ipc-kit.html`

1. Open `ipc-kit.html` in any plain-text editor (Notepad, TextEdit, VS Code, or gedit — save using **UTF-8** encoding).
2. Find `window.IPC_STRINGS` (`<script id="ipc-strings">`) and locate the built-in language block you want to edit (`fr`, `ar`, `es`, `ru`, or `zh`).
3. **To refine a built-in language:** Edit the translated strings inside its block directly and save the file. Remember that `set_erase_word` (`'ERASE'`) is kept as ASCII `ERASE` across languages so confirmation prompts work identically on any keyboard/IME unless your team explicitly updates both `set_erase_confirm` and `set_erase_word`.
4. **To add another language (for example, Swahili `sw` or Portuguese `pt`):**
   - Copy an entire language block (such as `fr: { ... },` or `ar: { ... },`) and paste it before the closing `};` of `window.IPC_STRINGS` with your ISO language code (e.g., `sw` or `pt` — must match `/^[a-z]{2,3}(-[A-Za-z0-9]{2,8})?$/` so backups validate cleanly).
   - Update `_name: '...'` (e.g., `'Kiswahili'` or `'Português'`) and `_dir: 'ltr'` (or `'rtl'` for right-to-left languages such as Urdu or Pashto). **Settings > Language** automatically lists every key present in `window.IPC_STRINGS`.
5. **Keep `{placeholders}` intact:**
   - Many dynamic strings contain curly-brace placeholders such as `{a}` (actions), `{o}` (opportunities), `{p}` (percentage), `{n}` (number/count), `{q}` (quantity), `{u}` (unit), `{month}`, `{area}`, `{time}`, `{when}`, `{days}`, `{batch}`, `{date}`, `{plan}`, `{f}` (filename), `{t}` (threshold), `{d}` (date), or `{v}` (version).
   - **Do not translate, remove, or reorder letters inside `{...}`.** Move the `{placeholder}` token to wherever it fits naturally in your language's grammar.
   - Example (`opp_result`):
     - English: `"{a} of {o} opportunities, {p}"`
     - Arabic: `"{a} من {o} فرص، {p}"`
     - French: `"{a} sur {o} opportunités, {p}"`
6. **Keep exact meaning for clinical and logistics terms:**
   - **Five moments `[HH-01]`:** Make sure the 5 moment labels clearly distinguish *1 Before touching a patient*, *2 Before a clean/aseptic procedure*, *3 After body fluid exposure risk*, *4 After touching a patient*, and *5 After touching patient surroundings*.
   - **Opportunity vs. Indication `[HH-02]`:** Keep the distinction clear that multiple moments (indications) happening at the same time count as **one opportunity**.
   - **Stock terms `[ST-01..ST-10]`:** Keep clear distinctions between *Usable stock*, *Stockout (0 usable)*, *Reorder point*, *Use first (earliest expiry)*, *Physical count*, and *Adjustment* reason codes.

---

## 3. How to Translate the Printable Field Kit (`field-kit/*.html`)

Each printable sheet in `field-kit/` is a standalone, self-contained HTML file with inline CSS and no external dependencies:

1. **Copy the file with a language suffix** before translating so the English original remains available as a reference:
   - `field-kit/quick-start.html` → `field-kit/quick-start.fr.html`
   - `field-kit/hand-hygiene-observation-sheet.html` → `field-kit/hand-hygiene-observation-sheet.fr.html`
   - `field-kit/stock-card-and-count-sheet.html` → `field-kit/stock-card-and-count-sheet.fr.html`
   - `field-kit/readiness-checklist.html` → `field-kit/readiness-checklist.fr.html`
   - `field-kit/review-routine-and-action-log.html` → `field-kit/review-routine-and-action-log.fr.html`
   - `field-kit/practice-scenarios.html` → `field-kit/practice-scenarios.fr.html`
   - `field-kit/data-handling-plan.html` → `field-kit/data-handling-plan.fr.html`
   - `field-kit/ipc-lead-review-and-pilot-checklist.html` → `field-kit/ipc-lead-review-and-pilot-checklist.fr.html`
2. Update `<html lang="en">` at the top of the copied file to your language code (for example, `<html lang="fr">`).
3. **Preserve all hard rules on every translated sheet:**
   - Keep the `<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:">` header tag and do not add external fonts, scripts, or images.
   - Keep the privacy notice on every sheet: *"Do not write names, ID numbers or clinical details on this sheet."*
   - Keep the evidence IDs in brackets (such as `[HH-02]`, `[ST-07]`, `[RC-01]`) and the CC BY-NC-SA 4.0 footer with @mostafase credit and the link to `evidence/evidence-register.html`.
   - Test print (`Ctrl+P` / `Cmd+P`) on A4 and US Letter to make sure translated text still fits on **one page** for the one-page forms (`quick-start`, `hand-hygiene-observation-sheet`, and `readiness-checklist`).

---

## 4. Mandatory Clinical & Field Review Checklist

Before using a translated version in your facility (`Part A` of `field-kit/ipc-lead-review-and-pilot-checklist.html`):

1. **Fluent clinical reviewer check:** Have a fluent local nurse, doctor, pharmacist, or IPC focal person read every screen and paper sheet against national IPC terminology.
2. **Role names check:** Confirm that the translated responsible roles (*IPC focal person*, *Ward in-charge*, *Storekeeper*, *Facility manager*, *Maintenance lead*, *Cleaning supervisor*) match job titles used in your facility, while still referring to **roles and never personal names**.
3. **Practice run test:** Have 2–3 staff members complete the 6 practice scenarios and a paper observation sheet in the translated language to confirm there is no ambiguity.
