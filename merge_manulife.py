#!/usr/bin/env python3
"""Merge manulife_holdings_raw.csv (TICKER,HOLDING_TICKER,HOLDING_NAME,WEIGHT_PCT,AS_OF_DATE)
into the 8-col master. Idempotent."""
import csv, os

BASE = os.path.dirname(os.path.abspath(__file__))
MASTER = os.path.join(BASE, 'canadian_etf_holdings_MASTER.csv')
RAW = os.path.join(BASE, 'manulife_holdings_raw.csv')
FIELDS = ['etf_ticker','etf_name','holding_ticker','holding_name','weight_pct','as_of_date','source','provider']

NAMES = {
    'BSKT': 'Manulife Smart Core Bond ETF',
}
SRC = 'browser:manulifeim.com_2026-09-19'
PROV = 'Manulife'

def main():
    existing = set()
    with open(MASTER, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            existing.add((r['etf_ticker'], r['holding_ticker'], r['holding_name'], r['weight_pct']))
    n_new = 0
    counts = {}
    with open(RAW, encoding='utf-8') as f, open(MASTER, 'a', newline='', encoding='utf-8') as out:
        w = csv.DictWriter(out, fieldnames=FIELDS)
        for r in csv.DictReader(f):
            key = (r['TICKER'], r['HOLDING_TICKER'], r['HOLDING_NAME'], r['WEIGHT_PCT'])
            if key in existing:
                continue
            existing.add(key)
            w.writerow({'etf_ticker': r['TICKER'], 'etf_name': NAMES.get(r['TICKER'], ''),
                        'holding_ticker': r['HOLDING_TICKER'], 'holding_name': r['HOLDING_NAME'],
                        'weight_pct': r['WEIGHT_PCT'], 'as_of_date': r['AS_OF_DATE'],
                        'source': SRC, 'provider': PROV})
            counts[r['TICKER']] = counts.get(r['TICKER'], 0) + 1
            n_new += 1
    print('Added Manulife rows:', n_new, counts)

if __name__ == '__main__':
    main()
