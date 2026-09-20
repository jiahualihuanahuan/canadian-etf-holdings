#!/usr/bin/env python3
"""Merge Mackenzie batch-2 raw (MALX, MAUG, MAUV, MBAL, MBQG, MCKG, MCLV, MCON, MCSB, MCYC).
MAAA/MAGV already merged - not touched. Idempotent: replaces rows for the tickers it covers."""
import csv, shutil, os
from collections import defaultdict

BASE = "/home/hatch/workspace/your_files/canadian-etf-holdings"
MASTER = os.path.join(BASE, "canadian_etf_holdings_MASTER.csv")
RAW_IN = os.path.join(BASE, "mackenzie_new2_raw.csv")
NOTES = os.path.join(BASE, "coverage_notes.csv")
SCHEMA = ["etf_ticker","etf_name","holding_ticker","holding_name","weight_pct",
          "as_of_date","source","provider"]

NAMES = {
    "MALX": "Mackenzie GQE US Alpha Extension ETF",
    "MAUG": "Mackenzie US All Cap Growth ETF",
    "MAUV": "Mackenzie US Value ETF",
    "MBAL": "Mackenzie Balanced Allocation ETF",
    "MBQG": "Mackenzie GQE Global Balanced ETF",
    "MCKG": "Mackenzie Corporate Knights Global 100 Index ETF",
    "MCLV": "Mackenzie GQE Canada Low Volatility ETF",
    "MCON": "Mackenzie Conservative Allocation ETF",
    "MCSB": "Mackenzie Canadian Short Term Fixed Income ETF",
    "MCYC": "Mackenzie Cyclical Tilt ETF",
}
ASOF = {"MCKG": "2026-09-17"}
SRC = "Mackenzie Investments - Complete Fund Holdings table on fund page (no downloadable file)"

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
                         "as_of_date": ASOF.get(t, "2026-06-30"),
                         "source": SRC,
                         "provider": "Mackenzie"})
    tickers = set(r["etf_ticker"] for r in rows)
    assert tickers == set(NAMES), tickers

    shutil.copy2(MASTER, MASTER + ".pre-mack2.bak")
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
    note_text = {
        "MALX": "Complete published table incl. short positions (negative weights), duplicates as shown (PLD/DXCM/SNDK pairs), cash; as of 2026-06-30. Holding tickers shown on site.",
        "MCKG": "Complete published table; as of 2026-09-17 (site updated more recently than other Mackenzie tables). Duplicates as shown (NOKIA/DXCM/PLD pairs). Holding tickers shown on site.",
        "MCSB": "Complete published table of 179 bonds + cash; as of 2026-06-30. Site table has NO Ticker column.",
    }
    with open(NOTES, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for t in sorted(tickers):
            if t in existing:
                continue
            w.writerow([t, note_text.get(t,
                "Complete published fund-holdings table; as of 2026-06-30. Holding tickers shown on site. Duplicates (e.g. PLD/SNDK/DXCM pairs) transcribed as displayed.")])

    totals = defaultdict(float)
    for r in rows:
        totals[r["etf_ticker"]] += r["weight_pct"]
    print(f"merged {len(rows)} rows across {len(tickers)} tickers; master rows: {len(kept)+len(rows)}")
    for t in sorted(tickers):
        n = sum(1 for r in rows if r["etf_ticker"] == t)
        print(f"  {t}: {n} rows, total {totals[t]:.2f}% (as of {ASOF.get(t,'2026-06-30')})")

if __name__ == "__main__":
    main()
