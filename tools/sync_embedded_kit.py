#!/usr/bin/env python3
"""
Synchronize standalone printable field-kit sheets, evidence register, and markdown
guides into:
  1. field-kit/ALL-PRINTABLE-SHEETS.html (single zero-script printable packet)
  2. <script id="ipc-embedded-kit"> inside ipc-kit.html (so every sheet & guide
     opens and prints inside ipc-kit.html even under Android content:// URIs)

Standard library only. Zero network access.
"""

from __future__ import annotations

import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IPC_KIT_PATH = os.path.join(ROOT, "ipc-kit.html")
ALL_SHEETS_PATH = os.path.join(ROOT, "field-kit", "ALL-PRINTABLE-SHEETS.html")

KIT_START_MARKER = "<!-- EMBEDDED-KIT-START -->"
KIT_END_MARKER = "<!-- EMBEDDED-KIT-END -->"

HTML_SOURCES = [
    ("field-kit/index.html", "index", "Field kit index (all 8 sheets)", False),
    ("field-kit/quick-start.html", "quick-start", "1. One-page quick start", True),
    ("field-kit/hand-hygiene-observation-sheet.html", "hand-hygiene-observation-sheet", "2. Hand hygiene observation sheet", True),
    ("field-kit/stock-card-and-count-sheet.html", "stock-card-and-count-sheet", "3. Stock card & count sheet", True),
    ("field-kit/readiness-checklist.html", "readiness-checklist", "4. IPC area readiness checklist", True),
    ("field-kit/review-routine-and-action-log.html", "review-routine-and-action-log", "5. Monthly review & action log", True),
    ("field-kit/practice-scenarios.html", "practice-scenarios", "6. Practice scenarios & answer key", True),
    ("field-kit/data-handling-plan.html", "data-handling-plan", "7. Facility data-handling plan", True),
    ("field-kit/ipc-lead-review-and-pilot-checklist.html", "ipc-lead-review-and-pilot-checklist", "8. IPC lead review & pilot checklist", True),
    ("evidence/evidence-register.html", "evidence-register", "Evidence register", False),
]

MD_SOURCES = [
    ("docs/DEVICE-TESTING.md", "device-testing", "Device testing & opening guide"),
    ("docs/TRANSLATING.md", "translating", "Translation guide"),
]

CSV_SOURCES = [
    "evidence/evidence-register.csv",
]

MD_SCOPED_CSS = """
@page { size: auto; margin: 12mm; }
.fk-sheet-md, .fk-sheet-md * { box-sizing: border-box; }
.fk-sheet-md {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  color: #111;
  background: #fff;
  padding: 10px;
  font-size: 13.5px;
  line-height: 1.45;
  max-width: 190mm;
  margin: 0 auto;
}
.fk-sheet-md h1 { font-size: 19px; margin: 0 0 8px 0; border-bottom: 2px solid #000; padding-bottom: 4px; }
.fk-sheet-md h2 { font-size: 15px; margin: 14px 0 6px 0; border-bottom: 1px solid #999; padding-bottom: 2px; }
.fk-sheet-md h3 { font-size: 13.5px; margin: 10px 0 4px 0; }
.fk-sheet-md p, .fk-sheet-md ul, .fk-sheet-md ol { margin: 6px 0; }
.fk-sheet-md ul, .fk-sheet-md ol { padding-left: 20px; }
.fk-sheet-md li { margin-bottom: 4px; }
.fk-sheet-md hr { border: 0; border-top: 1px solid #bbb; margin: 12px 0; }
.fk-sheet-md blockquote { margin: 8px 0; padding: 6px 10px; border-left: 3px solid #12324f; background: #f5f7fa; }
.fk-sheet-md code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px; background: #eef1f5; padding: 1px 4px; border-radius: 3px; }
.fk-sheet-md pre { background: #f4f6f8; border: 1px solid #ccc; padding: 8px 10px; overflow-x: auto; font-size: 12px; line-height: 1.35; }
.fk-sheet-md pre code { background: transparent; padding: 0; }
.fk-sheet-md table { width: 100%; border-collapse: collapse; margin: 8px 0; font-size: 12px; }
.fk-sheet-md th, .fk-sheet-md td { border: 1px solid #000; padding: 4px 6px; text-align: left; vertical-align: top; }
.fk-sheet-md th { background: #eee; }
@media print {
  .fk-sheet-md { padding: 0; font-size: 11px; max-width: 100%; }
}
""".strip()


def scope_single_selector(sel: str, scope_cls: str) -> str:
    s = sel.strip()
    if not s:
        return s
    if s == "*":
        return f".{scope_cls}, .{scope_cls} *"
    if s in ("body", "html", "html body"):
        return f".{scope_cls}"
    if s.startswith("body") and (len(s) == 4 or s[4] in " .:#[>~+"):
        return f".{scope_cls}" + s[4:]
    if s.startswith("html") and (len(s) == 4 or s[4] in " .:#[>~+"):
        return f".{scope_cls}" + s[4:]
    return f".{scope_cls} {s}"


def scope_css(css_text: str, scope_cls: str, keep_page: bool = True) -> str:
    clean = re.sub(r"/\*.*?\*/", "", css_text, flags=re.DOTALL)
    out = []
    i = 0
    n = len(clean)
    while i < n:
        while i < n and clean[i].isspace():
            i += 1
        if i >= n:
            break
        brace_idx = clean.find("{", i)
        if brace_idx == -1:
            break
        header = clean[i:brace_idx].strip()
        depth = 1
        j = brace_idx + 1
        while j < n and depth > 0:
            if clean[j] == "{":
                depth += 1
            elif clean[j] == "}":
                depth -= 1
            j += 1
        inner = clean[brace_idx + 1 : j - 1]
        if header.startswith("@page"):
            if keep_page:
                out.append(f"{header} {{ {inner.strip()} }}")
        elif header.startswith("@media") or header.startswith("@supports"):
            scoped_inner = scope_css(inner, scope_cls, keep_page=False)
            if scoped_inner.strip():
                indented = "\n  ".join(scoped_inner.splitlines())
                out.append(f"{header} {{\n  {indented}\n}}")
        else:
            sels = [scope_single_selector(s, scope_cls) for s in header.split(",") if s.strip()]
            out.append(f"{', '.join(sels)} {{ {inner.strip()} }}")
        i = j
    return "\n".join(out)


def extract_html_parts(file_path: str) -> tuple[str, str, str]:
    with open(file_path, encoding="utf-8") as fh:
        raw = fh.read()
    title_m = re.search(r"<title>(.*?)</title>", raw, re.DOTALL | re.IGNORECASE)
    style_m = re.search(r"<style>(.*?)</style>", raw, re.DOTALL | re.IGNORECASE)
    body_m = re.search(r"<body>(.*?)</body>", raw, re.DOTALL | re.IGNORECASE)
    if not (title_m and style_m and body_m):
        raise ValueError(f"Could not extract title/style/body from {file_path}")
    title = html.unescape(title_m.group(1).strip())
    css = style_m.group(1).strip()
    body = body_m.group(1).strip()
    return title, css, body


def render_inline_md(text: str) -> str:
    tokens: list[str] = []

    def _stash_code(m: re.Match[str]) -> str:
        idx = len(tokens)
        tokens.append(f"<code>{html.escape(m.group(1))}</code>")
        return f"\x00CODE{idx}\x00"

    stripped = re.sub(r"`([^`]+)`", _stash_code, text)
    escaped = html.escape(stripped, quote=True)
    escaped = re.sub(
        r"\[([^\]]+)\]\(([^)\s]+)\)",
        lambda m: (
            m.group(1)
            if re.match(r"^https?://", m.group(2), re.IGNORECASE)
            else f'<a href="{html.escape(m.group(2), quote=True)}">{m.group(1)}</a>'
        ),
        escaped,
    )
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", escaped)
    for idx, tok in enumerate(tokens):
        escaped = escaped.replace(f"\x00CODE{idx}\x00", tok)
    return escaped


def render_markdown(md_text: str) -> str:
    lines = md_text.splitlines()
    out: list[str] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        s = line.strip()
        if not s:
            i += 1
            continue
        if s.startswith("<!--") and s.endswith("-->"):
            i += 1
            continue
        if s.startswith("```"):
            i += 1
            code_lines = []
            while i < n and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            if i < n:
                i += 1
            out.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
            continue
        if re.match(r"^---+$", s):
            out.append("<hr>")
            i += 1
            continue
        m_h = re.match(r"^(#{1,3})\s+(.*)$", s)
        if m_h:
            lvl = len(m_h.group(1))
            out.append(f"<h{lvl}>{render_inline_md(m_h.group(2))}</h{lvl}>")
            i += 1
            continue
        if s.startswith(">"):
            quote_lines = []
            while i < n and lines[i].strip().startswith(">"):
                quote_lines.append(lines[i].strip().lstrip(">").strip())
                i += 1
            out.append("<blockquote><p>" + render_inline_md(" ".join(quote_lines)) + "</p></blockquote>")
            continue
        if s.startswith("|") and i + 1 < n and re.match(r"^\|[\s:|-]+\|?\s*$", lines[i + 1].strip()):
            headers = [c.strip() for c in s.strip("|").split("|")]
            i += 2
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                cols = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                while len(cols) < len(headers):
                    cols.append("")
                rows.append(cols[: len(headers)])
                i += 1
            th_html = "".join(f"<th>{render_inline_md(h)}</th>" for h in headers)
            body_html = "".join(
                "<tr>" + "".join(f"<td>{render_inline_md(c)}</td>" for c in r) + "</tr>"
                for r in rows
            )
            out.append(f"<table><thead><tr>{th_html}</tr></thead><tbody>{body_html}</tbody></table>")
            continue
        if re.match(r"^[-*]\s+", s) or re.match(r"^\d+\.\s+", s):
            is_ord = bool(re.match(r"^\d+\.\s+", s))
            tag = "ol" if is_ord else "ul"
            items: list[str] = []
            while i < n:
                cur = lines[i]
                cs = cur.strip()
                if not cs:
                    break
                if re.match(r"^\s{2,}[-*]\s+", cur):
                    sub = re.sub(r"^\s*[-*]\s+", "", cur)
                    if items:
                        items[-1] += "<br>• " + render_inline_md(sub)
                    i += 1
                elif (is_ord and re.match(r"^\d+\.\s+", cs)) or (not is_ord and re.match(r"^[-*]\s+", cs)):
                    item_txt = re.sub(r"^(\d+\.|[-*])\s+", "", cs)
                    items.append(render_inline_md(item_txt))
                    i += 1
                else:
                    break
            out.append(f"<{tag}>" + "".join(f"<li>{it}</li>" for it in items) + f"</{tag}>")
            continue
        para_lines = [s]
        i += 1
        while i < n:
            ns = lines[i].strip()
            if (
                not ns
                or ns.startswith("#")
                or ns.startswith(">")
                or ns.startswith("```")
                or ns.startswith("|")
                or re.match(r"^---+$", ns)
                or re.match(r"^[-*]\s+", ns)
                or re.match(r"^\d+\.\s+", ns)
            ):
                break
            para_lines.append(ns)
            i += 1
        out.append("<p>" + render_inline_md(" ".join(para_lines)) + "</p>")
    return "\n".join(out)


def build_all_printable_sheets(docs: dict[str, dict]) -> str:
    sheet_ids = [rel for rel, _, _, in_all in HTML_SOURCES if in_all]
    css_parts = [
        "@page { size: auto; margin: 12mm; }",
        "* { box-sizing: border-box; }",
        """body.all-sheets-body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  color: #000;
  background: #fff;
  margin: 0;
  padding: 12px;
  font-size: 13px;
  line-height: 1.4;
}
.toc-page { max-width: 190mm; margin: 0 auto 14px auto; }
.toc-page h1 { font-size: 20px; margin: 0 0 6px 0; border-bottom: 2px solid #000; padding-bottom: 4px; }
.toc-page .note { border: 1.5px solid #000; padding: 6px 8px; background: #f4f4f4; margin: 8px 0; font-size: 12.5px; }
.toc-page ul { padding-left: 20px; margin: 8px 0; }
.toc-page li { margin: 5px 0; }
.toc-page a { color: #000; font-weight: bold; }
.sheet-pack-item { border-top: 2px dashed #999; padding-top: 10px; margin-top: 14px; }
.sheet-pack-bar { max-width: 190mm; margin: 0 auto 6px auto; font-size: 11.5px; }
.sheet-pack-bar a { color: #000; }
@media print {
  body.all-sheets-body { padding: 0; }
  .sheet-pack-item { border-top: 0; padding-top: 0; margin-top: 0; page-break-before: always; break-before: page; }
  .sheet-pack-bar, .fk-all-no-print { display: none !important; }
}""",
    ]
    toc_links = []
    sections = []
    for rel in sheet_ids:
        entry = docs[rel]
        slug = entry["slug"]
        css_parts.append(entry["scopedCssNoPage"])
        # Replace relative cross-file nav-bar inside each bundled sheet with safe same-page anchor
        cleaned_body = re.sub(
            r'<div class="nav-bar">.*?</div>',
            '<div class="nav-bar"><a href="#top-toc">↑ Back to sheet list</a></div>',
            entry["bodyHtml"],
            count=1,
            flags=re.DOTALL,
        )
        toc_links.append(f'<li><a href="#sheet-{slug}">{html.escape(entry["label"])}</a></li>')
        sections.append(
            f'<section id="sheet-{slug}" class="sheet-pack-item">\n'
            f'  <div class="{entry["scopeClass"]}">\n{cleaned_body}\n  </div>\n'
            f"</section>"
        )

    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '  <meta charset="utf-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '  <meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; img-src data:">\n'
        "  <title>All 8 Printable Field Kit Sheets – IPC Starter Kit v1.0.0</title>\n"
        "  <style>\n"
        + "\n".join(css_parts)
        + "\n  </style>\n"
        "</head>\n"
        '<body class="all-sheets-body">\n'
        '  <div class="toc-page" id="top-toc">\n'
        '    <div class="sheet-pack-bar"><a href="index.html">← Field Kit Index</a> · <a href="../ipc-kit.html">Open App (ipc-kit.html)</a></div>\n'
        "    <h1>IPC Starter Kit – All 8 Printable Sheets Combined</h1>\n"
        "    <p>This single file contains all 8 black-and-white printable sheets for A4 and US Letter paper (<code>Ctrl+P</code> / <code>Cmd+P</code> or browser Share → Print / Save PDF). Links below jump within this same file so navigation works even when Android opens it via a <code>content://</code> URI.</p>\n"
        '    <div class="note"><strong>Privacy rule across all sheets:</strong> Do not write patient or staff names, ID numbers, clinical details, photos, or free-text observation notes. Always assign actions to a <strong>ROLE</strong> (e.g. <em>Ward in-charge</em>), never a person\'s name.</div>\n'
        "    <ul>\n      "
        + "\n      ".join(toc_links)
        + "\n    </ul>\n"
        "  </div>\n"
        + "\n".join(sections)
        + "\n</body>\n</html>\n"
    )


def main() -> int:
    docs: dict[str, dict] = {}
    order: list[str] = []

    for rel, slug, label, in_all in HTML_SOURCES:
        abs_path = os.path.join(ROOT, rel)
        title, css, body_html = extract_html_parts(abs_path)
        scope_cls = f"fk-sheet-{slug}"
        scoped_css = scope_css(css, scope_cls, keep_page=True)
        scoped_css_no_page = scope_css(css, scope_cls, keep_page=False)
        docs[rel] = {
            "id": rel,
            "slug": slug,
            "label": label,
            "title": title,
            "kind": "html",
            "inAllSheets": in_all,
            "scopeClass": scope_cls,
            "scopedCss": scoped_css,
            "scopedCssNoPage": scoped_css_no_page,
            "bodyHtml": body_html,
        }
        order.append(rel)

    for rel, slug, label in MD_SOURCES:
        abs_path = os.path.join(ROOT, rel)
        with open(abs_path, encoding="utf-8") as fh:
            md_text = fh.read()
        docs[rel] = {
            "id": rel,
            "slug": slug,
            "label": label,
            "title": f"{label} – IPC Starter Kit v1.0.0",
            "kind": "md",
            "inAllSheets": False,
            "scopeClass": "fk-sheet-md",
            "scopedCss": MD_SCOPED_CSS,
            "scopedCssNoPage": MD_SCOPED_CSS,
            "bodyHtml": '<div class="page">' + render_markdown(md_text) + "</div>",
        }
        order.append(rel)

    csvs: dict[str, str] = {}
    for rel in CSV_SOURCES:
        abs_path = os.path.join(ROOT, rel)
        with open(abs_path, encoding="utf-8") as fh:
            csvs[rel] = fh.read()

    # 1. Write field-kit/ALL-PRINTABLE-SHEETS.html
    all_sheets_html = build_all_printable_sheets(docs)
    with open(ALL_SHEETS_PATH, "w", encoding="utf-8") as fh:
        fh.write(all_sheets_html)

    # Trim scopedCssNoPage from ipc-kit.html payload so we don't store duplicate CSS twice
    app_docs = {}
    for k, v in docs.items():
        app_docs[k] = {
            "id": v["id"],
            "slug": v["slug"],
            "label": v["label"],
            "title": v["title"],
            "kind": v["kind"],
            "inAllSheets": v["inAllSheets"],
            "scopeClass": v["scopeClass"],
            "scopedCss": v["scopedCss"],
            "bodyHtml": v["bodyHtml"],
        }

    payload = {
        "order": order,
        "docs": app_docs,
        "csvs": csvs,
    }
    json_payload = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    script_block = (
        f"{KIT_START_MARKER}\n"
        '<script id="ipc-embedded-kit">\n'
        f"window.IPC_EMBEDDED_KIT = {json_payload};\n"
        "</script>\n"
        f"{KIT_END_MARKER}"
    )

    with open(IPC_KIT_PATH, encoding="utf-8") as fh:
        kit_html = fh.read()
    if KIT_START_MARKER not in kit_html or KIT_END_MARKER not in kit_html:
        raise RuntimeError("Embedded kit markers not found in ipc-kit.html")
    pattern = re.compile(
        re.escape(KIT_START_MARKER) + r".*?" + re.escape(KIT_END_MARKER),
        re.DOTALL,
    )
    updated_kit, count = pattern.subn(lambda _m: script_block, kit_html, count=1)
    if count != 1:
        raise RuntimeError("Expected single replacement in ipc-kit.html")
    with open(IPC_KIT_PATH, "w", encoding="utf-8") as fh:
        fh.write(updated_kit)

    print(
        f"Synced {len(HTML_SOURCES)} HTML docs, {len(MD_SOURCES)} Markdown guides, "
        f"and {len(CSV_SOURCES)} CSV files into ipc-kit.html and ALL-PRINTABLE-SHEETS.html."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
