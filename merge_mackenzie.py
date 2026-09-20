#!/usr/bin/env python3
"""Merge Mackenzie MAAA + MAGV (complete fund-holdings page tables) into master.
Idempotent: replaces all rows for the tickers it covers."""
import csv, shutil, os

BASE = "/home/hatch/workspace/your_files/canadian-etf-holdings"
MASTER = os.path.join(BASE, "canadian_etf_holdings_MASTER.csv")
RAW_IN = os.path.join(BASE, "mackenzie_new_raw.csv")
NOTES = os.path.join(BASE, "coverage_notes.csv")
SCHEMA = ["etf_ticker","etf_name","holding_ticker","holding_name","weight_pct",
          "as_of_date","source","provider"]

NAMES = {
    "MAAA": "Mackenzie AAA CLO ETF",
    "MAGV": "Mackenzie Global Value ETF",
}

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
                         "as_of_date": "2026-06-30",
                         "source": "mackenzieinvestments.com fund page (Complete Fund Holdings table)",
                         "provider": "Mackenzie Investments"})
    tickers = set(r["etf_ticker"] for r in rows)

    shutil.copy2(MASTER, MASTER + ".pre-mack.bak")
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
        if t == "MAAA":
            new_notes.append((t, "Complete published portfolio (111 rows incl. cash at -3.7%) from Complete Fund Holdings table; as of 2026-06-30. No holding tickers published by issuer."))
        else:
            new_notes.append((t, "Complete published portfolio (67 rows incl. cash) from Complete Fund Holdings table; as of 2026-06-30. Issuer shows a Ticker column; Nokia Oyj appears twice at 1.3% verbatim from the site."))
    with open(NOTES, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for t, note in new_notes:
            w.writerow([t, note])

    print(f"merged {len(rows)} rows across {len(tickers)} tickers; master rows: {len(kept)+len(rows)}")

if __name__ == "__main__":
    main()
