#!/usr/bin/env python3
"""Merge Guardian 11 tickers (Q1 2026 Summary of Investment Portfolio PDFs, top-25 tables)
into master. Idempotent: replaces all rows for the tickers it covers."""
import csv, shutil, os

BASE = "/home/hatch/workspace/your_files/canadian-etf-holdings"
MASTER = os.path.join(BASE, "canadian_etf_holdings_MASTER.csv")
RAW_IN = os.path.join(BASE, "guardian_new_raw.csv")
NOTES = os.path.join(BASE, "coverage_notes.csv")
SCHEMA = ["etf_ticker","etf_name","holding_ticker","holding_name","weight_pct",
          "as_of_date","source","provider"]

NAMES = {
    "GBFC": "GuardBonds 2026 Investment Grade Bond Fund",
    "GBFD": "GuardBonds 2027 Investment Grade Bond Fund",
    "GBFE": "GuardBonds 2028 Investment Grade Bond Fund",
    "GBFF": "GuardBonds 2029 Investment Grade Bond Fund",
    "GBLF": "GuardBonds 1-3 Year Laddered Investment Grade Bond Fund",
    "GCBD": "Guardian Canadian Bond Fund",
    "GCEI": "Guardian Canadian Equity Income Fund",
    "GCFE": "Guardian Canadian Focused Equity Fund",
    "GCSC": "Guardian Canadian Diversified Core Equity Fund",
    "GCTB": "Guardian Ultra-Short Canadian T-Bill Fund",
    "GFGE": "Guardian Fundamental Global Equity Fund",
}
# tickers whose published table is effectively the full portfolio
FULL = {"GBFC", "GBFD", "GBFE", "GBFF", "GBLF", "GCTB"}

def main():
    rows = []
    with open(RAW_IN, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            t = r["etf_ticker"]
            assert t in NAMES, t
            rows.append({"etf_ticker": t, "etf_name": NAMES[t],
                         "holding_ticker": r["holding_ticker"].strip(),
                         "holding_name": r["holding_name"].strip(),
                         "weight_pct": float(r["weight_pct"]),
                         "as_of_date": "2026-03-31",
                         "source": "Guardian Document Library Q1 2026 Summary of Investment Portfolio PDF",
                         "provider": "Guardian Capital"})
    tickers = set(r["etf_ticker"] for r in rows)
    assert tickers == set(NAMES)

    shutil.copy2(MASTER, MASTER + ".pre-guard.bak")
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
        if t in FULL:
            new_notes.append((t, "Effectively complete published portfolio (issuer's Summary of Investment Portfolio table covers ~99.5-100% of NAV); as of 2026-03-31. No holding tickers published (except GBLF's underlying ETF units). Fund pages on guardiancapital.com/investmentsolutions are bot-blocked; no CSV/Excel download exists."))
        else:
            new_notes.append((t, "Partial: Top 25 holdings only (issuer's Summary of Investment Portfolio; no complete list or download published); as of 2026-03-31. No holding tickers published."))
    with open(NOTES, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for t, note in new_notes:
            w.writerow([t, note])

    print(f"merged {len(rows)} rows across {len(tickers)} tickers; master rows: {len(kept)+len(rows)}")

if __name__ == "__main__":
    main()
