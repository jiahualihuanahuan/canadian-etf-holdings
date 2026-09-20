# Canadian ETF Holdings Dataset

Holdings for Canadian-listed ETFs, collected from official issuer websites. **Work in progress** — extraction is ongoing.

## Dataset (2026-09-20, partial)

| File | Contents |
|---|---|
| `canadian_etf_holdings_MASTER.csv` | **236,183 holding rows** across **946 tickers**: `etf_ticker, etf_name, holding_ticker, holding_name, weight_pct, as_of_date, source, provider` |
| `canadian_etf_list.csv` + `universe_expansion_new.csv` | **1,173 ETF universe** (provisional) — ticker, name, provider |
| `coverage_notes.csv` | **829 coverage notes** — status for ETFs without complete holdings (terminated, Top-N only, extraction pending) |

**Coverage:** 946 of 1,173 provisional classes (80.6%) have complete holdings from issuer-published sources. The universe list is still being reconciled (terminated funds, renames, mergers, ticker reuse).

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
- **Fidelity** (FCCB, 1,101 holdings) — browser-extracted from fidelity.ca
- **Mackenzie** (30+ funds) — browser-extracted from mackenzieinvestments.com

Fund-of-funds ETFs show their direct underlying holdings (e.g., XEQT holds XIC/XUU/XEF). We do not duplicate look-through portfolios.

## Known limitations

1. **~227 classes lack complete holdings.** Reasons documented in `coverage_notes.csv`:
   - Terminated/merged funds
   - Issuers publishing Top-10/Top-25 only
   - Extraction pending (Mackenzie QEE — complete holdings not published; others)
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
