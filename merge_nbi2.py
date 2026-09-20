#!/usr/bin/env python3
"""Merge NBI new-batch (35 tickers) into master. Idempotent: replaces all rows
for the tickers it covers. All are top-N partials; NBIV is terminated."""
import csv, shutil, os

BASE = "/home/hatch/workspace/your_files/canadian-etf-holdings"
MASTER = os.path.join(BASE, "canadian_etf_holdings_MASTER.csv")
RAW_IN = os.path.join(BASE, "nbi_new_batch_raw.csv")
NOTES = os.path.join(BASE, "coverage_notes.csv")
SCHEMA = ["etf_ticker","etf_name","holding_ticker","holding_name","weight_pct",
          "as_of_date","source","provider"]

NAMES = {
    "NALT": "NBI Liquid Alternatives ETF",
    "NBBX": "NBI Canadian Bond Index Fund - ETF Series",
    "NBCG": "NBI Canadian Equity Growth Fund - ETF Series",
    "NBCX": "NBI Canadian Equity Index Fund - ETF Series",
    "NBEM": "NBI Diversified Emerging Markets Equity Fund - ETF Series",
    "NBGE": "NBI Global Equity Fund - ETF Series",
    "NBGE.F": "NBI Global Equity Fund - ETFH Series",
    "NBIE": "NBI International Equity Fund - ETF Series",
    "NBIE.F": "NBI International Equity Fund - ETFH Series",
    "NBIX": "NBI International Equity Index Fund - ETF Series",
    "NBLD": "NBI Balanced ETF Portfolio",
    "NBQC": "NBI Quebec Growth Fund - ETF Series",
    "NBSC": "NBI Global Small Cap Fund - ETF Series",
    "NREA": "NBI Global Real Assets Income Fund - ETF Series",
    "NSCB": "NBI Sustainable Canadian Bond ETF",
    "NSCC": "NBI Sustainable Canadian Corporate Bond ETF",
    "NSCE": "NBI Sustainable Canadian Equity ETF",
    "NSDG": "NBI SmartData Global Equity Fund - ETF Series",
    "NSDI": "NBI SmartData International Equity Fund - ETF Series",
    "NSDI.F": "NBI SmartData International Equity Fund - ETFH Series",
    "NSDU": "NBI SmartData U.S. Equity Fund - ETF Series",
    "NSDU.F": "NBI SmartData U.S. Equity Fund - ETFH Series",
    "NSGE": "NBI Sustainable Global Equity ETF",
    "NSSB": "NBI Sustainable Canadian Short Term Bond ETF",
    "NTGA": "NBI Target 2026 Investment Grade Bond Fund - ETF Series",
    "NTGB": "NBI Target 2027 Investment Grade Bond Fund - ETF Series",
    "NTGC": "NBI Target 2028 Investment Grade Bond Fund - ETF Series",
    "NTGD": "NBI Target 2029 Investment Grade Bond Fund - ETF Series",
    "NTGE": "NBI Target 2030 Investment Grade Bond Fund - ETF Series",
    "NTGF": "NBI Target 2031 Investment Grade Bond Fund - ETF Series",
    "NTHM": "NBI Thematic Rotation ETF",
    "NUBF": "NBI Unconstrained Fixed Income ETF",
    "NUSA": "NBI Active U.S. Equity ETF",
    "NUSA.F": "NBI Active U.S. Equity ETF - CAD Hedged",
}

def main():
    rows = []
    with open(RAW_IN, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            t = r["etf_ticker"]
            assert t in NAMES, t
            rows.append({
                "etf_ticker": t, "etf_name": NAMES[t],
                "holding_ticker": r["holding_ticker"].strip(),
                "holding_name": r["holding_name"].strip(),
                "weight_pct": float(r["weight_pct"]),
                "as_of_date": "2026-08-31",
                "source": "nbinvestments.ca fund page Allocation tab (Top 10 holdings table)",
                "provider": "NBI",
            })
    tickers = set(r["etf_ticker"] for r in rows)
    assert tickers == set(NAMES), f"mismatch: {set(NAMES)-tickers}"

    shutil.copy2(MASTER, MASTER + ".pre-nbi2.bak")
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
        if t not in existing:
            extra = " (only 3 rows published on site)" if t == "NSDG" else ""
            new_notes.append((t, f"Partial: Top 10 holdings only (issuer publishes no complete list or download){extra}; as of 2026-08-31. Holding tickers shown by issuer only for ETF holdings."))
    if "NBIV" not in existing:
        new_notes.append(("NBIV", "Terminated: ETF series not found in NBI fund search (only mutual-fund series remain); still referenced in NCNS/NEQT/NGRW/NBLD holdings tables as of 2026-08-31."))
    with open(NOTES, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for t, note in new_notes:
            w.writerow([t, note])

    print(f"merged {len(rows)} rows across {len(tickers)} tickers; master rows: {len(kept)+len(rows)}")

if __name__ == "__main__":
    main()
