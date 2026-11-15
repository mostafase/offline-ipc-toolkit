#!/usr/bin/env python3
"""IPC Starter Kit desktop helper (Python 3.8+, standard library only).

Two read-only jobs that are easier on a desktop than in a phone browser:

  check-backup FILE...
      Check backup files made by ipc-kit.html BEFORE you rely on them:
      format, version, checksum, and a strict field check (a file that
      contains any unexpected field, such as a name or a note, is refused).
      Exit code 0 = every file is valid, 1 = at least one is not.

  combine-reports CSV... [--by area|period|all] [--threshold N] [-o OUT]
      Combine hand hygiene report CSVs (from several areas, months or
      facilities) by ADDING COUNTS FIRST, then recalculating
      adherence = 100 x actions / opportunities.

This tool never changes or uploads anything and makes no network requests.
It only reads the files you name and, with -o, writes one new CSV.

License: PolyForm Noncommercial 1.0.0 (see LICENSE).
Required Notice: Copyright (c) 2026 mostafase (https://github.com/mostafase)
"""

import argparse
import csv
import io
import json
import re
import sys
import zlib
from datetime import date

TOOL_VERSION = "1.0.0"
BACKUP_FORMAT = "ipc-starter-kit-backup"
SCHEMA_VERSION = 1
MAX_BACKUP_BYTES = 5 * 1024 * 1024
MAX_COUNT = 100000
MAX_QTY = 1000000

AREA_CODE_RE = re.compile(r"^[A-Z0-9][A-Z0-9-]{0,11}$")
BATCH_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9\-/.]{0,19}$")
LANG_RE = re.compile(r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})?$")
PERIOD_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
ID_RE = re.compile(r"^[a-z]\d{1,9}$")
BAD_TEXT_RE = re.compile(r"[\x00-\x1f\x7f<>]")
ADJUST_REASONS = {"expired": -1, "damaged": -1, "lost": -1, "transfer_out": -1,
                  "found": 1, "transfer_in": 1, "correction": 0}

HH_CSV_HEADER = ["period", "area", "sessions", "opportunities", "hand_rub", "handwash", "missed",
                 "actions", "adherence_percent", "small_sample", "moment_data_opportunities",
                 "m1_indications", "m1_actions", "m2_indications", "m2_actions",
                 "m3_indications", "m3_actions", "m4_indications", "m4_actions",
                 "m5_indications", "m5_actions"]


# --------------------------------------------------------------------------- helpers

def is_int(v):
    # JSON true/false are bool in Python, which is a subclass of int; exclude them.
    return isinstance(v, int) and not isinstance(v, bool)


def is_count(v, top=MAX_COUNT):
    return is_int(v) and 0 <= v <= top


def valid_date(s):
    if not isinstance(s, str) or not re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return False
    try:
        date.fromisoformat(s)
        return True
    except ValueError:
        return False


def checksum(data):
    """CRC32 of the compact JSON text, identical to the app's crc32(JSON.stringify(data))."""
    text = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    return format(zlib.crc32(text.encode("utf-8")) & 0xFFFFFFFF, "08x")


def _reject_constant(name):
    raise ValueError("invalid number " + name)


def keys_exactly(obj, allowed, path, errs):
    if not isinstance(obj, dict):
        errs.append(path + ": not an object")
        return False
    for k in obj:
        if k not in allowed:
            errs.append('%s: unexpected field "%s"' % (path, str(k)[:30]))
    for k in allowed:
        if k not in obj:
            errs.append('%s: missing field "%s"' % (path, k))
    return True


# --------------------------------------------------------------------------- validation

def check_hh_entry(e, area_codes, allow_zero=False):
    """Mirror of validateHHEntry() in ipc-kit.html. Returns a list of problem codes."""
    errs = []
    if not isinstance(e.get("period"), str) or not PERIOD_RE.match(e["period"]):
        errs.append("hh_period")
    if e.get("area") not in area_codes:
        errs.append("hh_area")
    for k in ("rub", "wash", "missed"):
        if not is_count(e.get(k)):
            errs.append("hh_count (%s)" % k)
    if errs:
        return errs
    opp = e["rub"] + e["wash"] + e["missed"]
    actions = e["rub"] + e["wash"]
    if opp == 0 and not allow_zero:
        errs.append("hh_zero")
    ind, act = e.get("ind"), e.get("act")
    if ind is None and act is None:
        return errs
    if not (isinstance(ind, list) and isinstance(act, list) and len(ind) == 5 and len(act) == 5):
        return errs + ["hh_moments"]
    if not all(is_count(x) for x in ind + act):
        return errs + ["hh_moments"]
    for i in range(5):
        if ind[i] > opp:
            errs.append("hh_ind_gt_opp (moment %d)" % (i + 1))
        if act[i] > ind[i]:
            errs.append("hh_act_gt_ind (moment %d)" % (i + 1))
        if act[i] > actions:
            errs.append("hh_act_gt_actions (moment %d)" % (i + 1))
        if ind[i] - act[i] > e["missed"]:
            errs.append("hh_missed_mismatch (moment %d)" % (i + 1))
    if not errs and sum(ind) < opp:
        errs.append("hh_ind_lt_opp")  # every opportunity has at least one moment
    return errs


def check_item(it, seen_names):
    errs = []
    name, unit = it.get("name"), it.get("unit")
    if not isinstance(name, str) or not name.strip() or len(name) > 50 or BAD_TEXT_RE.search(name):
        errs.append("item_name")
    elif name.strip().lower() in seen_names:
        errs.append("item_dup")
    if not isinstance(unit, str) or not unit.strip() or len(unit) > 30 or BAD_TEXT_RE.search(unit):
        errs.append("item_unit")
    if not is_count(it.get("reorderPoint"), MAX_QTY):
        errs.append("item_reorder")
    if not isinstance(it.get("tracksExpiry"), bool):
        errs.append("item_track")
    ad = it.get("alertDays")
    if ad is not None and not (is_int(ad) and 1 <= ad <= 730):
        errs.append("item_alert")
    if not isinstance(it.get("active"), bool):
        errs.append("item_active")
    return errs


def check_txn(t, items, area_codes):
    errs = []
    item = items.get(t.get("itemId"))
    if item is None:
        return ["txn_item"]
    if t.get("type") not in ("receipt", "issue", "count", "adjust"):
        errs.append("txn_type")
    if not valid_date(t.get("date")):
        errs.append("txn_date")
    qty = t.get("qty")
    if not is_int(qty) or abs(qty) > MAX_QTY:
        errs.append("txn_qty")
    for k in ("batch", "expiry", "reason", "area"):
        if not isinstance(t.get(k), str):
            return errs + ["txn_text (%s)" % k]
    if item["tracksExpiry"]:
        if not valid_date(t["expiry"]):
            errs.append("txn_expiry")
        if t["batch"] != "" and not BATCH_RE.match(t["batch"]):
            errs.append("txn_batch")
    elif t["batch"] != "" or t["expiry"] != "":
        errs.append("txn_no_batch")
    if t["area"] != "" and t["area"] not in area_codes:
        errs.append("txn_area")
    if errs:
        return errs
    if t["type"] == "adjust":
        if t["reason"] not in ADJUST_REASONS:
            errs.append("txn_reason")
        else:
            sign = ADJUST_REASONS[t["reason"]]
            if qty == 0 or (sign < 0 < qty) or (qty < 0 < sign):
                errs.append("txn_adjust_sign")
    else:
        if t["reason"] != "":
            errs.append("txn_reason")
        if (qty < 0) if t["type"] == "count" else (qty <= 0):
            errs.append("txn_qty")
    if t["type"] in ("receipt", "issue") and t["expiry"] and t["expiry"] < t["date"]:
        errs.append("txn_receive_expired" if t["type"] == "receipt" else "txn_issue_expired")
    if t["type"] != "issue" and t["area"] != "":
        errs.append("txn_area")
    return errs


def negative_items(txns):
    """Replay transactions per item in date order (stable). Return item ids whose batch ever went below zero."""
    order = sorted(range(len(txns)), key=lambda i: (txns[i]["itemId"], txns[i]["date"], i))
    bal, bad = {}, set()
    for i in order:
        t = txns[i]
        key = (t["itemId"], t["batch"], t["expiry"])
        q = bal.get(key, 0)
        if t["type"] == "receipt":
            q += t["qty"]
        elif t["type"] == "issue":
            q -= t["qty"]
        elif t["type"] == "adjust":
            q += t["qty"]
        elif t["type"] == "count":
            q = t["qty"]
        bal[key] = q
        if q < 0:
            bad.add(t["itemId"])
    return bad


def validate_data(d):
    """Strict check of the dataset. Mirrors validateData() in ipc-kit.html."""
    errs = []
    if not keys_exactly(d, ["schema", "settings", "hh", "stock", "meta"], "data", errs):
        return errs
    if d["schema"] != SCHEMA_VERSION:
        errs.append("data.schema: unsupported version")
    s = d["settings"]
    if keys_exactly(s, ["facilityLabel", "areaCodes", "smallSampleThreshold", "expiryWindowDays", "language"], "settings", errs):
        fl = s.get("facilityLabel")
        if not isinstance(fl, str) or len(fl) > 40 or BAD_TEXT_RE.search(fl):
            errs.append("settings.facilityLabel: invalid")
        codes = s.get("areaCodes")
        if not isinstance(codes, list) or len(codes) > 40:
            errs.append("settings.areaCodes: invalid")
        else:
            for i, c in enumerate(codes):
                if not isinstance(c, str) or not AREA_CODE_RE.match(c):
                    errs.append("settings.areaCodes[%d]: invalid code" % i)
                elif codes.index(c) != i:
                    errs.append("settings.areaCodes[%d]: duplicate" % i)
        if not (is_int(s.get("smallSampleThreshold")) and 0 <= s["smallSampleThreshold"] <= 10000):
            errs.append("settings.smallSampleThreshold: invalid")
        if not (is_int(s.get("expiryWindowDays")) and 1 <= s["expiryWindowDays"] <= 730):
            errs.append("settings.expiryWindowDays: invalid")
        if not isinstance(s.get("language"), str) or not LANG_RE.match(s["language"]):
            errs.append("settings.language: invalid")
    meta = d["meta"]
    if keys_exactly(meta, ["lastBackupAt", "nextId"], "meta", errs):
        if meta.get("lastBackupAt") is not None and not isinstance(meta.get("lastBackupAt"), str):
            errs.append("meta.lastBackupAt: invalid")
        if not (is_int(meta.get("nextId")) and meta["nextId"] >= 1):
            errs.append("meta.nextId: invalid")
    if errs:
        return errs

    ids = set()

    def check_id(obj_id, path):
        if not isinstance(obj_id, str) or not ID_RE.match(obj_id):
            errs.append(path + ".id: invalid")
            return
        if obj_id in ids:
            errs.append(path + ".id: duplicate")
        ids.add(obj_id)
        if int(obj_id[1:]) >= meta["nextId"]:
            errs.append(path + ".id: not below meta.nextId")

    hh = d["hh"]
    if keys_exactly(hh, ["entries", "draft"], "hh", errs):
        if not isinstance(hh["entries"], list):
            errs.append("hh.entries: not a list")
        else:
            for i, e in enumerate(hh["entries"]):
                p = "hh.entries[%d]" % i
                if not keys_exactly(e, ["id", "period", "area", "source", "rub", "wash", "missed", "ind", "act"], p, errs):
                    continue
                check_id(e["id"], p)
                if e["source"] not in ("tally", "paper"):
                    errs.append(p + ".source: invalid")
                errs.extend(p + ": " + c for c in check_hh_entry(e, s["areaCodes"]))
        dr = hh["draft"]
        if dr is not None and keys_exactly(dr, ["period", "area", "rub", "wash", "missed", "ind", "act", "last"], "hh.draft", errs):
            errs.extend("hh.draft: " + c for c in check_hh_entry(dr, s["areaCodes"], allow_zero=True))
            last = dr["last"]
            if last is not None and keys_exactly(last, ["moments", "outcome"], "hh.draft.last", errs):
                if not isinstance(last["moments"], list) or not last["moments"] or \
                        any((not is_int(m)) or m not in (1, 2, 3, 4, 5) for m in last["moments"]):
                    errs.append("hh.draft.last.moments: invalid")
                if last["outcome"] not in ("rub", "wash", "missed"):
                    errs.append("hh.draft.last.outcome: invalid")

    st = d["stock"]
    if keys_exactly(st, ["items", "txns"], "stock", errs):
        if not isinstance(st["items"], list) or not isinstance(st["txns"], list):
            errs.append("stock: items/txns must be lists")
            return errs[:50]
        items, names = {}, set()
        for i, it in enumerate(st["items"]):
            p = "stock.items[%d]" % i
            if not keys_exactly(it, ["id", "name", "unit", "reorderPoint", "tracksExpiry", "alertDays", "active"], p, errs):
                continue
            check_id(it["id"], p)
            errs.extend(p + ": " + c for c in check_item(it, names))
            if isinstance(it.get("name"), str):
                names.add(it["name"].strip().lower())
            items[it["id"]] = it
        good_txns = []
        for i, t in enumerate(st["txns"]):
            p = "stock.txns[%d]" % i
            if not keys_exactly(t, ["id", "itemId", "date", "type", "qty", "batch", "expiry", "reason", "area"], p, errs):
                continue
            check_id(t["id"], p)
            problems = check_txn(t, items, s["areaCodes"])
            errs.extend(p + ": " + c for c in problems)
            if not problems:
                good_txns.append(t)
        for item_id in sorted(negative_items(good_txns)):
            errs.append("stock: item %s balance goes below zero (txn_insufficient)" % item_id)
    return errs[:50]


def parse_backup(raw_bytes):
    """Return (ok, errors, backup). Never modifies anything."""
    if len(raw_bytes) == 0:
        return False, ["empty"], None
    if len(raw_bytes) > MAX_BACKUP_BYTES:
        return False, ["too_large"], None
    try:
        text = raw_bytes.decode("utf-8-sig")
        b = json.loads(text, parse_constant=_reject_constant)
    except (UnicodeDecodeError, ValueError):
        return False, ["not_json"], None
    if not isinstance(b, dict) or b.get("format") != BACKUP_FORMAT:
        return False, ["not_backup"], None
    fv = b.get("formatVersion")
    if not is_int(fv) or fv < 1:
        return False, ["not_backup"], None
    if fv > SCHEMA_VERSION:
        return False, ["newer_version (made by a newer app; update this tool)"], None
    errs = []
    allowed = ["format", "formatVersion", "appVersion", "createdAt", "mode", "checksum", "data"]
    for k in b:
        if k not in allowed:
            errs.append('unexpected field "%s"' % str(k)[:30])
    if b.get("mode") not in ("real", "practice"):
        errs.append("bad_mode")
    if not isinstance(b.get("createdAt"), str):
        errs.append("bad_date")
    if not isinstance(b.get("data"), dict):
        return False, errs + ["no_data"], None
    if b.get("checksum") != checksum(b["data"]):
        errs.append("checksum (file was changed or damaged after it was made)")
    if errs:
        return False, errs, None
    data_errs = validate_data(b["data"])
    if data_errs:
        return False, data_errs, None
    return True, [], b


def cmd_check_backup(args):
    all_ok = True
    for name in args.files:
        try:
            with open(name, "rb") as fh:
                raw = fh.read(MAX_BACKUP_BYTES + 1)
        except OSError as exc:
            print("INVALID  %s\n  - cannot read file: %s" % (name, exc.strerror))
            all_ok = False
            continue
        ok, errs, b = parse_backup(raw)
        if ok:
            d = b["data"]
            opp = sum(e["rub"] + e["wash"] + e["missed"] for e in d["hh"]["entries"])
            print("VALID    %s" % name)
            print("  made: %s  mode: %s  app version: %s" % (b["createdAt"], b["mode"], b.get("appVersion", "")))
            print("  hand hygiene: %d sessions, %d opportunities, %d area codes"
                  % (len(d["hh"]["entries"]), opp, len(d["settings"]["areaCodes"])))
            print("  stock: %d items, %d transactions" % (len(d["stock"]["items"]), len(d["stock"]["txns"])))
            if b["mode"] == "practice":
                print("  note: this is a PRACTICE (fictional) backup.")
        else:
            all_ok = False
            print("INVALID  %s" % name)
            for e in errs[:20]:
                print("  - " + e)
            if len(errs) > 20:
                print("  - ... and %d more" % (len(errs) - 20))
    return 0 if all_ok else 1


# --------------------------------------------------------------------------- combine reports

def fmt_pct(num, den):
    """Same display rule as the app: whole number, never a misleading 0% or 100%."""
    if den <= 0:
        return "No observations"
    p = int((100 * num / den) + 0.5)
    if p == 100 and num < den:
        return ">99%"
    if p == 0 and num > 0:
        return "<1%"
    return "%d%%" % p


def read_hh_csv(name):
    with open(name, newline="", encoding="utf-8-sig") as fh:
        reader = csv.reader(fh)
        header = next(reader, None)
        if header != HH_CSV_HEADER:
            raise ValueError("%s: not a hand hygiene report CSV from this kit (header does not match)" % name)
        rows = []
        for n, r in enumerate(reader, start=2):
            if not r or (r[0] == "ALL" and r[1] == "ALL"):
                continue  # skip blank lines and the file's own total row
            if len(r) != len(HH_CSV_HEADER):
                raise ValueError("%s line %d: wrong number of columns" % (name, n))
            rec = dict(zip(HH_CSV_HEADER, r))
            try:
                for k in ("sessions", "opportunities", "hand_rub", "handwash", "missed", "actions", "moment_data_opportunities"):
                    rec[k] = int(rec[k])
                    if rec[k] < 0:
                        raise ValueError
                for i in range(1, 6):
                    for k in ("m%d_indications" % i, "m%d_actions" % i):
                        rec[k] = int(rec[k]) if rec[k] != "" else None
            except ValueError:
                raise ValueError("%s line %d: counts must be whole numbers" % (name, n))
            if rec["hand_rub"] + rec["handwash"] + rec["missed"] != rec["opportunities"] or \
                    rec["hand_rub"] + rec["handwash"] != rec["actions"]:
                raise ValueError("%s line %d: counts do not add up" % (name, n))
            rows.append(rec)
        return rows


def combine(rows, by, threshold):
    groups = {}
    for r in rows:
        if by == "area":
            key = ("ALL", r["area"])
        elif by == "period":
            key = (r["period"], "ALL")
        else:
            key = ("ALL", "ALL")
        g = groups.setdefault(key, {"sessions": 0, "opp": 0, "rub": 0, "wash": 0, "missed": 0, "mopp": 0,
                                    "ind": [0] * 5, "act": [0] * 5})
        g["sessions"] += r["sessions"]
        g["rub"] += r["hand_rub"]
        g["wash"] += r["handwash"]
        g["missed"] += r["missed"]
        if r["moment_data_opportunities"] > 0:
            g["mopp"] += r["moment_data_opportunities"]
            for i in range(5):
                g["ind"][i] += r["m%d_indications" % (i + 1)] or 0
                g["act"][i] += r["m%d_actions" % (i + 1)] or 0
    out = [HH_CSV_HEADER]
    for key in sorted(groups):
        g = groups[key]
        opp = g["rub"] + g["wash"] + g["missed"]
        actions = g["rub"] + g["wash"]
        # Half-up rounding to one decimal, matching Math.round() in the app (Python's round() is banker's rounding).
        pct = "" if opp == 0 else "%.1f" % (int(1000.0 * actions / opp + 0.5) / 10)
        row = [key[0], key[1], g["sessions"], opp, g["rub"], g["wash"], g["missed"], actions, pct,
               "yes" if 0 < opp < threshold else "no", g["mopp"]]
        for i in range(5):
            row += [g["ind"][i], g["act"][i]] if g["mopp"] else ["", ""]
        out.append(row)
    return out


def cmd_combine(args):
    rows = []
    try:
        for name in args.files:
            rows.extend(read_hh_csv(name))
    except (OSError, ValueError) as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 1
    table = combine(rows, args.by, args.threshold)
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\r\n")
    writer.writerows(table)
    if args.output:
        with open(args.output, "w", newline="", encoding="utf-8") as fh:
            fh.write(buf.getvalue())
        print("wrote %s" % args.output)
    else:
        sys.stdout.write(buf.getvalue())
    # Plain-language summary for the reader.
    print("", file=sys.stderr)
    for r in table[1:]:
        label = " ".join(x for x in (r[0], r[1]) if x != "ALL") or "All"
        result = fmt_pct(r[7], r[3])
        counts = "No observations" if r[3] == 0 else "%d of %d opportunities, %s" % (r[7], r[3], result)
        flag = "  (small sample: interpret with care)" if r[9] == "yes" else ""
        print("  %-16s %s%s" % (label, counts, flag), file=sys.stderr)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ipc_tool.py", description="IPC Starter Kit desktop helper (offline, read-only).")
    ap.add_argument("--version", action="version", version="%(prog)s " + TOOL_VERSION)
    sub = ap.add_subparsers(dest="command")
    p1 = sub.add_parser("check-backup", help="check one or more backup files")
    p1.add_argument("files", nargs="+")
    p1.set_defaults(func=cmd_check_backup)
    p2 = sub.add_parser("combine-reports", help="combine hand hygiene report CSVs by adding counts")
    p2.add_argument("files", nargs="+")
    p2.add_argument("--by", choices=["area", "period", "all"], default="area")
    p2.add_argument("--threshold", type=int, default=200,
                    help="flag results with fewer opportunities than this (facility choice, default 200)")
    p2.add_argument("-o", "--output", help="write the combined CSV to this new file")
    p2.set_defaults(func=cmd_combine)
    args = ap.parse_args(argv)
    if not getattr(args, "func", None):
        ap.print_help()
        return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
