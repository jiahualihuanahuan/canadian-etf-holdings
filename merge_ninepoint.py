#!/usr/bin/env python3
"""Merge ninepoint_holdings_raw.csv into the 8-col master. Ninepoint publishes no
holdings downloads; data from ninepoint.com page tables/text. Blank weight_pct
where the site publishes no weights. Idempotent."""
import csv, os

BASE = os.path.dirname(os.path.abspath(__file__))
MASTER = os.path.join(BASE, 'canadian_etf_holdings_MASTER.csv')
RAW = os.path.join(BASE, 'ninepoint_holdings_raw.csv')
FIELDS = ['etf_ticker','etf_name','holding_ticker','holding_name','weight_pct','as_of_date','source','provider']

NAMES = {
    'ABHI': 'Ninepoint Barrick High Income Shares ETF',
    'BCHI': 'Ninepoint BCE HighShares ETF',
    'CCHI': 'Ninepoint Cameco HighShares ETF',
    'CLHI': 'Ninepoint Celestica HighShares ETF',
    'CQHI': 'Ninepoint Canadian Natural Resources HighShares ETF',
    'CRHI': 'Ninepoint CNR HighShares ETF',
    'CSHI': 'Ninepoint Constellation Software HighShares ETF',
    'CSUC': 'Ninepoint Constellation Software CoreShares ETF',
    'ECHI': 'Ninepoint Enhanced Canadian HighShares ETF',
    'ENHI': 'Ninepoint Enbridge HighShares ETF',
    'GBSL': 'Ninepoint Global Select Fund',
    'GBSL.U': 'Ninepoint Global Select Fund USD Series',
    'GBUL': 'Ninepoint Gold Bullion Fund',
    'GLDE': 'Ninepoint Gold & Precious Minerals Fund',
    'GOHI': 'Ninepoint Alphabet HighShares ETF',
    'INFR': 'Ninepoint Global Infrastructure Fund',
    'INHI': 'Ninepoint Intel HighShares ETF',
    'KGHI': 'Ninepoint Kinross Gold HighShares ETF',
    'NACO': 'Ninepoint Alternative Credit Opportunities Fund',
    'NBAL': 'Ninepoint Balanced+ Fund',
    'NBND': 'Ninepoint Diversified Bond Fund',
    'NMNG': 'Ninepoint Mining Evolution Fund',
    'NNRG': 'Ninepoint Energy Fund',
    'NNRG.U': 'Ninepoint Energy Fund USD Series',
    'NRGI': 'Ninepoint Energy Income Fund',
    'NSAV': 'Ninepoint Cash Management Fund',
    'NVHI': 'Ninepoint NVIDIA HighShares ETF',
    'PLHI': 'Ninepoint Palantir HighShares ETF',
    'RYHI': 'Ninepoint RY-Linked HighShares ETF',
    'SBUL': 'Ninepoint Silver Bullion Fund',
    'SHHI': 'Ninepoint Shopify HighShares ETF',
    'SUHI': 'Ninepoint Suncor HighShares ETF',
    'SXHI': 'Ninepoint SpaceX HighShares ETF',
    'TDHI': 'Ninepoint TD-Linked HighShares ETF',
    'TIF': 'Ninepoint Target Income Fund',
    'TKN': 'Ninepoint Crypto and AI Leaders ETF',
    'TKN.U': 'Ninepoint Crypto and AI Leaders ETF USD Series',
    'TSHI': 'Ninepoint Tesla HighShares ETF',
    'USHI': 'Ninepoint Enhanced U.S. Equity HighShares ETF',
}
DATE_MAP = {
    '2026-09-18': ['ABHI','BCHI','CCHI','CLHI','CQHI','CRHI','CSHI','CSUC','ENHI','KGHI','SHHI','SUHI','TDHI'],
    '2026-08-31': ['GBSL','GBSL.U','GBUL','GLDE','GOHI','INFR','INHI','NACO','NBAL','NBND','NMNG',
                   'NNRG','NNRG.U','NRGI','NSAV','NVHI','PLHI','SBUL','SXHI','TIF','TKN','TKN.U','TSHI'],
    '2026-07-31': ['ECHI'],
    '2025-07-31': ['RYHI'],
    '2026-09-14': ['USHI'],
}
TICKER_DATE = {t: d for d, ts in DATE_MAP.items() for t in ts}
SRC = 'browser:ninepoint.com_2026-09-19'
PROV = 'Ninepoint'

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
                        'weight_pct': r['WEIGHT_PCT'], 'as_of_date': TICKER_DATE.get(r['TICKER'], ''),
                        'source': SRC, 'provider': PROV})
            counts[r['TICKER']] = counts.get(r['TICKER'], 0) + 1
            n_new += 1
    print('Added Ninepoint rows:', n_new, counts)

if __name__ == '__main__':
    main()
