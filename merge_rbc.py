#!/usr/bin/env python3
"""Merge RBC GAM holdings CSVs into master. Idempotent: replaces all rows for
the tickers it covers. -U USD classes duplicate verified-identical base holdings."""
import csv, glob, re, shutil, os
from datetime import datetime

BASE = "/home/hatch/workspace/your_files/canadian-etf-holdings"
DL = "/home/hatch/workspace/browser_downloads/sess-3597525341"
MASTER = os.path.join(BASE, "canadian_etf_holdings_MASTER.csv")
RAW = os.path.join(BASE, "rbc_holdings_raw.csv")
NOTES = os.path.join(BASE, "coverage_notes.csv")
SCHEMA = ["etf_ticker","etf_name","holding_ticker","holding_name","weight_pct",
          "as_of_date","source","provider"]

# download-file suffix -> (ticker, fund name)
FILE_TICKER = {
    "226": ("RBO",  "RBC 1-5 Year Laddered Canadian Corporate Bond ETF"),
    "228": ("RCD",  "RBC Quant Canadian Dividend Leaders ETF"),
    "230": ("RCDC", "RBC Canadian Dividend Covered Call ETF"),
    "233": ("RDBH", "RBC U.S. Discount Bond (CAD Hedged) ETF"),
    "237": ("RGQP", "RBC Target 2027 Canadian Government Bond ETF"),
    "239": ("RGQQ", "RBC Target 2028 Canadian Government Bond ETF"),
    "240": ("RGQR", "RBC Target 2029 Canadian Government Bond ETF"),
    "243": ("RGQS", "RBC Target 2030 Canadian Government Bond ETF"),
    "244": ("RID",  "RBC Quant EAFE Dividend Leaders ETF"),
    "246": ("RIDH", "RBC Quant EAFE Dividend Leaders (CAD Hedged) ETF"),
    "248": ("RLB",  "RBC 1-5 Year Laddered Canadian Bond ETF"),
    "250": ("RPD",  "RBC Quant European Dividend Leaders ETF"),
    "253": ("RPDH", "RBC Quant European Dividend Leaders (CAD Hedged) ETF"),
    "255": ("RPF",  "RBC Canadian Preferred Share ETF"),
    "258": ("RQP",  "RBC Target 2027 Canadian Corporate Bond Index ETF"),
    "259": ("RQQ",  "RBC Target 2028 Canadian Corporate Bond Index ETF"),
    "261": ("RQR",  "RBC Target 2029 Canadian Corporate Bond Index ETF"),
    "263": ("RQS",  "RBC Target 2030 Canadian Corporate Bond Index ETF"),
    "268": ("RUD",  "RBC Quant U.S. Dividend Leaders ETF"),
    "276": ("RUDH", "RBC Quant U.S. Dividend Leaders (CAD Hedged) ETF"),
    "271": ("RUDB", "RBC U.S. Discount Bond ETF"),
    "273": ("RUDC", "RBC U.S. Dividend Covered Call ETF"),
    "280": ("RUQP", "RBC Target 2027 U.S. Corporate Bond ETF"),
    "283": ("RUQQ", "RBC Target 2028 U.S. Corporate Bond ETF"),
    "285": ("RUQR", "RBC Target 2029 U.S. Corporate Bond ETF"),
    "287": ("RUQS", "RBC Target 2030 U.S. Corporate Bond ETF"),
    "289": ("RUSB", "RBC Short Term U.S. Corporate Bond ETF"),
}
DUPE_U = {"RID": "RID-U", "RPD": "RPD-U", "RUD": "RUD-U", "RUDB": "RUDB-U",
          "RUDC": "RUDC-U", "RUQP": "RUQP-U", "RUQQ": "RUQQ-U", "RUQR": "RUQR-U",
          "RUQS": "RUQS-U", "RUSB": "RUSB-U"}
U_NAME = {
    "RID-U": "RBC Quant EAFE Dividend Leaders ETF (USD Units)",
    "RPD-U": "RBC Quant European Dividend Leaders ETF (USD Units)",
    "RUD-U": "RBC Quant U.S. Dividend Leaders ETF (USD Units)",
    "RUDB-U": "RBC U.S. Discount Bond ETF (USD Units)",
    "RUDC-U": "RBC U.S. Dividend Covered Call ETF (USD Units)",
    "RUQP-U": "RBC Target 2027 U.S. Corporate Bond ETF (USD Units)",
    "RUQQ-U": "RBC Target 2028 U.S. Corporate Bond ETF (USD Units)",
    "RUQR-U": "RBC Target 2029 U.S. Corporate Bond ETF (USD Units)",
    "RUQS-U": "RBC Target 2030 U.S. Corporate Bond ETF (USD Units)",
    "RUSB-U": "RBC Short Term U.S. Corporate Bond ETF (USD Units)",
}
TERMINATED = {
    "RGQN": "RBC Target 2025 Government Bond ETF — terminated/matured; detail page empty, no holdings published.",
    "RGQO": "RBC Target 2026 Government Bond ETF — terminated/matured; detail page empty, no holdings published.",
    "RPSB": "terminated legacy fund; detail page empty/error, no product in site search; no holdings published.",
    "RQN": "terminated legacy fund; no product in site search; no holdings published.",
    "RQO": "terminated legacy fund; no product in site search; no holdings published.",
    "RUBH": "terminated legacy fund; no product in site search; no holdings published.",
    "RUBY": "terminated legacy fund; detail page empty; no holdings published.",
    "RUBY-U": "terminated legacy fund (USD variant of RUBY); no holdings published.",
    "RXD": "terminated legacy fund; detail page empty; no holdings published.",
    "RXD-U": "terminated legacy fund (USD variant of RXD); no holdings published.",
    "RUQN": "terminated (404); no holdings published.",
    "RUQN-U": "terminated (USD variant of RUQN); no holdings published.",
    "RUQO": "terminated (404); no holdings published.",
    "RUQO-U": "terminated (USD variant of RUQO); no holdings published.",
}

def clean_weight(s):
    s = s.replace("%", "").replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None

def parse_rbc(path):
    rows = [r for r in csv.reader(open(path, encoding="utf-8-sig")) if any(c.strip() for c in r)]
    as_of = ""
    hdr = -1
    for i, r in enumerate(rows[:20]):
        low = [c.strip().lower() for c in r]
        m = re.search(r"as of\s+([\d/]+)", " ".join(low))
        if m:
            d = datetime.strptime(m.group(1), "%m/%d/%Y").date()
            as_of = d.isoformat()
        if low[0] in ("holding", "holdings") and any("value" in c or "%" in c for c in low):
            hdr = i
            break
    out = []
    for r in rows[hdr + 1:]:
        cells = [c.strip() for c in r]
        if len(cells) < 2:
            continue
        name, w = cells[0], clean_weight(cells[1])
        if not name or w is None:
            continue
        if re.search(r"\btotal\b", name.lower()):
            continue
        out.append({"holding_name": name, "weight_pct": w})
    return as_of, out

def main():
    tickers_done = set()
    raw_rows = []
    warnings = []
    files = {re.search(r"Z-(\d+)-", f).group(1): f
             for f in glob.glob(os.path.join(DL, "*holdings_9_18_2026.csv"))}
    for suf, (ticker, name) in sorted(FILE_TICKER.items(), key=lambda x: x[1][0]):
        path = files.get(suf)
        if not path:
            warnings.append(f"{ticker}: download file missing")
            continue
        as_of, holdings = parse_rbc(path)
        total = sum(h["weight_pct"] for h in holdings)
        if total < 95:
            warnings.append(f"{ticker}: weight total {total:.2f}% below 95%")
        for h in holdings:
            raw_rows.append({"etf_ticker": ticker, "etf_name": name,
                             "holding_ticker": "", "holding_name": h["holding_name"],
                             "weight_pct": h["weight_pct"], "as_of_date": as_of,
                             "source": "RBC GAM holdings CSV (rbcgam.com)",
                             "provider": "RBC GAM"})
        # -U duplicate (verified identical via Currency options on rbcgam.com)
        if ticker in DUPE_U:
            u = DUPE_U[ticker]
            for h in holdings:
                raw_rows.append({"etf_ticker": u, "etf_name": U_NAME[u],
                                 "holding_ticker": "", "holding_name": h["holding_name"],
                                 "weight_pct": h["weight_pct"], "as_of_date": as_of,
                                 "source": "RBC GAM holdings CSV (rbcgam.com) — USD class, verified identical to base via Currency options",
                                 "provider": "RBC GAM"})
        tickers_done.add(ticker)
        tickers_done.add(DUPE_U[ticker]) if ticker in DUPE_U else None

    with open(RAW, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SCHEMA)
        w.writeheader()
        w.writerows(raw_rows)

    # idempotent merge: back up, drop covered tickers, append
    shutil.copy2(MASTER, MASTER + ".pre-rbc.bak")
    kept = []
    with open(MASTER, encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            if row["etf_ticker"] not in tickers_done:
                kept.append(row)
    tmp = MASTER + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SCHEMA)
        w.writeheader()
        w.writerows(kept)
        w.writerows(raw_rows)
    os.replace(tmp, MASTER)

    # coverage notes
    existing = set()
    with open(NOTES, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            existing.add(row["etf_ticker"])
    new_notes = []
    for t in sorted(tickers_done):
        if t not in existing:
            if t.endswith("-U"):
                base = t[:-2]
                new_notes.append((t, f"Complete holdings (duplicated from verified-identical {base}); RBC GAM publishes names and weights, no holding tickers; as of 2026-09-18."))
            else:
                new_notes.append((t, "Complete holdings from RBC GAM CSV download; names and weights only, no holding tickers; as of 2026-09-18."))
    for t, note in TERMINATED.items():
        if t not in existing:
            new_notes.append((t, note))
    with open(NOTES, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for t, note in new_notes:
            w.writerow([t, note])

    print(f"raw rows: {len(raw_rows)}, tickers with rows: {len(tickers_done)}, "
          f"terminated: {len(TERMINATED)}, master rows now: {len(kept)+len(raw_rows)}")
    for w_ in warnings:
        print("WARN:", w_)

if __name__ == "__main__":
    main()
