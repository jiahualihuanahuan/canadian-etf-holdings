#!/usr/bin/env python3
"""Build /tmp/globalx_ingest.csv and /tmp/globalx_notes.txt from parsed Global X data."""
import csv, json, os, re

WORK = os.path.expanduser("~/workspace/your_files/canadian-etf-holdings/raw_extractions/globalx_missing")
BP_DIR = os.path.join(WORK, "html_betapro")

# Tickers with complete direct portfolios from globalx.ca
GX_COMPLETE = ("AGCC AIQ BCCC BCCL BKCC BKCL BNKL CANL CMCC CMCL CNCC CNCL COMX "
               "EACC EACL EMCC EMCL ENCL EQCC EQCL GLCL GRCC HAC HBAL HBNK HCON "
               "HEQL HEQT HEWB HGRW HGY HSAV HSUV HUC HUG HUN HUZ MART PAVE PPLN "
               "QQCC QQCL QQQL REIT RING RNCC RNCL RSCC RSSX SAFE SHLD SVCC SVCL "
               "TTTX UBNK UMRT URCC USCC USCL USSL UTIL").split()
# Bond/cash candidates with <10 holdings (complete)
BOND_KEEP = "CASH CBIL UCSH LPAY MPAY PAYL PAYM PAYS SPAY".split()
# BetaPro futures-based funds with complete published derivatives book (betapro.ca)
BP_COMPLETE = "BITI GLDD GLDU SLVD SLVU VOLX".split()

# Skipped tickers with reasons
SKIP_PARTIAL_GX = ("CHPS CHQQ CNDX COPP CPCC DIVY EAFX EMMX ENCC ETHI GLCC GLDX HAL HAZ "
                   "HBGD HCRE HLIT HMMJ HSH HULC HURA HXCN HXDM HXE HXEM HXF HXH HXX "
                   "INOC MEDX MTRX NRGY NYSX ORBX QQQX RBOT RSCL SLVX TOKN USSX").split()
SKIP_PARTIAL_BP = ("CFOD CFOU CNDD CNDI CNDU GDXD GDXU HQD NRGD NRGU QQI QQU SCND SOXL "
                   "SOXS SPXD SPXI SPXU SQQQ SSPX TCND TQQQ TSPX STLT TTLT").split()

def parse_betapro(ticker):
    html = open(os.path.join(BP_DIR, f"bp_{ticker.lower()}.html"), encoding="utf-8", errors="replace").read()
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    name = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else ticker
    idx = html.find("Top Holdings")
    seg = html[idx:idx + 20000] if idx >= 0 else ""
    m2 = re.search(r"As at\s+([A-Z][a-z]+ \d{1,2}, \d{4})", seg)
    asof = m2.group(1) if m2 else ""
    rows = []
    for mm in re.finditer(r'<p class="text-sonicSilver font-bold">(.*?)</p>\s*<p class="text-white font-normal">\s*(-?[\d,]+\.?\d*)\s*%\s*</p>', seg, re.S):
        n = re.sub(r"\s+", " ", mm.group(1)).strip()
        if "Security Name" in n:
            continue
        rows.append((n, "", mm.group(2).replace(",", "")))
    return name.upper(), asof, rows

def main():
    data = {r["ticker"]: r for r in json.load(open(os.path.join(WORK, "parsed2.json")))}
    out_rows = []
    notes_lines = []
    included = []

    for t in GX_COMPLETE + BOND_KEEP:
        r = data[t]
        assert r["direct"], f"no direct rows for {t}"
        s = sum(float(h["weight"]) for h in r["direct"] if h["weight"])
        included.append((t, len(r["direct"]), s, r["as_of"]))
        for h in r["direct"]:
            out_rows.append({
                "etf_ticker": t,
                "etf_name": (r["fund_name"] or t).upper(),
                "holding_ticker": h["ticker"],
                "holding_name": h["name"],
                "weight_pct": h["weight"],
                "as_of_date": r["as_of"] or "",
                "source": "globalx.ca (python extraction)",
                "provider": "Global X",
            })
        if abs(s - 100) > 1.5:
            notes_lines.append(f"{t}: direct-holdings weight sum = {s:.2f}% (kept; published table sums off 100)")

    for t in BP_COMPLETE:
        name, asof, rows = parse_betapro(t)
        s = sum(float(w) for _, _, w in rows)
        included.append((t, len(rows), s, asof))
        for n, ht, w in rows:
            out_rows.append({
                "etf_ticker": t,
                "etf_name": name,
                "holding_ticker": ht,
                "holding_name": n,
                "weight_pct": w,
                "as_of_date": asof,
                "source": "betapro.ca (python extraction)",
                "provider": "Global X",
            })
        notes_lines.append(f"{t}: futures-only published portfolio ({len(rows)} rows, sums {s:.2f}%) - no cash/margin line published; kept as complete published derivatives book")

    with open("/tmp/globalx_ingest.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["etf_ticker", "etf_name", "holding_ticker",
                                          "holding_name", "weight_pct", "as_of_date",
                                          "source", "provider"])
        w.writeheader()
        w.writerows(out_rows)

    notes = []
    notes.append("GLOBAL X EXTRACTION NOTES")
    notes.append(f"Included tickers: {len(included)}  |  Total rows: {len(out_rows)}")
    notes.append("")
    notes.append("COMPLETENESS RULE APPLIED")
    notes.append("globalx.ca fund pages publish a 'Top Holdings' table of DIRECT holdings plus, for")
    notes.append("fund-of-funds, a separate 'Top Underlying Holdings' look-through table. Only the")
    notes.append("direct table was ingested; the look-through table was excluded (wrapper holdings")
    notes.append("retained, no duplication). A ticker was included only if its direct table summed to")
    notes.append("~100% (within ~1.5pp; a few covered-call/futures funds print 100.1-101.5% due to")
    notes.append("published rounding).")
    notes.append("")
    notes.append("INCLUDED (ticker: rows, weight-sum, as-of)")
    for t, n, s, a in included:
        notes.append(f"  {t}: {n} rows, {s:.2f}%, {a}")
    notes.append("")
    notes.append("SKIPPED - TOP-10/PARTIAL DISCLOSURE ONLY (globalx.ca)")
    notes.append(" ".join(SKIP_PARTIAL_GX))
    notes.append("SKIPPED - TOP-10 REFERENCE-INDEX DISCLOSURE ONLY (betapro.ca; actual holdings are")
    notes.append("swaps/forwards not disclosed by issuer)")
    notes.append(" ".join(SKIP_PARTIAL_BP))
    notes.append("")
    notes.append("SKIPPED - BOND/CASH CANDIDATE WITH >= 10 HOLDINGS (per user rule)")
    notes.append("  UBIL: 10 published rows summing 99.37% - excluded (>=10 holdings).")
    notes.append("")
    notes.append("ANOMALIES / FLAGS")
    for line in notes_lines:
        notes.append("  " + line)
    notes.append("  HAC: page has Long Positions and Short Positions sections. The two short rows")
    notes.append("       ('US DOLLAR FORWARDS - CURRENCY HEDGE' 0.28%, 'CASH, CASH EQUIVALENTS,")
    notes.append("       MARGIN & OTHER' 0.83%) are published with positive weights; kept as published.")
    notes.append("  SVCC: includes a published 0.00% row (SSR MINING INC); kept.")
    notes.append("  Several holding names are truncated in the issuer HTML itself, e.g.")
    notes.append("    'GLOBAL X LITHIUM & BATTERY T', 'GLOBAL X CANADIAN SELECT UNIVERSE BOND INDEX CORPO',")
    notes.append("    'GLOBAL X US 7-10 YEAR TREASURY BOND INDEX CORPORAT', 'GLOBAL X MID-TERM GOVERNMENT")
    notes.append("    BOND PREMIUM YIELD ET', 'GLOBAL X EQUAL WEIGHT CANADIAN TELECOMMUNICATIONS',")
    notes.append("    'ISHARES 7-10 YEAR TREASURY B'. Kept exactly as published; not expanded/invented.")
    notes.append("  URCC direct sum 101.47%, SVCC 101.03%, QQCC 100.28%, EACC 100.52% - published")
    notes.append("       rounding; kept as published.")
    notes.append("  Covered-call/index wrapper ETFs (e.g. CNCC->CNDX, QQCC->QQQX.U, USCC->USSX) hold")
    notes.append("       units of a sibling Global X ETF; wrapper position retained, no look-through.")
    notes.append("")
    notes.append("PAGES RESOLVED VIA betapro.ca")
    notes.append("26 tickers 404'd on globalx.ca/product/{ticker} but are live BetaPro funds whose pages")
    notes.append("live at betapro.ca/product/{ticker} (lowercase). BITI/HQD returned HTTP 200 on")
    notes.append("globalx.ca but rendered no holdings; their betapro.ca pages worked. STLT/TTLT/VOLX")
    notes.append("likewise 404 on globalx.ca but live on betapro.ca. All 31 betapro.ca pages fetched")
    notes.append("via Python; no browser needed.")
    notes.append("")
    notes.append("NO BROWSER USED. All 142 assigned tickers fetched and parsed via Python.")
    notes.append("Raw HTML: raw_extractions/globalx_missing/html/ and html_betapro/")

    with open("/tmp/globalx_notes.txt", "w") as f:
        f.write("\n".join(notes) + "\n")

    print(f"tickers={len(included)} rows={len(out_rows)}")
    print("wrote /tmp/globalx_ingest.csv and /tmp/globalx_notes.txt")

if __name__ == "__main__":
    main()
