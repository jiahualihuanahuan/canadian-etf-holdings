#!/usr/bin/env python3
"""Merge dynamic_holdings_raw.csv into the 8-col master. Dynamic publishes no
holdings downloads and no holding tickers; data from dynamic.ca page top-10s.
Idempotent."""
import csv, os

BASE = os.path.dirname(os.path.abspath(__file__))
MASTER = os.path.join(BASE, 'canadian_etf_holdings_MASTER.csv')
RAW = os.path.join(BASE, 'dynamic_holdings_raw.csv')
FIELDS = ['etf_ticker','etf_name','holding_ticker','holding_name','weight_pct','as_of_date','source','provider']

NAMES = {
    'DXAU': 'Dynamic Active Global Gold ETF',
    'DXB': 'Dynamic Active Tactical Bond ETF',
    'DXBB': 'Dynamic Active Bond ETF',
    'DXBC': 'Dynamic Active Canadian Bond ETF',
    'DXBG': 'Dynamic Global Fixed Income Fund (ETF series)',
    'DXBU': 'Dynamic Active U.S. Investment Grade Corporate Bond ETF',
    'DXC': 'Dynamic Active Canadian Dividend ETF',
    'DXCB': 'Dynamic Active Corporate Bond ETF',
    'DXCO': 'Dynamic Credit Opportunities Fund (ETF series)',
    'DXCP': 'Dynamic Short Term Credit PLUS Fund (ETF series)',
    'DXDB': 'Dynamic Active Discount Bond ETF',
    'DXDU.U': 'Dynamic Active U.S. Discount Bond ETF',
    'DXEM': 'Dynamic Active Emerging Markets ETF',
    'DXF': 'Dynamic Active Global Financial Services ETF',
    'DXG': 'Dynamic Active Global Dividend ETF',
    'DXG.U': 'Dynamic Active Global Dividend ETF (USD units)',
    'DXGE': 'Dynamic Active Global Equity Income ETF',
    'DXID': 'Dynamic Active Innovation and Disruption ETF',
    'DXID.U': 'Dynamic Active Innovation and Disruption ETF (USD units)',
    'DXIF': 'Dynamic Active International ETF',
    'DXMC': 'Dynamic Active Multi-Crypto ETF',
    'DXMO': 'Dynamic Active Mining Opportunities ETF',
    'DXN': 'Dynamic Active Global Infrastructure ETF',
    'DXO': 'Dynamic Active Crossover Bond ETF',
    'DXP': 'Dynamic Active Preferred Shares ETF',
    'DXQ': 'Dynamic Active Enhanced Yield Covered Options ETF',
    'DXR': 'Dynamic Retirement Income Fund (ETF series)',
    'DXRE': 'Dynamic Active Real Estate ETF',
    'DXU': 'Dynamic Active U.S. Dividend ETF',
    'DXU.U': 'Dynamic Active U.S. Dividend ETF (USD units)',
    'DXUS': 'Dynamic Active U.S. Equity ETF',
    'DXUS.U': 'Dynamic Active U.S. Equity ETF (USD units)',
    'DXV': 'Dynamic Active Ultra Short Term Bond ETF',
    'DXW': 'Dynamic Active International Dividend ETF',
    'DXZ': 'Dynamic Active U.S. Mid-Cap ETF',
}
DATE_MAP = {
    '2026-07-31': ['DXB','DXBB','DXBC','DXBG','DXBU','DXC','DXCB','DXCP','DXDB','DXDU.U','DXEM','DXG','DXG.U','DXID.U','DXIF','DXMC','DXO','DXP','DXU','DXU.U','DXV','DXW'],
    '2026-02-28': ['DXAU','DXGE','DXID','DXMO','DXN','DXQ','DXRE','DXUS','DXUS.U'],
    '2026-06-30': ['DXF','DXZ'],
    '2025-10-31': ['DXCO','DXR'],
}
TICKER_DATE = {t: d for d, ts in DATE_MAP.items() for t in ts}
SRC = 'browser:dynamic.ca_2026-09-19'
PROV = 'Dynamic'

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
                        'holding_ticker': '', 'holding_name': r['HOLDING_NAME'],
                        'weight_pct': r['WEIGHT_PCT'], 'as_of_date': TICKER_DATE.get(r['TICKER'], ''),
                        'source': SRC, 'provider': PROV})
            counts[r['TICKER']] = counts.get(r['TICKER'], 0) + 1
            n_new += 1
    print('Added Dynamic rows:', n_new, counts)

if __name__ == '__main__':
    main()
