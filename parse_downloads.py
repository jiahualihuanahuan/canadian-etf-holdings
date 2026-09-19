#!/usr/bin/env python3
"""Parse issuer holdings downloads (from browser tasks) into the master holdings CSV.

Scans ~/workspace/browser_downloads/sess-*/ for new files, parses each known
issuer format, and appends rows to canadian_etf_holdings_MASTER.csv.
Tracks processed files in parsed_downloads.json (idempotent re-runs).
"""
import csv, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DL_ROOT = Path.home() / "workspace" / "browser_downloads"
MASTER = HERE / "canadian_etf_holdings_MASTER.csv"
STATE = HERE / "parsed_downloads.json"
MAP = HERE / "download_ticker_map.json"   # filename -> etf ticker (for files w/o ticker in name)

MASTER_COLS = ["etf_ticker", "etf_name", "holding_ticker", "holding_name",
               "weight_pct", "as_of_date", "source", "provider"]

# filename (exact, after the sess timestamp prefix) -> ticker, for files whose
# names don't carry the ticker (Vanguard "Holdings details" files etc.)
SEED_MAP = {
    # Vanguard (from 2026-09-19 task handoff)
    "Holdings_details_-_Vanguard_FTSE_Developed_Asia_Pacific_All_Cap_Index_ETF_-_2026-09-19.xlsx": "VA",
    "Holdings_details_-_Vanguard_Canadian_Aggregate_Bond_Index_ETF_-_2026-09-19.xlsx": "VAB",
    "Holdings_details_-_Vanguard_Balanced_ETF_Portfolio_-_2026-09-19.xlsx": "VBAL",
    "Holdings_details_-_Vanguard_Global_ex-U.S._Aggregate_Bond_Index_ETF__CAD-hedged__-_2026-09-19.xlsx": "VBG",
    "Holdings_details_-_Vanguard_U.S._Aggregate_Bond_Index_ETF__CAD-hedged__-_2026-09-19.xlsx": "VBU",
    "Holdings_details_-_Vanguard_FTSE_Canada_Index_ETF_-_2026-09-19.xlsx": "VCE",
    "Holdings_details_-_Vanguard_FTSE_Canada_All_Cap_Index_ETF_-_2026-09-19.xlsx": "VCN",
    "Holdings_details_-_Vanguard_FTSE_Developed_All_Cap_ex_U.S._Index_ETF_-_2026-09-19.xlsx": "VDU",
    "Holdings_details_-_Vanguard_FTSE_Canadian_High_Dividend_Yield_Index_ETF_-_2026-09-19.xlsx": "VDY",
    "Holdings_details_-_Vanguard_Conservative_ETF_Portfolio_-_2026-09-19.xlsx": "VCNS",
}


def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {"processed": []}


def load_map():
    m = dict(SEED_MAP)
    if MAP.exists():
        m.update(json.loads(MAP.read_text()))
    return m


def clean_weight(v):
    if v is None:
        return ""
    s = str(v).strip().replace("%", "").replace(",", "")
    try:
        return round(float(s), 6)
    except ValueError:
        return ""


def parse_vanguard_xlsx(path):
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows, header_seen, as_of = [], False, ""
    for row in ws.iter_rows(values_only=True):
        vals = [("" if c is None else str(c).strip()) for c in row]
        if not header_seen:
            if vals[0] == "Ticker" and "Holding name" in vals[1]:
                header_seen = True
            elif vals[0].startswith("As at") or vals[0].startswith("As of"):
                as_of = vals[0].replace("As at", "").replace("As of", "").strip()
            continue
        if not vals[0] and not vals[1]:
            continue
        w = clean_weight(vals[2])
        if w == "":
            continue
        rows.append({"holding_ticker": vals[0], "holding_name": vals[1],
                     "weight_pct": w, "as_of": as_of})
    return rows


def parse_bmo_xlsx(path):
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows, header_seen = [], False
    for row in ws.iter_rows(values_only=True):
        vals = [("" if c is None else str(c).strip()) for c in row]
        if not header_seen:
            if vals[0] == "Weight (%)" and vals[1] == "Name":
                header_seen = True
            continue
        if not vals[1]:
            continue
        w = clean_weight(vals[0])
        if w == "":
            continue
        rows.append({"holding_ticker": "", "holding_name": vals[1],
                     "weight_pct": w, "as_of": ""})
    return rows


def parse_ishares_csv(path):
    text = read_text_smart(path)
    lines = text.splitlines()
    as_of = ""
    start = 0
    for i, ln in enumerate(lines[:6]):
        m = re.search(r"Fund Holdings as of,\s*\"?([^\"]+)\"?", ln)
        if m:
            as_of = m.group(1).strip()
        if ln.startswith("Ticker,"):
            start = i
            break
    rows = []
    for rec in csv.DictReader(lines[start:]):
        # iShares fund-of-funds files repeat the "Fund Holdings as of" header
        # before an underlying-fund look-through section: stop at the repeat.
        if (rec.get("Ticker") or "").strip() == "Fund Holdings as of":
            break
        name = (rec.get("Name") or "").strip()
        if not name:
            continue
        w = clean_weight(rec.get("Weight (%)"))
        if w == "":
            continue
        t = (rec.get("Ticker") or "").strip()
        rows.append({"holding_ticker": t if t and t != "-" else "",
                     "holding_name": name, "weight_pct": w, "as_of": as_of})
    return rows


def build_etf_universe():
    """All known Canadian ETF tickers (base, no class suffix) for fund-of-funds detection."""
    uni = set()
    for f in [HERE / "canadian_etf_list.csv", HERE / "universe_expansion_new.csv"]:
        if f.exists():
            for r in csv.DictReader(open(f, encoding="utf-8-sig")):
                t = (r.get("ticker") or "").strip().split(".")[0]
                if t:
                    uni.add(t)
    # also add known US-listed iShares ETFs commonly held
    uni.update(["ITOT", "IEMG", "EEM", "IVV", "AGG", "TLT", "IEF"])
    return uni


ETF_UNIVERSE = build_etf_universe()
COVERAGE_NOTES = {}  # etf_ticker -> note


def apply_fof_filter(ticker, rows):
    """For fund-of-funds files containing direct holdings + full look-through
    (weights sum ~200%), keep only the direct holdings, which are listed first
    in the file. Find the split point where the cumulative weight first reaches
    ~100% and the remainder also sums to ~100% (a second full section)."""
    if not rows:
        return rows
    total = sum(r["weight_pct"] for r in rows)
    if not (185 <= total <= 215):
        return rows
    cum = 0.0
    for i, r in enumerate(rows):
        cum += r["weight_pct"]
        if cum >= 99.0:
            rest = total - cum
            if 95 <= cum <= 105 and 95 <= rest <= 105:
                keep = rows[:i + 1]
                COVERAGE_NOTES[ticker] = (
                    f"fund-of-funds: file contained direct holdings + full look-through "
                    f"(summed {total:.1f}%); kept {len(keep)} direct holdings only")
                return keep
            break
    return rows


def read_text_smart(path):
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, ValueError):
            continue
    return raw.decode("utf-8", errors="replace")


def parse_evolve_csv(path):
    rows = []
    text = read_text_smart(path)
    for rec in csv.DictReader(text.splitlines()):
            name = (rec.get("SECURITY_NAME") or "").strip()
            if not name:
                continue
            try:
                w = round(float(rec.get("PORTFOLIO_MWEIGHT") or 0) * 100, 6)
            except ValueError:
                continue
            if w == 0:
                continue
            raw = (rec.get("TICKER") or "").strip().strip('"')
            t = raw.split()[0] if raw else ""
            rows.append({"holding_ticker": t, "holding_name": name,
                         "weight_pct": w, "as_of": ""})
    return rows


def parse_ci_csv(path):
    text = read_text_smart(path)
    lines = text.splitlines()
    as_of, start = "", 0
    for i, ln in enumerate(lines[:6]):
        m = re.search(r"As of\s+(\d{4}-\d{2}-\d{2})", ln)
        if m:
            as_of = m.group(1)
        if ln.startswith("Name,"):
            start = i
            break
    rows = []
    for rec in csv.DictReader(lines[start:]):
        name = (rec.get("Name") or "").strip()
        if not name:
            continue
        w = clean_weight(rec.get("Percent %"))
        if w == "":
            continue
        t = (rec.get("Ticker") or "").strip()
        rows.append({"holding_ticker": t if t else "", "holding_name": name,
                     "weight_pct": w, "as_of": as_of})
    return rows


def parse_rbc_csv(path):
    """RBC GAM format: preamble lines, then \"Holding\",\"Value (%)\" header, then name/weight rows."""
    rows = [r for r in csv.reader(open(path, encoding="utf-8-sig")) if any(c.strip() for c in r)]
    as_of = ""
    hdr_idx = -1
    for i, r in enumerate(rows[:20]):
        cells = [c.strip() for c in r]
        low = [c.lower() for c in cells]
        m = re.search(r"as of\s+([\d/]+)", " ".join(low))
        if m:
            as_of = m.group(1)
        if low[0] in ("holding", "holdings", "name", "security", "issuer"):
            if any("value" in c or "weight" in c or "%" in c for c in low):
                hdr_idx = i
                break
    if hdr_idx < 0:
        return []
    out = []
    for r in rows[hdr_idx + 1:]:
        cells = [c.strip() for c in r]
        if len(cells) < 2:
            continue
        name, w = cells[0], clean_weight(cells[1])
        if not name or w == "":
            continue
        nl = name.lower()
        if "total" in nl or nl.startswith("grand"):
            continue
        out.append({"holding_ticker": "", "holding_name": name, "weight_pct": w, "as_of": as_of})
    return out


# CI fund-name fragment -> ticker fallback (when filename not in explicit map)
CI_NAME_TO_TICKER = {
    "CIBalancedAssetAllocationETF": "CBAL",
    "CIBalancedGrowthAssetAllocationETF": "CBGR",
    "CIBalancedIncomeAssetAllocationETF": "CBIN",
    "CIConservativeAssetAllocationETF": "CCNV",
    "CIBalancedPlusAssetAllocationETFFund": "CBAP",
    "CIEquityPlusAssetAllocationETFFund": "CEQP",
    "CIGrowthAssetAllocationETF": "CGRO",
    "CICanadianShort-TermAggregateBondIndexETF": "CAGS",
    "CIEuropeHedgedEquityIndexETF": "EHE",
    "CIU.S.MidCapDividendIndexETF": "UMI",
    "XTLTU": "XTLT-U",
    "CIInternationalQualityDividendGrowthIndexETF": "IQD",
    "CIMorningstarCanadaMomentumIndexETF": "WXM",
    "CIEmergingMarketsDividendIndexETF": "EMV.B",
    "CICanadaQualityDividendGrowthIndexETF": "DGRC",
    "CIU.S.QualityDividendGrowthIndexETF": "DGR",
    "XUSCU": "XUSC-U",
    "XUUU": "XUU-U",
    "CIEquityAssetAllocationETF": "CEQT",
}


def _hint_for_filename(rest):
    """Provider hint from filename patterns (independent of ticker mapping)."""
    if re.match(r"([A-Z]{2,6}(?:\.[A-Z])?)\.csv$", rest):          # ARTI.csv, AGG.csv
        return "Evolve"
    if re.match(r"([A-Z]{2,6})_holdings\.csv$", rest):             # XBB_holdings.csv
        return "iShares"
    if re.match(r"Holdings_Extract_en_US_([A-Z]{2,6})_\d+\.xlsx$", rest):  # BMO
        return "BMO"
    if re.match(r"(CI.+?)_holdings_en_\d{4}-\d{2}-\d{2}\.csv$", rest):  # CI
        return "CI"
    if re.match(r"([A-Z]{2,6})_Holdings_History\.csv$", rest):     # Purpose BTCC (price hist)
        return "Purpose-history"
    if re.match(r"Scotia_ETF_Holdings_([A-Z]{2,6})(?:-a)?\.csv$", rest):  # Scotia index trackers
        return "Scotia"
    return None


def detect_ticker(fname, fmap):
    """Return (etf_ticker, provider_hint) from a download filename."""
    # strip the browser-download timestamp prefix: browser-download-<ts>-<n>-<rest>
    m = re.match(r"browser-download-[^-]+-\d+-(.*)$", fname)
    rest = m.group(1) if m else fname
    hint = _hint_for_filename(rest)
    if fname in fmap:
        return fmap[fname], hint
    if rest in fmap:
        return fmap[rest], hint
    m2 = re.match(r"([A-Z]{2,6}(?:\.[A-Z])?)\.csv$", rest)          # ARTI.csv, AGG.csv
    if m2:
        return m2.group(1), "Evolve"
    m2 = re.match(r"([A-Z]{2,6})_holdings\.csv$", rest)             # XBB_holdings.csv
    if m2:
        return m2.group(1), "iShares"
    m2 = re.match(r"Holdings_Extract_en_US_([A-Z]{2,6})_\d+\.xlsx$", rest)  # BMO
    if m2:
        return m2.group(1), "BMO"
    m2 = re.match(r"(CI.+?)_holdings_en_\d{4}-\d{2}-\d{2}\.csv$", rest)  # CI
    if m2:
        return CI_NAME_TO_TICKER.get(m2.group(1), m2.group(1)), "CI"
    m2 = re.match(r"([A-Z]{2,6})_Holdings_History\.csv$", rest)     # Purpose BTCC (price hist)
    if m2:
        return m2.group(1), "Purpose-history"
    m2 = re.match(r"Scotia_ETF_Holdings_([A-Z]{2,6})(?:-a)?\.csv$", rest)  # Scotia index trackers
    if m2:
        return m2.group(1), "Scotia"
    return None, None


def parse_scotia_csv(path):
    """Scotia index-tracker CSVs: 'Top Holdings,Weight (%)' then "name", weight rows."""
    raw = read_text_smart(path).splitlines()
    out = []
    for ln in raw:
        if not ln.strip() or ln.lower().startswith("top holdings"):
            continue
        cells = list(csv.reader([ln]))[0]
        if len(cells) < 2:
            continue
        name, w = cells[0].strip().strip('"'), clean_weight(cells[1])
        if not name or w == "":
            continue
        nl = name.lower()
        if "total" in nl or nl.startswith("grand"):
            continue
        out.append({"holding_ticker": "", "holding_name": name,
                    "weight_pct": w, "as_of": "2026-08-31"})
    return out


def parse_file(path, ticker, provider_hint):
    suf = path.suffix.lower()
    if provider_hint == "Purpose-history":
        return []  # price history, not holdings
    if "Holdings_details" in path.name or (suf == ".xlsx" and "Vanguard" in path.name):
        return parse_vanguard_xlsx(path)
    if provider_hint == "Scotia":
        return parse_scotia_csv(path)
    if suf == ".xlsx":
        return parse_bmo_xlsx(path)
    head = read_text_smart(path)[:2000]
    if provider_hint == "Evolve" or "PORTFOLIO_MWEIGHT" in head:
        return parse_evolve_csv(path)
    if provider_hint == "CI":
        return parse_ci_csv(path)
    if provider_hint == "RBC" or "rbcgam.com" in head:
        return parse_rbc_csv(path)
    return parse_ishares_csv(path)


PROVIDER_BY_TICKER_PREFIX = {}  # filled from universe files below


# filename fragments that are never ETFs — skip even if parseable
BLOCKLIST = ["PrivatePool", "download.pdf", "OpportunitiesFund_holdings"]


def main():
    state = load_state()
    processed = set(state["processed"])
    fmap = load_map()

    # provider lookup from universe files
    prov = {}
    for f in [HERE / "canadian_etf_list.csv", HERE / "universe_expansion_new.csv"]:
        if f.exists():
            for r in csv.DictReader(open(f, encoding="utf-8-sig")):
                p = r.get("provider") or r.get("Provider") or ""
                t = (r.get("ticker") or "").strip()
                if t:
                    prov[t] = p

    files = sorted(DL_ROOT.glob("sess-*/browser-download-*"))
    new_rows, n_files, skipped = [], 0, 0
    for path in files:
        key = str(path)
        if key in processed:
            continue
        if any(b in path.name for b in BLOCKLIST):
            processed.add(key)
            continue
        ticker, hint = detect_ticker(path.name, fmap)
        if not ticker:
            skipped += 1
            continue
        try:
            holdings = parse_file(path, ticker, hint)
            holdings = apply_fof_filter(ticker, holdings)
        except Exception as e:
            print(f"PARSE FAIL {path.name}: {e}", file=sys.stderr)
            continue
        for h in holdings:
            new_rows.append({
                "etf_ticker": ticker,
                "etf_name": "",
                "holding_ticker": h["holding_ticker"],
                "holding_name": h["holding_name"],
                "weight_pct": h["weight_pct"],
                "as_of_date": h["as_of"],
                "source": f"issuer-download:{path.name}",
                "provider": prov.get(ticker, {"CI": "CI Global Asset Management"}.get(hint, hint or "")),
            })
        processed.add(key)
        n_files += 1

    # special-case: Purpose BTCC/BTCC.B/BTCC.U are pure bitcoin ETFs
    # (their "Holdings_History" downloads are price series, not holdings)
    existing = {r["etf_ticker"] for r in new_rows}
    if MASTER.exists():
        for r in csv.DictReader(open(MASTER, encoding="utf-8")):
            existing.add(r["etf_ticker"])
    for t in ["BTCC", "BTCC.B", "BTCC.U"]:
        if t not in existing:
            new_rows.append({"etf_ticker": t, "etf_name": "Purpose Bitcoin ETF",
                             "holding_ticker": "BTC", "holding_name": "Bitcoin",
                             "weight_pct": 100.0, "as_of_date": "2026-09-19",
                             "source": "issuer:single-asset-crypto",
                             "provider": "Purpose Investments Inc."})

    if new_rows:
        write_header = not MASTER.exists()
        with open(MASTER, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=MASTER_COLS)
            if write_header:
                w.writeheader()
            w.writerows(new_rows)
    if COVERAGE_NOTES:
        nf = HERE / "coverage_notes.csv"
        have = set()
        if nf.exists():
            for r in csv.DictReader(open(nf, encoding="utf-8")):
                have.add(r["etf_ticker"])
        with open(nf, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["etf_ticker", "note"])
            if not have:
                w.writeheader()
            for t, n in COVERAGE_NOTES.items():
                if t not in have:
                    w.writerow({"etf_ticker": t, "note": n})
    state["processed"] = sorted(processed)
    STATE.write_text(json.dumps(state, indent=1))
    print(f"files parsed: {n_files}, skipped (no ticker): {skipped}, "
          f"new holding rows: {len(new_rows)}")


if __name__ == "__main__":
    main()
