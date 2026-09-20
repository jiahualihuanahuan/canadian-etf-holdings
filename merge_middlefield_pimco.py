#!/usr/bin/env python3
"""Merge Middlefield (top-10 page tables) + PIMCO (official xlsx downloads) into master.
Idempotent: replaces all rows for the tickers it covers. PMIF.U duplicates PMIF (same fund file).
PIMCO file date is 2026-06-30 (Unaudited) per the workbooks themselves."""
import csv, glob, re, shutil, os
import openpyxl

BASE = "/home/hatch/workspace/your_files/canadian-etf-holdings"
DL = "/home/hatch/workspace/browser_downloads/sess-3597525341"
MASTER = os.path.join(BASE, "canadian_etf_holdings_MASTER.csv")
NOTES = os.path.join(BASE, "coverage_notes.csv")
SCHEMA = ["etf_ticker","etf_name","holding_ticker","holding_name","weight_pct",
          "as_of_date","source","provider"]

MIDDLEFIELD_NAMES = {
    "MAEC": "Middlefield ActivEnergy Dividend Class - ETF Series",
    "MDIV": "Middlefield Global Dividend Growers ETF",
    "MHCD": "Middlefield Healthcare Dividend ETF",
    "MINF": "Middlefield Global Infrastructure Dividend ETF",
    "MINN": "Middlefield Innovation Dividend ETF",
    "MIPC": "Middlefield Income Plus Class - ETF Series",
    "MREL": "Middlefield Real Estate Dividend ETF",
    "MSBP": "Middlefield Short Duration Bond Plus ETF",
    "MUSA": "Middlefield U.S. Equity Dividend ETF",
}
# ticker -> (filename pattern, fund name); PMIF.U duplicates PMIF's file
PIMCO = {
    "CORE": ("Canadian_Core_Bond_Fund", "PIMCO Canadian Core Bond Fund"),
    "IGCF": ("Investment_Grade_Credit_Fund_Canada", "PIMCO Investment Grade Credit Fund (Canada)"),
    "PCON": ("Managed_Conservative_Bond_Pool", "PIMCO Managed Conservative Bond Pool"),
    "PCOR": ("Managed_Core_Bond_Pool", "PIMCO Managed Core Bond Pool"),
    "PLDI": ("Low_Duration_Monthly_Income_Fund_Canada", "PIMCO Low Duration Monthly Income Fund (Canada)"),
    "PMIF": ("Monthly_Income_Fund_Canada", "PIMCO Monthly Income Fund (Canada)"),
    "PMNT": ("Global_Short_Maturity_Fund_Canada", "PIMCO Global Short Maturity Fund (Canada)"),
}

def main():
    rows = []
    # --- Middlefield: top-10 page tables from browser handoff ---
    import io
    raw = io.StringIO(open(os.path.join(BASE, "middlefield_new_raw.csv"), encoding="utf-8").read())
    for r in csv.DictReader(raw):
        t = r["etf_ticker"]
        assert t in MIDDLEFIELD_NAMES, t
        rows.append({"etf_ticker": t, "etf_name": MIDDLEFIELD_NAMES[t],
                     "holding_ticker": "", "holding_name": r["holding_name"].strip(),
                     "weight_pct": float(r["weight_pct"]), "as_of_date": "2026-08-31",
                     "source": "middlefield.com fund page (Top 10 holdings table)",
                     "provider": "Middlefield"})
    tickers = set(MIDDLEFIELD_NAMES)

    # --- PIMCO: official xlsx ---
    for ticker, (pat, name) in PIMCO.items():
        cands = glob.glob(os.path.join(DL, f"*{pat}_HLD_Data.xlsx"))
        if ticker == "PMIF":
            cands = [c for c in cands if "Low_Duration" not in c]
        assert len(cands) == 1, (pat, cands)
        files = cands
        wb = openpyxl.load_workbook(files[0], data_only=True, read_only=True)
        ws = wb["Portfolio Holdings"]
        holdings = []
        for row in ws.iter_rows(min_row=12, values_only=True):
            desc = (row[5] or "").strip() if isinstance(row[5], str) else row[5]
            tk = (row[4] or "").strip() if isinstance(row[4], str) else ""
            w = row[13]
            if not desc or not isinstance(w, (int, float)):
                continue
            if re.search(r"\btotal\b", str(desc).lower()) and len(str(desc)) < 30:
                continue
            holdings.append((tk, str(desc), w * 100))
        total = sum(h[2] for h in holdings)
        for tk, desc, w in holdings:
            rows.append({"etf_ticker": ticker, "etf_name": name,
                         "holding_ticker": tk, "holding_name": desc,
                         "weight_pct": round(w, 6), "as_of_date": "2026-06-30",
                         "source": "PIMCO official holdings Excel (pimco.com)",
                         "provider": "PIMCO Canada"})
        tickers.add(ticker)
        print(f"{ticker}: {len(holdings)} rows, total {total*100:.2f}%")
    # PMIF.U duplicates PMIF (same fund-level file, verified)
    for r in [r for r in rows if r["etf_ticker"] == "PMIF"]:
        c = dict(r)
        c["etf_ticker"] = "PMIF.U"
        c["etf_name"] = "PIMCO Monthly Income Fund (Canada) (ETF Series - USD)"
        c["source"] = "PIMCO official holdings Excel (pimco.com) — USD class, same fund-level file as PMIF"
        rows.append(c)
    tickers.add("PMIF.U")

    # idempotent merge
    shutil.copy2(MASTER, MASTER + ".pre-mfp.bak")
    kept = []
    with open(MASTER, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["etf_ticker"] not in tickers:
                kept.append(row)
    tmp = MASTER + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SCHEMA)
        w.writeheader()
        w.writerows(kept)
        w.writerows(rows)
    os.replace(tmp, MASTER)

    existing = set()
    with open(NOTES, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            existing.add(row["etf_ticker"])
    new_notes = []
    for t in sorted(tickers):
        if t in existing:
            continue
        if t in MIDDLEFIELD_NAMES:
            new_notes.append((t, "Partial: Top 10 holdings only (middlefield.com publishes no complete list or download); as of 2026-08-31. No holding tickers published."))
        elif t == "PMIF.U":
            new_notes.append((t, "Complete holdings duplicated from PMIF (same fund-level PIMCO file; USD ETF class); as of 2026-06-30."))
        else:
            new_notes.append((t, "Complete holdings from PIMCO official Excel download; as of 2026-06-30 (Unaudited) per workbook (note: file predates the 2026-08-31 portfolio composition date)."))
    if "PBAL" not in existing:
        new_notes.append(("PBAL", "New fund (inception 2026-01-26); PIMCO publishes no holdings Excel or holdings table — only sector allocation and a Portfolio Statistics PDF; no holdings data available."))
    with open(NOTES, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for t, note in new_notes:
            w.writerow([t, note])

    print(f"merged {len(rows)} rows across {len(tickers)} tickers; master rows: {len(kept)+len(rows)}")

if __name__ == "__main__":
    main()
