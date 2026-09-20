#!/usr/bin/env python3
"""Merge Fidelity browser-extracted holdings into the master CSV.

Idempotent: skips only rows that are exact duplicates of the full
master row (etf_ticker, etf_name, holding_ticker, holding_name,
weight_pct, as_of_date, source, provider). Never collapses rows on a
partial key — legitimate repeated positions are preserved.

Fidelity publishes holding names + weights only (no holding tickers);
holding_ticker is written blank.
"""
import csv, os, sys

BASE = os.path.dirname(os.path.abspath(__file__))
MASTER = os.path.join(BASE, "canadian_etf_holdings_MASTER.csv")
NOTES = os.path.join(BASE, "coverage_notes.csv")
RAW = os.path.join(BASE, "fidelity_holdings_raw.csv")
COLS = ["etf_ticker", "etf_name", "holding_ticker", "holding_name",
        "weight_pct", "as_of_date", "source", "provider"]

rows, keys = [], set()
with open(MASTER, newline='', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        rows.append(row)
        keys.add((row['etf_ticker'], row['etf_name'], row['holding_ticker'],
                  row['holding_name'], str(row['weight_pct']),
                  row['as_of_date'], row['source'], row['provider']))

# back up before merge
with open(MASTER + ".bak-fidelity", "w", newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=COLS)
    w.writeheader()
    w.writerows(rows)

new_rows, counts = [], {}
with open(RAW, newline='', encoding='utf-8') as f:
    for rec in csv.DictReader(f):
        t = rec['TICKER'].strip()
        name = rec['holding_name'].strip()
        w = rec['weight_pct'].strip()
        try:
            w = round(float(w), 6)
        except ValueError:
            w = ""
        key = (t, '', '', name, str(w), rec['as_of'].strip(),
               'browser:fidelity.ca_2026-09-19', 'Fidelity Investments Canada')
        if key in keys:
            continue
        keys.add(key)
        new_rows.append(dict(zip(COLS, key)))
        counts[t] = counts.get(t, 0) + 1

with open(MASTER, 'a', newline='', encoding='utf-8') as f:
    csv.DictWriter(f, fieldnames=COLS).writerows(new_rows)

# normalize literal 'n/a' holding tickers to blank for fidelity rows
norm = 0
for r in rows + new_rows:
    if r['provider'] == 'Fidelity Investments Canada' and r['holding_ticker'].strip().lower() == 'n/a':
        r['holding_ticker'] = ''
        norm += 1
if norm:
    with open(MASTER, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows + new_rows)

notes = {
    'FAUS': 'Fidelity: full 136-holding table extracted 2026-06-30; issuer publishes holding names + weights only, no holding tickers',
    'FBAL': 'Fidelity: fund-of-funds; 18 underlying funds (all categories expanded) as of 2026-09-18; complete at fund level',
    'FBTC': 'Fidelity: single-asset bitcoin ETF; no holdings table published, weight set to 100% Bitcoin (2026-09-18)',
    'FBTC.U': 'Fidelity: single-asset bitcoin ETF (USD series); no holdings table published, weight set to 100% Bitcoin (2026-09-18)',
}
have = {r['etf_ticker'] for r in csv.DictReader(open(NOTES, encoding='utf-8'))}
with open(NOTES, 'a', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['etf_ticker', 'note'])
    for t, n in notes.items():
        if t not in have:
            w.writerow({'etf_ticker': t, 'note': n})

print(f"Added {len(new_rows)} Fidelity rows: {counts}; normalized {norm} n/a tickers")
print(f"Master: {len(rows) + len(new_rows)} rows")
