#!/usr/bin/env python3
"""Merge longpoint_holdings_raw.csv (TICKER,HOLDING_TICKER,HOLDING_NAME,WEIGHT_PCT)
into the 8-col master. LongPoint publishes no downloads; data from page tables.
As-of dates vary per ticker (DATE_MAP). HBDV/HBOP/HBTA top-10 tables publish no
weights. Idempotent."""
import csv, os

BASE = os.path.dirname(os.path.abspath(__file__))
MASTER = os.path.join(BASE, 'canadian_etf_holdings_MASTER.csv')
RAW = os.path.join(BASE, 'longpoint_holdings_raw.csv')
FIELDS = ['etf_ticker','etf_name','holding_ticker','holding_name','weight_pct','as_of_date','source','provider']

NAMES = {
    'AAPU': 'SavvyLong (2X) AAPL ETF', 'ABXU': 'SavvyLong (2X) Barrick ETF',
    'ALPU': 'SavvyLong (2X) GOOGL ETF', 'AMZU': 'SavvyLong (2X) AMZN ETF',
    'BNKU': 'MegaLong (3X) Canadian Banks Daily Leveraged Alternative ETF',
    'CCOU': 'SavvyLong (2X) Cameco ETF',
    'CGMD': 'MegaShort (-3X) Canadian Gold Miners Daily Leveraged Alternative ETF',
    'CGMU': 'MegaLong (3X) Canadian Gold Miners Daily Leveraged Alternative ETF',
    'CNQU': 'SavvyLong (2X) Cdn Natural Resources ETF',
    'COID': 'SavvyShort (-2X) COIN ETF', 'COIU': 'SavvyLong (2X) COIN ETF',
    'COMU': 'SavvyLong 2X CIBC (CM) Equity-Linked ETF',
    'CSUU': 'SavvyLong (2X) Constellation Software ETF',
    'FORU': 'ForAll Core & More U.S. Equity Index ETF',
    'GASD': 'SavvyShort Geared Natural Gas ETF', 'GASU': 'SavvyLong Geared Natural Gas ETF',
    'HBDV': 'Humilis North American Dividend Growth ETF',
    'HBOP': 'Humilis Fundamental Opportunities ETF',
    'HBTA': 'Humilis North American Tactical Equity Fund',
    'MOAT': 'Moat Active Premium Yield ETF',
    'MSFU': 'SavvyLong (2X) MSFT ETF', 'MSTU': 'SavvyLong (2X) MSTR ETF',
    'MSTZ': 'SavvyShort (-2X) MSTR ETF', 'NBCU': 'SavvyLong 2X NBC (NA) Equity-Linked ETF',
    'NVDD': 'SavvyShort (-2X) NVDA ETF', 'NVDU': 'SavvyLong (2X) NVDA ETF',
    'OILD': 'SavvyShort Geared Crude Oil ETF', 'OILU': 'SavvyLong Geared Crude Oil ETF',
    'QQQD': 'MegaShort (-3X) NASDAQ-100 Daily Leveraged Alternative ETF',
    'QQQU': 'MegaLong (3X) NASDAQ-100 Daily Leveraged Alternative ETF',
    'RBCU': 'SavvyLong 2X RBC (RY) Equity-Linked ETF',
    'RGBM': 'Return Stacked Global Balanced & Macro ETF',
    'RGBM.U': 'Return Stacked Global Balanced & Macro ETF USD Shares',
    'SHPD': 'SavvyShort (-2X) Shopify ETF', 'SHPU': 'SavvyLong (2X) Shopify ETF',
    'SOXD': 'MegaShort (-3X) US Semiconductors Daily Leveraged Alternative ETF',
    'SOXU': 'MegaLong (3X) US Semiconductors Daily Leveraged Alternative ETF',
    'SPYD': 'MegaShort (-3X) S&P 500 Daily Leveraged Alternative ETF',
    'SPYU': 'MegaLong (3X) S&P 500 Daily Leveraged Alternative ETF',
    'TCCA': 'Trading Central Quant Canada 50 Equity Index ETF',
    'TCEU': 'Trading Central Quant Europe 50 Equity Index ETF',
    'TCUS': 'Trading Central Quant U.S. 50 Equity Index ETF',
    'TCWW': 'Trading Central Quant Global 50 Equity Index ETF',
    'TDU': 'SavvyLong 2X TDB (TD) Equity-Linked ETF',
    'TSLD': 'SavvyShort (-2X) TSLA ETF', 'TSLU': 'SavvyLong (2X) TSLA ETF',
}
DATE_MAP = {
    '2026-09-16': ['AAPU','ABXU','ALPU','AMZU','CCOU','CNQU','COID','COIU','COMU','CSUU',
                   'MSFU','MSTU','MSTZ','NBCU','NVDD','NVDU','RBCU','RGBM','RGBM.U',
                   'SHPD','SHPU','TDU','TSLD','TSLU'],
    '2026-09-03': ['BNKU'],
    '2026-06-30': ['CGMD','CGMU','SOXD','SOXU'],
    '2026-09-08': ['FORU','MOAT'],
    '2026-08-27': ['GASD','GASU'],
    '2026-07-31': ['HBDV','HBOP','HBTA'],
    '2026-09-04': ['OILD','OILU'],
    '2026-08-31': ['QQQD','QQQU','SPYD','SPYU'],
    '2026-08-21': ['TCCA','TCEU','TCUS','TCWW'],
}
TICKER_DATE = {t: d for d, ts in DATE_MAP.items() for t in ts}
SRC = 'browser:longpointetfs.com_2026-09-19'
PROV = 'LongPoint'

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
    print('Added LongPoint rows:', n_new, counts)

if __name__ == '__main__':
    main()
