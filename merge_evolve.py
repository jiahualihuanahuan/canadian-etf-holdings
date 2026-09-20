#!/usr/bin/env python3
"""Merge evolve_holdings_raw.csv (DIVS top-10, EARN, ETC) into the 8-col master. Idempotent."""
import csv, os

BASE = os.path.dirname(os.path.abspath(__file__))
MASTER = os.path.join(BASE, 'canadian_etf_holdings_MASTER.csv')
RAW = os.path.join(BASE, 'evolve_holdings_raw.csv')
FIELDS = ['etf_ticker','etf_name','holding_ticker','holding_name','weight_pct','as_of_date','source','provider']

NAMES = {
    'DIVS': 'Evolve Active Canadian Preferred Share Fund',
    'EARN': 'Evolve Active Global Fixed Income Fund',
    'ETC': 'Evolve Cryptocurrencies ETF',
}
SRC = 'browser:evolveetfs.com_2026-09-19'
PROV = 'Evolve ETFs'

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
    print('Added Evolve rows:', n_new, counts)

if __name__ == '__main__':
    main()
