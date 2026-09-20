# Canadian ETF Holdings Dataset

Holdings for Canadian-listed ETFs, collected from official issuer websites. **Work in progress** — extraction is ongoing.

## Dataset (2026-09-20, partial)

| File | Contents |
|---|---|
| `canadian_etf_holdings_MASTER.csv` | **292,802 holding rows** across **1,419 tickers**: `etf_ticker, etf_name, holding_ticker, holding_name, weight_pct, as_of_date, source, provider` |
| `all_etfs_yahoo.csv` | **2,038-entry ETF universe** — ticker, name, provider |
| `coverage_notes.csv` | **833 coverage notes** — status for ETFs without complete holdings (terminated, Top-N only, bond funds skipped, extraction pending) |
| `missing_etfs_vs_master.csv` | **711 tickers** in universe without complete holdings in master |

**Coverage:** 1,419 of 2,038 universe entries (69.6%) have complete holdings from issuer-published sources. Bond/fixed-income ETFs are included where official complete holdings are available.

## Sources

Holdings come from official issuer websites (CSV/XLSX downloads or published tables):
- **Vanguard** — official holdings XLSX
- **BlackRock/iShares** — official holdings CSV exports
- **CIBC, Desjardins, PIMCO, Franklin Templeton, BMO, CI GAM, Scotia** — official downloads
- **Harvest** (21 funds) — browser-extracted from harvestetfs.com
- **Hamilton** (22 funds) — browser-extracted from hamiltonetfs.com
- **Manulife** (11 funds, 21 tickers) — browser-extracted from manulifeim.com
- **First Trust** (7 funds) — browser-extracted
- **Fidelity** (6 funds) — official downloads
- **Fidelity** (FCCB 1,101 holdings; FCGB 1,963 holdings as of 2026-06-30 via official holdings API — weights truncated to 2dp by issuer, sum 90.04%, see coverage note) — fidelity.ca
- **Mackenzie** (30+ funds) — browser-extracted from mackenzieinvestments.com

Fund-of-funds ETFs show their direct underlying holdings (e.g., XEQT holds XIC/XUU/XEF). We do not duplicate look-through portfolios.

## Known limitations

1. **711 tickers lack complete holdings.** Reasons documented in `coverage_notes.csv`:
   - Terminated/merged funds (e.g., Harvest HBFE/HLFE terminated 2024)
   - Issuers publishing Top-10/Top-25 only
   - Bond/fixed-income ETFs where only Top-N is published
   - Extraction pending
2. **Weight sums** are preserved as published. Leveraged/inverse funds and derivatives may sum above 100%.
3. **Blank holding tickers** mean the issuer did not publish a ticker (common for bonds, FX forwards, cash). We never invent tickers.
4. **As-of dates** vary by issuer (most September 2026; some June/August 2026 for semi-annual filers).
5. The **1,173-class universe is provisional** — it includes terminated funds, renames, and possible duplicates still being reconciled.

## Scripts

| Script | Purpose |
|---|---|
| `parse_downloads.py` | Parses issuer CSV/XLSX downloads into the master (resumable via `parsed_downloads.json`; **not** safely idempotent — back up before merging) |
| `fetch_holdings.py` | Legacy top-10 collector (finance-query API) |
| `fetch_holdings_full.py` | Legacy issuer-table scraper |

## Reproducibility

```bash
~/workspace/.venvs/insider-tracker/bin/python parse_downloads.py
```

Parses new files in `~/workspace/browser_downloads/sess-*/`, skips already-processed files, appends to the master.
