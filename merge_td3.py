#!/usr/bin/env python3
"""Merge TD batch-3 (strict PDF re-extraction) into master.
Replaces rows for the 32 PDF-verified session tickers + 7 verified -U duplicates.
Removes the TD-BATCH2-QUARANTINE coverage note (superseded)."""
import csv, shutil, os

BASE = "/home/hatch/workspace/your_files/canadian-etf-holdings"
MASTER = os.path.join(BASE, "canadian_etf_holdings_MASTER.csv")
RAW_IN = os.path.join(BASE, "td_batch3_raw.csv")
NOTES = os.path.join(BASE, "coverage_notes.csv")
SCHEMA = ["etf_ticker","etf_name","holding_ticker","holding_name","weight_pct",
          "as_of_date","source","provider"]

NAMES = {
    "TCSB": "TD Select Short Term Corporate Bond Ladder ETF",
    "TCSH": "TD Cash Management ETF",
    "TDOC": "TD Global Healthcare Leaders Index ETF",
    "TEC": "TD Global Technology Leaders Index ETF",
    "TECI": "TD Global Technology Innovators Index ETF",
    "TECX": "TD Global Technology Leaders CAD Hedged Index ETF",
    "TEQT": "TD All-Equity ETF Portfolio",
    "TGED": "TD Active Global Enhanced Dividend ETF",
    "TGFI": "TD Active Global Income ETF",
    "TGGR": "TD Active Global Equity Growth ETF",
    "TGRE": "TD Active Global Real Estate Equity ETF",
    "TGRO": "TD Growth ETF Portfolio",
    "THE": "TD International Equity CAD Hedged Index ETF",
    "THU": "TD U.S. Equity CAD Hedged Index ETF",
    "TILV": "TD Q International Low Volatility ETF",
    "TINF": "TD Active Global Infrastructure Equity ETF",
    "TPE": "TD International Equity Index ETF",
    "TPRF": "TD Active Preferred Share ETF",
    "TPU": "TD U.S. Equity Index ETF",
    "TQCD": "TD Q Canadian Dividend ETF",
    "TQGD": "TD Q Global Dividend ETF",
    "TQGM": "TD Q Global Multifactor ETF",
    "TQSM": "TD Q U.S. Small-Mid-Cap Equity ETF",
    "TTP": "TD Canadian Equity Index ETF",
    "TUED": "TD Active U.S. Enhanced Dividend ETF",
    "TUEX": "TD Active U.S. Enhanced Dividend CAD Hedged ETF",
    "TUHY": "TD Active U.S. High Yield Bond ETF",
    "TULB": "TD U.S. Long Term Treasury Bond ETF",
    "TULV": "TD Q U.S. Low Volatility ETF",
    "TUSB": "TD Select U.S. Short Term Corporate Bond Ladder ETF",
    "TUSD-U": "TD U.S. Cash Management ETF - US$",
    "TDB": "TD Canadian Aggregate Bond Index ETF",
}
DUPLICATES = {
    "TDOC-U": ("TDOC", "TD Global Healthcare Leaders Index ETF - US$"),
    "TEC-U": ("TEC", "TD Global Technology Leaders Index ETF - US$"),
    "TGED-U": ("TGED", "TD Active Global Enhanced Dividend ETF - US$"),
    "TPU.U": ("TPU", "TD U.S. Equity Index ETF - US$"),
    "TQSM-U": ("TQSM", "TD Q U.S. Small-Mid-Cap Equity ETF - US$"),
    "TUED-U": ("TUED", "TD Active U.S. Enhanced Dividend ETF - US$"),
    "TUSB-U": ("TUSB", "TD Select U.S. Short Term Corporate Bond Ladder ETF - US$"),
}

def main():
    rows = []
    base_rows = {}
    with open(RAW_IN, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            t = r["etf_ticker"]
            assert t in NAMES, t
            rec = {"etf_ticker": t, "etf_name": NAMES[t], "holding_ticker": "",
                   "holding_name": r["holding_name"].strip(), "weight_pct": r["weight_pct"].strip(),
                   "as_of_date": "2026-03-31",
                   "source": "TD Asset Management Quarterly Portfolio Summary PDF (as at March 31, 2026; strict re-extraction)",
                   "provider": "TDAM"}
            rows.append(rec)
            base_rows.setdefault(t, []).append(rec)
    assert len(rows) == 687, len(rows)
    for du, (base, _) in DUPLICATES.items():
        assert base in base_rows, base
        for r in base_rows[base]:
            d = dict(r)
            d["etf_ticker"] = du
            d["etf_name"] = DUPLICATES[du][1]
            d["source"] = ("TD Asset Management Quarterly Portfolio Summary PDF (as at March 31, 2026) "
                           f"— verified identical to {base}; duplicated")
            rows.append(d)
    tickers = set(r["etf_ticker"] for r in rows)
    assert len(tickers) == 39, len(tickers)

    shutil.copy2(MASTER, MASTER + ".pre-td3.bak")
    kept = []
    with open(MASTER, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["etf_ticker"] not in tickers:
                kept.append(row)
    tmp = MASTER + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SCHEMA)
        w.writeheader(); w.writerows(kept); w.writerows(rows)
    os.replace(tmp, MASTER)

    notes = []
    with open(NOTES, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["etf_ticker"] != "TD-BATCH2-QUARANTINE":
                notes.append(row)
    existing = {row["etf_ticker"] for row in notes}
    for t in sorted(tickers):
        if t not in existing:
            notes.append({"etf_ticker": t,
                          "note": ("Partial: TD publishes only Top-25 quarterly portfolio summaries "
                                   "(as at March 31, 2026); complete holdings not published. No holding tickers published. "
                                   "Strict PDF-verified re-extraction 2026-09-19.")})
    with open(NOTES, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["etf_ticker", "note"])
        w.writeheader(); w.writerows(notes)
    print(f"merged {len(rows)} rows across {len(tickers)} tickers; master rows: {len(kept)+len(rows)}")

if __name__ == "__main__":
    main()
