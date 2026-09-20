#!/usr/bin/env python3
"""Merge desjardins_holdings_raw.csv into the 8-col master. Desjardins CSVs carry
no holding tickers. Idempotent."""
import csv, os

BASE = os.path.dirname(os.path.abspath(__file__))
MASTER = os.path.join(BASE, 'canadian_etf_holdings_MASTER.csv')
RAW = os.path.join(BASE, 'desjardins_holdings_raw.csv')
FIELDS = ['etf_ticker','etf_name','holding_ticker','holding_name','weight_pct','as_of_date','source','provider']

NAMES = {
    'DACL': 'Desjardins Canadian Equity Leaders ETF',
    'DACU': 'Desjardins Active Canadian Bond Universe ETF',
    'DAGL': 'Desjardins Global Opportunities ETF',
    'DAMG': 'Desjardins Absolute Return Global Equity Markets ETF - CA$ Hedged',
    'DAMG.U': 'Desjardins Absolute Return Global Equity Markets ETF - US$ Hedged',
    'DANC': 'Desjardins Market Neutral ETF',
    'DANC.U': 'Desjardins Market Neutral ETF - US$ Hedged',
    'DCBC': 'Desjardins Canadian Corporate Bond Index ETF',
    'DCC': 'Desjardins 1-5 Year Laddered Canadian Corporate Bond Index ETF',
    'DCG': 'Desjardins 1-5 Year Laddered Canadian Government Bond Index ETF',
    'DCP': 'Desjardins Canadian Preferred Share Index ETF',
    'DCS': 'Desjardins Canadian Short Term Bond Index ETF',
    'DCU': 'Desjardins Canadian Universe Bond Index ETF',
    'DGGB': 'Desjardins Global Government Bond Index ETF',
    'DGLM': 'Desjardins Global Macro ETF',
    'DMEC': 'Desjardins Canadian Equity Index ETF',
    'DMEE': 'Desjardins Emerging Markets Equity Index ETF',
    'DMEI': 'Desjardins International Equity Index ETF',
    'DMEU': 'Desjardins American Equity Index ETF',
    'DMID': 'Desjardins American Mid Cap Equity Index ETF',
    'DMQC': 'Desjardins Quebec Equity ETF',
    'DRCU': 'Desjardins RI Active Canadian Bond - Net-Zero Emissions Pathway ETF',
    'DRFC': 'Desjardins RI Canada Multifactor - Net-Zero Emissions Pathway ETF',
    'DRFD': 'Desjardins RI Developed ex-USA ex-Canada Multifactor - Net-Zero Emissions Pathway ETF',
    'DRFE': 'Desjardins RI Emerging Markets Multifactor - Net-Zero Emissions Pathway ETF',
    'DRFG': 'Desjardins RI Global Multifactor - Fossil Fuel Reserves Free ETF',
    'DRFU': 'Desjardins RI USA Multifactor - Net-Zero Emissions Pathway ETF',
    'DRMC': 'Desjardins RI Canada - Net-Zero Emissions Pathway ETF',
    'DRMD': 'Desjardins RI Developed ex-USA ex-Canada - Net-Zero Emissions Pathway ETF',
    'DRME': 'Desjardins RI Emerging Markets - Net-Zero Emissions Pathway ETF',
    'DRMU': 'Desjardins RI USA - Net-Zero Emissions Pathway ETF',
    'DUIG': 'Desjardins US Investment Grade Corporate Bond Index ETF',
}
SRC = 'file:desjardins_complete_list_csv_2026-09-19'
PROV = 'Desjardins'

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
                        'weight_pct': r['WEIGHT_PCT'], 'as_of_date': r['AS_OF_DATE'],
                        'source': SRC, 'provider': PROV})
            counts[r['TICKER']] = counts.get(r['TICKER'], 0) + 1
            n_new += 1
    print('Added Desjardins rows:', n_new, counts)

if __name__ == '__main__':
    main()
