#!/usr/bin/env python3
"""Merge Scotia RI / Starlight / Lysander transcribed rows (TOP_N_ONLY).
Idempotent: replaces rows for covered tickers. Adds coverage notes."""
import csv, shutil, os

BASE = "/home/hatch/workspace/your_files/canadian-etf-holdings"
MASTER = os.path.join(BASE, "canadian_etf_holdings_MASTER.csv")
RAW_IN = os.path.join(BASE, "scotiastarlight_lysander_raw.csv")
NOTES = os.path.join(BASE, "coverage_notes.csv")
SCHEMA = ["etf_ticker","etf_name","holding_ticker","holding_name","weight_pct",
          "as_of_date","source","provider"]

NAMES = {
    "SRIB": ("Scotia Responsible Investing Canadian Bond Index ETF", "Scotia"),
    "SRIC": ("Scotia Responsible Investing Canadian Equity Index ETF", "Scotia"),
    "SRII": ("Scotia Responsible Investing International Equity Index ETF", "Scotia"),
    "SRIU": ("Scotia Responsible Investing U.S. Equity Index ETF", "Scotia"),
    "SCDG": ("Starlight Dividend Growth Class", "Starlight"),
    "SCDGC": ("Starlight Dividend Growth Class", "Starlight"),
    "SCGG": ("Starlight Global Growth Fund", "Starlight"),
    "SCGI": ("Starlight Global Infrastructure Fund", "Starlight"),
    "SCGR": ("Starlight Global Real Estate Fund", "Starlight"),
    "SCNA": ("Starlight North American Equity Fund", "Starlight"),
    "SCNAE": ("Starlight North American Equity Fund", "Starlight"),
    "LYCT": ("Lysander-Canso Corporate Treasury ActivETF", "Lysander"),
    "LYFR": ("Lysander-Canso Floating Rate ActivETF", "Lysander"),
    "PR": ("Lysander-Slater Preferred Share ActivETF", "Lysander"),
}
SRC = {
    "Scotia": "Scotia Funds ETF profile page (top-10 only; index trackers have CSV downloads but RI series does not)",
    "Starlight": "Starlight Capital fund page (top-10 only; Series F mutual-fund view of same underlying fund as ETF ticker)",
    "Lysander": "Lysander Funds fund page (top-10 only; no holding tickers published)",
}

def main():
    rows = []
    with open(RAW_IN, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            t = r["etf_ticker"]
            assert t in NAMES, t
            rows.append({"etf_ticker": t, "etf_name": NAMES[t][0],
                         "holding_ticker": r["holding_ticker"].strip(),
                         "holding_name": r["holding_name"].strip(),
                         "weight_pct": r["weight_pct"].strip(),
                         "as_of_date": "2026-08-31",
                         "source": SRC[NAMES[t][1]], "provider": NAMES[t][1]})
    tickers = sorted(set(r["etf_ticker"] for r in rows))
    assert tickers == sorted(NAMES), tickers
    assert len(rows) == 136, len(rows)

    shutil.copy2(MASTER, MASTER + ".pre-scotia.bak")
    kept = []
    with open(MASTER, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["etf_ticker"] not in NAMES:
                kept.append(row)
    tmp = MASTER + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SCHEMA)
        w.writeheader(); w.writerows(kept); w.writerows(rows)
    os.replace(tmp, MASTER)

    existing = set()
    with open(NOTES, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            existing.add(row["etf_ticker"])
    notes = {
        "SRIB": "Partial: Top 10 holdings only (Scotia publishes no CSV/download for RI series; index trackers SITB/SITC/SITI/SITU have full CSVs); as of 2026-08-31. No holding tickers published.",
        "SRIC": "Partial: Top 10 holdings only (Scotia publishes no CSV/download for RI series); as of 2026-08-31. No holding tickers published.",
        "SRII": "Partial: Top 10 holdings only (Scotia publishes no CSV/download for RI series); as of 2026-08-31. No holding tickers published.",
        "SRIU": "Partial: Top 10 holdings only (Scotia publishes no CSV/download for RI series); as of 2026-08-31. No holding tickers published.",
        "SITE": "NO_HOLDINGS_TABLE: Scotia Emerging Markets Equity Index Tracker ETF publishes no holdings section or download (only sector allocation); as of 2026-08-31.",
        "SCDG": "Partial: Top 10 only; as of 2026-08-31. Weight not displayed on page for one holding (blank weight, not zero). SCDGC is same fund pool.",
        "SCDGC": "Partial: Top 10 only; as of 2026-08-31. Same fund pool as SCDG; rows duplicated.",
        "SCGG": "Partial: Top 10 only; as of 2026-08-31. 3 holding weights not displayed on page (blank, not zero).",
        "SCGI": "Partial: Top 10 only; as of 2026-08-31. 3 holding weights not displayed on page (blank, not zero).",
        "SCGR": "Partial: Top 10 only; as of 2026-08-31. 3 holding weights not displayed on page (blank, not zero).",
        "SCNA": "Partial: Top 10 only; as of 2026-08-31. 5 holding weights not displayed on page (blank, not zero). SCNAE is same fund pool.",
        "SCNAE": "Partial: Top 10 only; as of 2026-08-31. Same fund pool as SCNA; rows duplicated.",
        "LYCT": "Partial: Top 10 only; as of 2026-08-31. No holding tickers published.",
        "LYFR": "Partial: Top 10 only; as of 2026-08-31. No holding tickers published.",
        "PR": "Partial: Top 10 only; as of 2026-08-31. No holding tickers published.",
        "PBAL": "NO_HOLDINGS: PIMCO Managed Balanced Portfolio, incepted 2026-01-26; no holdings Excel or holdings table published yet (2026-08-31).",
    }
    with open(NOTES, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for t, note in notes.items():
            if t not in existing:
                w.writerow([t, note])
    print(f"merged {len(rows)} rows across {len(tickers)} tickers; master rows: {len(kept)+len(rows)}")

if __name__ == "__main__":
    main()
