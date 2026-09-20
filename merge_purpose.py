#!/usr/bin/env python3
"""Merge Purpose Investments browser-extracted holdings into the master CSV.

Master schema: etf_ticker, etf_name, holding_ticker, holding_name,
               weight_pct, as_of_date, source, provider
Completeness/partial info goes to coverage_notes.csv (etf_ticker, note).

Special cases:
- BTCC classes: skipped (already in master as single-asset BTC 100%)
- KILO/SBT classes: ounce-denominated single physical asset -> 100% Gold/Silver Bars
- SYLD: issuer publishes only top-10 with coupon yield, not weights -> blank weight + note
- BNC/BND/IGB: TOP-10 ONLY partials
- PIN/PINC/PRA/PRP: TOP-5-PER-CATEGORY partials
- Terminated / not-found tickers recorded in coverage_notes.csv
Idempotent: skips (etf_ticker, holding_name, weight_pct) already present.
"""
import csv, os

BASE = os.path.dirname(os.path.abspath(__file__))
MASTER = os.path.join(BASE, "canadian_etf_holdings_MASTER.csv")
NOTES = os.path.join(BASE, "coverage_notes.csv")
RAW = os.path.join(BASE, "purpose_holdings_raw.csv")

COLS = ["etf_ticker", "etf_name", "holding_ticker", "holding_name",
        "weight_pct", "as_of_date", "source", "provider"]

TERMINATED = {"MJJ", "PEU", "PEU.B", "PUD", "PUD.B", "SBND"}
NOT_FOUND = {"FLOT", "FLOT.B", "FLOT.U", "PCF", "PFG"}
TOP10 = {"BNC", "BND", "IGB"}
TOP5CAT = {"PIN", "PINC", "PRA", "PRP"}
SKIP_DUP = {"BTCC", "BTCC.B", "BTCC.U"}  # already in master as single-asset

NOTES_TO_ADD = {}
for t in TERMINATED:
    NOTES_TO_ADD[t] = "Purpose: fund terminated per purpose.com (browser extraction 2026-09-19); excluded from holdings"
for t in NOT_FOUND:
    NOTES_TO_ADD[t] = "Purpose: ticker not found on purpose.com; unverified (browser extraction 2026-09-19)"
for t in TOP10:
    NOTES_TO_ADD[t] = "Purpose: issuer publishes only top-10 holdings for this fund; full ticker-level holdings unavailable (2026-09-19)"
for t in TOP5CAT:
    NOTES_TO_ADD[t] = "Purpose: issuer publishes only top-five holdings per category for this fund; full ticker-level holdings unavailable (2026-09-19)"
NOTES_TO_ADD["SYLD"] = "Purpose: issuer publishes only top-10 holdings with coupon yield (not weight %); weights unavailable (2026-09-19)"
for t in ["KILO", "KILO.B", "KILO.U"]:
    NOTES_TO_ADD[t] = "Purpose: single physical asset (gold bars, 187,449 oz per 2026-09-18); weight set to 100% single asset"
for t in ["SBT", "SBT.B", "SBT.U"]:
    NOTES_TO_ADD[t] = "Purpose: single physical asset (silver bars, 1,598,047 oz per 2026-09-18); weight set to 100% single asset"


def main():
    rows, keys = [], set()
    with open(MASTER, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            rows.append(row)
            keys.add((row['etf_ticker'], row['holding_name'], str(row['weight_pct'])))

    new_rows, counts = [], {}
    with open(RAW, newline='', encoding='utf-8') as f:
        for rec in csv.DictReader(f):
            t = rec['TICKER'].strip()
            if t in SKIP_DUP:
                continue
            name = rec['holding_name'].strip()
            raw_w = rec['weight_pct'].strip()
            w = raw_w
            if t.startswith("KILO"):
                name, w = "Gold Bars", "100"
            elif t.startswith("SBT"):
                name, w = "Silver Bars", "100"
            elif t == "SYLD":
                w = ""  # yields, not weights; see coverage note
            try:
                w = round(float(w), 6) if w != "" else ""
            except ValueError:
                w = ""
            key = (t, name, str(w))
            if key in keys:
                continue
            keys.add(key)
            new_rows.append({
                'etf_ticker': t,
                'etf_name': '',
                'holding_ticker': rec['holding_ticker'].strip() or 'n/a',
                'holding_name': name,
                'weight_pct': w,
                'as_of_date': rec['as_of'].strip(),
                'source': 'browser:purpose.com_2026-09-19',
                'provider': 'Purpose Investments Inc.',
            })
            counts[t] = counts.get(t, 0) + 1

    with open(MASTER, 'a', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writerows(new_rows)

    have = set()
    if os.path.exists(NOTES):
        with open(NOTES, newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                have.add(row['etf_ticker'])
    with open(NOTES, 'a', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['etf_ticker', 'note'])
        for t, n in sorted(NOTES_TO_ADD.items()):
            if t not in have:
                w.writerow({'etf_ticker': t, 'note': n})

    print(f"Added {len(new_rows)} Purpose rows")
    for t, c in sorted(counts.items()):
        print(f"  {t}: {c}")
    print(f"Master now has {len(rows) + len(new_rows)} data rows; "
          f"{len({r['etf_ticker'] for r in rows} | set(counts))} etfs")


if __name__ == "__main__":
    main()
