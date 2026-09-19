# Canadian ETF Holdings Dataset

Complete holdings for Canadian-listed ETFs, collected from official issuer websites.

## Dataset (2026-09-19)

| File | Contents |
|---|---|
| `canadian_etf_holdings_MASTER.csv` | **217,131 holding rows** — one row per holding per ETF: `etf_ticker, etf_name, holding_ticker, holding_name, weight_pct, as_of_date, source, provider` |
| `canadian_etf_list.csv` + `universe_expansion_new.csv` | **1,173 ETF universe** — ticker, name, provider |
| `coverage_notes.csv` | **821 coverage notes** — honest status for ETFs without complete holdings (terminated, Top-N only, extraction pending) |

**Coverage:** 839 of 1,173 ETFs (71.5%) have complete holdings from issuer-published sources. Every ETF is classified — 0 unclassified.

## Sources

Holdings come from official issuer websites (CSV/XLSX downloads or published tables):
- **Vanguard** (117,965 rows) — official holdings XLSX
- **BlackRock/iShares** (28,510 rows) — official holdings CSV exports
- **CIBC, Desjardins, PIMCO, Franklin Templeton, BMO, CI GAM, Scotia** — official downloads
- **Harvest** (42 funds) — browser-extracted from harvestetfs.com
- **Hamilton** — browser-extracted from hamiltonetfs.com

Fund-of-funds ETFs show their direct underlying holdings (e.g., XEQT holds XIC/XUU/XEF). We do not duplicate look-through portfolios.

## Honest limitations

1. **334 ETFs lack complete holdings.** Reasons documented in `coverage_notes.csv`:
   - Terminated/merged funds (e.g., First Asset tickers absorbed by CI)
   - Issuers publishing Top-10/Top-25 only (e.g., Hamilton HFG/HUM via SOI)
   - Extraction pending for Fidelity (72), Mackenzie (47), Manulife (27)
2. **Weight sums** are preserved as published. Leveraged/inverse funds and derivatives may sum above 100%.
3. **Blank holding tickers** mean the issuer did not publish a ticker (common for bonds, FX forwards, cash). We never invent tickers.
4. **As-of dates** vary by issuer (most September 2026; some June 2026 for semi-annual filers).

## Scripts

| Script | Purpose |
|---|---|
| `parse_downloads.py` | Parses issuer CSV/XLSX downloads into the master (idempotent, resumable via `parsed_downloads.json`) |
| `fetch_holdings.py` | Legacy top-10 collector (finance-query API) |
| `fetch_holdings_full.py` | Legacy issuer-table scraper |

## Reproducibility

```bash
~/workspace/.venvs/insider-tracker/bin/python parse_downloads.py
```

Parses new files in `~/workspace/browser_downloads/sess-*/`, skips already-processed files, appends to the master.
