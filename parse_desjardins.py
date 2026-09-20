#!/usr/bin/env python3
"""Parse Desjardins complete-list CSVs (semicolon-delimited, French decimal commas,
header metadata lines) into desjardins_holdings_raw.csv with
TICKER,HOLDING_TICKER,HOLDING_NAME,WEIGHT_PCT,AS_OF_DATE.
Desjardins files carry no holding tickers -> HOLDING_TICKER left blank."""
import csv, glob, os, re, datetime

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, 'desjardins_holdings_raw.csv')

MONTHS = {m: i+1 for i, m in enumerate(['january','february','march','april','may','june',
        'july','august','september','october','november','december'])}

def parse_date(s):
    m = re.search(r'as at\s+([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})', s)
    if not m:
        return ''
    mon, day, year = m.group(1).lower(), int(m.group(2)), int(m.group(3))
    return '%04d-%02d-%02d' % (year, MONTHS.get(mon, 1), day)

def main():
    rows = []
    for path in sorted(glob.glob(os.path.expanduser('~/workspace/browser_downloads/sess-*/browser-download-*-desjardins_*.csv'))):
        with open(path, encoding='utf-8-sig') as f:
            lines = f.read().splitlines()
        if not lines:
            continue
        as_of = parse_date(lines[0])
        ticker = ''
        in_data = False
        n = 0
        for ln in lines:
            if ln.startswith('Ticker;'):
                ticker = ln.split(';', 1)[1].strip()
            elif ln.startswith('Name;Weighting %'):
                in_data = True
                continue
            elif in_data:
                if not ln.strip():
                    continue
                parts = ln.split(';')
                if len(parts) < 2:
                    continue
                name, wt = parts[0].strip(), parts[1].strip().replace(',', '.')
                try:
                    w = float(wt)
                except ValueError:
                    continue
                rows.append((ticker, '', name, '%.2f' % w, as_of))
                n += 1
        print(os.path.basename(path)[-60:], '->', ticker, as_of, n, 'rows')
    with open(OUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['TICKER', 'HOLDING_TICKER', 'HOLDING_NAME', 'WEIGHT_PCT', 'AS_OF_DATE'])
        w.writerows(rows)
    print('Wrote', OUT, len(rows), 'rows')

if __name__ == '__main__':
    main()
