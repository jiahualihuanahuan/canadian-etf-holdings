#!/usr/bin/env python3
"""Merge brompton_holdings_raw.csv (TICKER,HOLDING_TICKER,HOLDING_NAME,WEIGHT_PCT)
into the 8-col master. Brompton pages show Top-25 for most, full portfolio for
BFIN/BMAX/CLSA/KNGG/PAYG/PAYI/PAYU/SPLT; no holding tickers except internal
Brompton fund holdings. All as at 2026-08-31. Idempotent."""
import csv, os

BASE = os.path.dirname(os.path.abspath(__file__))
MASTER = os.path.join(BASE, 'canadian_etf_holdings_MASTER.csv')
RAW = os.path.join(BASE, 'brompton_holdings_raw.csv')
FIELDS = ['etf_ticker','etf_name','holding_ticker','holding_name','weight_pct','as_of_date','source','provider']

NAMES = {
    'BAAA': 'Brompton Wellington Square AAA CLO ETF',
    'BAAA.U': 'Brompton Wellington Square AAA CLO ETF',
    'BBBB': 'Brompton Wellington Square Investment Grade CLO ETF',
    'BBBB.U': 'Brompton Wellington Square Investment Grade CLO ETF',
    'BDIV': 'Brompton Global Dividend Growth ETF',
    'BEPR': 'Brompton Flaherty & Crumrine Enhanced Investment Grade Preferred ETF',
    'BEPR.U': 'Brompton Flaherty & Crumrine Enhanced Investment Grade Preferred ETF',
    'BFIN': 'Brompton North American Financials Dividend ETF',
    'BFIN.U': 'Brompton North American Financials Dividend ETF',
    'BGIE': 'Brompton Global Infrastructure ETF',
    'BLOV': 'Brompton North American Low Volatility Dividend ETF',
    'BMAX': 'Brompton Enhanced Multi-Asset Income ETF',
    'BPRF': 'Brompton Flaherty & Crumrine Investment Grade Preferred ETF',
    'BPRF.U': 'Brompton Flaherty & Crumrine Investment Grade Preferred ETF',
    'CLSA': 'Brompton Split Corp. Enhanced Equity Income ETF',
    'EDGF': 'Brompton European Dividend Growth ETF',
    'HIG': 'Brompton Global Healthcare Income & Growth ETF',
    'HIG.U': 'Brompton Global Healthcare Income & Growth ETF',
    'KNGC': 'Brompton Canadian Cash Flow Kings ETF',
    'KNGG': 'Brompton Global Cash Flow Kings ETF',
    'KNGU': 'Brompton U.S. Cash Flow Kings ETF',
    'KNGX': 'Brompton International Cash Flow Kings ETF',
    'PAYG': 'Brompton Global Equity HighPay ETF',
    'PAYI': 'Brompton Utilities & Infrastructure HighPay ETF',
    'PAYU': 'Brompton U.S. Equity HighPay ETF',
    'SPLT': 'Brompton Split Corp. Preferred Share ETF',
    'SPLT.U': 'Brompton Split Corp. Preferred Share ETF',
    'TLF': 'Brompton Tech Leaders Income ETF',
    'TLF.U': 'Brompton Tech Leaders Income ETF',
}
SRC = 'browser:bromptongroup.com_2026-09-19'
PROV = 'Brompton'
AS_OF = '2026-08-31'

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
                        'weight_pct': r['WEIGHT_PCT'], 'as_of_date': AS_OF,
                        'source': SRC, 'provider': PROV})
            counts[r['TICKER']] = counts.get(r['TICKER'], 0) + 1
            n_new += 1
    print('Added Brompton rows:', n_new, counts)

if __name__ == '__main__':
    main()
