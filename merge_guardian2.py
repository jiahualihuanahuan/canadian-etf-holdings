#!/usr/bin/env python3
"""Merge Guardian batch-2 (18 tickers: top-25 summaries + 4 verified .F duplicates).
Idempotent: replaces rows for covered tickers. Also fixes 6 mislabeled 'effectively
complete' notes from batch 1 -> Top-25 partial."""
import csv, shutil, os

BASE = "/home/hatch/workspace/your_files/canadian-etf-holdings"
MASTER = os.path.join(BASE, "canadian_etf_holdings_MASTER.csv")
RAW_IN = os.path.join(BASE, "guardian_new2_raw.csv")
NOTES = os.path.join(BASE, "coverage_notes.csv")
SCHEMA = ["etf_ticker","etf_name","holding_ticker","holding_name","weight_pct",
          "as_of_date","source","provider"]

NAMES = {
    "GGEP": "Guardian Directed Equity Path Portfolio",
    "GGPY": "Guardian Directed Premium Yield Portfolio",
    "GIDY": "Guardian i3 Global Dividend Premium Yield Fund",
    "GIES": "Guardian International Equity Select Fund",
    "GIGC": "Guardian Investment Grade Corporate Bond Fund",
    "GIGD": "Guardian i3 Global Dividend Growth Fund",
    "GIGF": "Guardian i3 Global Core Equity ETF",
    "GIIF": "Guardian i3 International Core Equity Fund",
    "GIUS": "Guardian i3 U.S. Core Equity Fund",
    "GSDB": "Guardian Short Duration Bond Fund",
    "GSIF": "Guardian Strategic Income Fund",
    "GUTB.U": "Guardian Ultra-Short U.S. T-Bill Fund (USD units)",
    "GGEP.F": "Guardian Directed Equity Path Portfolio (Hedged series)",
    "GGPY.F": "Guardian Directed Premium Yield Portfolio (Hedged series)",
    "GIGF.F": "Guardian i3 Global Core Equity ETF (Hedged series)",
    "GIUS.F": "Guardian i3 U.S. Core Equity Fund (Hedged series)",
}
DUP = {"GGEP.F": "GGEP", "GGPY.F": "GGPY", "GIGF.F": "GIGF", "GIUS.F": "GIUS"}
SRC = ("Guardian Capital Document Library - quarterly Summary of Investment "
       "Portfolio (top-25 disclosure; issuer does not publish a complete holdings list or CSV)")
PARTIAL_TXT = ("Partial: Top 25 holdings only (issuer's Summary of Investment Portfolio; no complete "
               "list or download published); as of 2026-03-31. No holding tickers published. "
               "Retail fund pages bot-blocked.")

def main():
    rows = []
    base_rows = []
    with open(RAW_IN, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            base_rows.append((r["etf_ticker"], r["holding_ticker"].strip(),
                              r["holding_name"].strip(), float(r["weight_pct"])))
    for t, ht, hn, w in base_rows:
        rows.append((t, ht, hn, w))
    for dup_t, base_t in DUP.items():  # verified same pool
        for t, ht, hn, w in base_rows:
            if t == base_t:
                rows.append((dup_t, ht, hn, w))
    tickers = sorted(set(r[0] for r in rows))
    assert tickers == sorted(NAMES), tickers
    assert len(rows) == 377, len(rows)

    shutil.copy2(MASTER, MASTER + ".pre-guard2.bak")
    kept = []
    with open(MASTER, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["etf_ticker"] not in NAMES:
                kept.append(row)
    tmp = MASTER + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SCHEMA)
        w.writeheader()
        w.writerows(kept)
        for t, ht, hn, wp in rows:
            w.writerow({"etf_ticker": t, "etf_name": NAMES[t], "holding_ticker": ht,
                        "holding_name": hn, "weight_pct": wp,
                        "as_of_date": "2026-03-31", "source": SRC, "provider": "Guardian"})

    os.replace(tmp, MASTER)

    # fix batch-1 notes mislabeled "effectively complete"
    fixed = 0
    with open(NOTES, encoding="utf-8") as f:
        note_rows = list(csv.DictReader(f))
    for r in note_rows:
        if r["etf_ticker"] in {"GBFC","GBFD","GBFE","GBFF","GBLF","GCTB"}:
            r["note"] = PARTIAL_TXT
            fixed += 1
    with open(NOTES, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["etf_ticker","note"])
        w.writeheader(); w.writerows(note_rows)

    existing = {r["etf_ticker"] for r in note_rows}
    new_notes = {
        "GIAI": "NO_HOLDINGS: Guardian i3 AI Technology and Innovation Fund, incepted 2026-06-30; issuer Fund Facts states info not available because the fund is new.",
        "GICD": "NO_HOLDINGS: Guardian i3 Canadian Dividend Growth Fund, incepted 2026-05-14; no portfolio summary or interim report published yet.",
        "GUTB.U": "Complete published portfolio: single position (U.S. Treasury Bills, 100.2% of NAV); as of 2026-03-31. No holding ticker published.",
    }
    with open(NOTES, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for t in tickers:
            if t in existing:
                continue
            w.writerow([t, new_notes.get(t, PARTIAL_TXT +
                        f" Verified same fund pool as {DUP[t]}; rows duplicated from base class." if t in DUP else PARTIAL_TXT)])
    print(f"merged {len(rows)} rows across {len(tickers)} tickers; fixed {fixed} batch-1 notes; master rows: {len(kept)+len(rows)}")

if __name__ == "__main__":
    main()
