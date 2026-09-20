#!/usr/bin/env python3
"""Merge nbi_holdings_raw.csv (TICKER,HOLDING_TICKER,HOLDING_NAME,WEIGHT_PCT,AS_OF_DATE)
into the 8-col master. NBI pages publish TOP-10 holdings only, no holding tickers.
Idempotent."""
import csv, os

BASE = os.path.dirname(os.path.abspath(__file__))
MASTER = os.path.join(BASE, 'canadian_etf_holdings_MASTER.csv')
RAW = os.path.join(BASE, 'nbi_holdings_raw.csv')
FIELDS = ['etf_ticker','etf_name','holding_ticker','holding_name','weight_pct','as_of_date','source','provider']

NAMES = {
    'NBUE': 'NBI U.S. Equity Fund - ETF Series',
    'NBUE.F': 'NBI U.S. Equity Fund - ETFH Series',
    'NBUX': 'NBI U.S. Equity Index Fund - ETF Series',
    'NCNS': 'NBI Conservative ETF Portfolio',
    'NCPB': 'NBI Canadian Core Plus Bond Fund - ETF Series',
    'NDIV': 'NBI Canadian Dividend Income ETF',
    'NEQT': 'NBI Equity ETF Portfolio',
    'NGPE': 'NBI Global Private Equity ETF',
    'NGRW': 'NBI Growth ETF Portfolio',
    'NHYB': 'NBI High Yield Bond ETF',
    'NINT': 'NBI Active International Equity ETF',
    'NINV': 'NBI Innovators Fund - ETF Series',
    'NINV.F': 'NBI Innovators Fund - ETFH Series',
    'NMBL': 'Meritage Tactical ETF Balanced Portfolio - ETF Series',
    'NMEQ': 'Meritage Tactical ETF Equity Portfolio - ETF Series',
    'NMGR': 'Meritage Tactical ETF Growth Portfolio - ETF Series',
    'NMMO': 'Meritage Tactical ETF Moderate Portfolio - ETF Series',
    'NPRF': 'NBI Active Canadian Preferred Shares ETF',
    'NBSC.F': 'NBI Global Small Cap Fund - ETFH Series',
}
SRC = 'browser:nbinvestments.ca_2026-09-19'
PROV = 'NBI'

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
    print('Added NBI rows:', n_new, counts)

if __name__ == '__main__':
    main()
