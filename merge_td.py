#!/usr/bin/env python3
"""Merge td_holdings_raw.csv (TICKER,HOLDING_TICKER,HOLDING_NAME,WEIGHT_PCT,AS_OF_DATE)
into the 8-col master. TD pages show full holdings for bond/target funds and top-N
for others; no holding tickers shown. Idempotent."""
import csv, os

BASE = os.path.dirname(os.path.abspath(__file__))
MASTER = os.path.join(BASE, 'canadian_etf_holdings_MASTER.csv')
RAW = os.path.join(BASE, 'td_holdings_raw.csv')
FIELDS = ['etf_ticker','etf_name','holding_ticker','holding_name','weight_pct','as_of_date','source','provider']

NAMES = {
    'TBAL': 'TD Balanced ETF Portfolio',
    'TBCF': 'TD Target 2026 Investment Grade Bond ETF',
    'TBCG': 'TD Target 2027 Investment Grade Bond ETF',
    'TBCH': 'TD Target 2028 Investment Grade Bond ETF',
    'TBCI': 'TD Target 2029 Investment Grade Bond ETF',
    'TBCJ': 'TD Target 2030 Investment Grade Bond ETF',
    'TBNK': 'TD Canadian Bank Dividend Index ETF',
    'TBUF.U': 'TD Target 2026 U.S. Investment Grade Bond ETF',
    'TBUG.U': 'TD Target 2027 U.S. Investment Grade Bond ETF',
    'TCLB': 'TD Canadian Long Term Federal Bond ETF',
    'TCLV': 'TD Q Canadian Low Volatility ETF',
    'TCON': 'TD Conservative ETF Portfolio',
    'TDNA': 'TD North American Dividend Fund – ETF Series',
}
SRC = 'browser:td.com_2026-09-19'
PROV = 'TD'

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
    print('Added TD rows:', n_new, counts)

if __name__ == '__main__':
    main()
