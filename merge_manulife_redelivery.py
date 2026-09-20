#!/usr/bin/env python3
"""Merge Manulife full redelivery (2026-09-19) into master.
Purely additive except coverage notes: none of these tickers exist in master yet.
BYLD.B is a verified duplicate of BYLD (row-by-row identical per browser check).
MCOR is top-10 preview only (mutual-fund-class page); row 9 weight left blank (page cell blank)."""
import csv, shutil, os

BASE = "/home/hatch/workspace/your_files/canadian-etf-holdings"
MASTER = os.path.join(BASE, "canadian_etf_holdings_MASTER.csv")
RAW_IN = os.path.join(BASE, "manulife_redelivery_raw.csv")
NOTES = os.path.join(BASE, "coverage_notes.csv")
SCHEMA = ["etf_ticker","etf_name","holding_ticker","holding_name","weight_pct",
          "as_of_date","source","provider"]

NAMES = {
    "MCAP": "Manulife Conservative ETF Portfolio",
    "MCLC": "Manulife Multifactor Canadian Large Cap Index ETF",
    "MCOR": "Manulife Core Plus Bond Fund – ETF Series (MCOR)",
    "BYLD": "Manulife Smart Enhanced Yield Bond ETF (Hedged Units)",
    "BYLD.B": "Manulife Smart Enhanced Yield Bond ETF – Unhedged Units",
    "CBND": "Manulife Smart Corporate Bond ETF",
    "CDEF": "Manulife Smart Defensive Equity ETF",
    "CDIV": "Manulife Smart Dividend ETF",
    "CYLD": "Manulife Smart Enhanced Yield ETF",
    "GBND": "Manulife Smart Global Bond ETF",
    "GDIV": "Manulife Smart Global Dividend ETF Portfolio",
    "GEDG": "Manulife Global Edge ETF",
    "MBAP": "Manulife Balanced ETF Portfolio",
    "IDEF.B": "Manulife Smart International Defensive Equity ETF – Unhedged Units",
    "IDIV.B": "Manulife Smart International Dividend ETF – Unhedged Units",
}

def main():
    rows = []
    byld_rows = []
    with open(RAW_IN, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            t = r["etf_ticker"]
            assert t in NAMES, t
            rec = {"etf_ticker": t, "etf_name": NAMES[t], "holding_ticker": "",
                   "holding_name": r["holding_name"].strip(), "weight_pct": r["weight_pct"].strip(),
                   "as_of_date": "2026-08-31",
                   "source": ("Manulife IM fund page holdings table (holdings as of 31/08/2026; "
                              "transcribed from verified page text; no CSV download offered)"),
                   "provider": "Manulife"}
            rows.append(rec)
            if t == "BYLD":
                byld_rows.append(rec)
    assert len(rows) == 1113, len(rows)
    for r in byld_rows:
        d = dict(r)
        d["etf_ticker"] = "BYLD.B"
        d["etf_name"] = NAMES["BYLD.B"]
        d["source"] += " — full holdings opened and compared row-by-row to BYLD; identical; duplicated"
        rows.append(d)
    tickers = set(r["etf_ticker"] for r in rows)
    assert len(tickers) == 15, len(tickers)

    shutil.copy2(MASTER, MASTER + ".pre-manulife-redelivery.bak")
    with open(MASTER, encoding="utf-8") as f:
        kept = [row for row in csv.DictReader(f) if row["etf_ticker"] not in tickers]
    tmp = MASTER + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SCHEMA)
        w.writeheader(); w.writerows(kept); w.writerows(rows)
    os.replace(tmp, MASTER)

    notes = list(csv.DictReader(open(NOTES, encoding="utf-8")))
    existing = {row["etf_ticker"] for row in notes}
    for t in sorted(tickers):
        if t not in existing:
            notes.append({"etf_ticker": t, "note": (
                "Top-10 preview only: MCOR lives on a mutual-fund-class page with no View Full Holdings link "
                "and no holdings download (Positions 368). One row (HM Treasury 4.38% 7/31/2054) had a blank "
                "weight cell on the page; weight left blank, not imputed." if t == "MCOR" else (
                "Complete holdings (as of 31/08/2026) via verified page transcription; issuer offers no "
                "holdings CSV download and publishes no holding tickers. "
                "BYLD.B verified identical to BYLD row-by-row; duplicated." if t in ("BYLD", "BYLD.B") else
                "Complete holdings (as of 31/08/2026) via verified page transcription; issuer offers no "
                "holdings CSV download and publishes no holding tickers."))})
    if "MCAN" not in existing:
        notes.append({"etf_ticker": "MCAN",
                      "note": ("Top-10 preview only: MCAN lives on a mutual-fund-class page with no View Full Holdings "
                               "link and no holdings download. No full holdings captured.")})
    with open(NOTES, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["etf_ticker", "note"])
        w.writeheader(); w.writerows(notes)
    print(f"merged {len(rows)} rows across {len(tickers)} tickers; master rows: {len(kept)+len(rows)}")

if __name__ == "__main__":
    main()
