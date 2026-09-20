#!/usr/bin/env python3
"""
Fetch holdings for every Canadian ETF and save them incrementally to CSV.

ETF list source : Wikipedia "List of Canadian exchange-traded funds"
Holdings source  : finance-query API (https://finance-query.com/v2/etf-profile/<T>.TO)
                   NOTE: this source returns the TOP 10 holdings per ETF only.
                   Full portfolio holdings sit behind bot protection on
                   aggregator sites; see README.md for details.

Outputs (in this script's directory):
  canadian_etf_list.csv      - ticker, exchange, name, provider
  canadian_etf_holdings.csv  - one row per holding, appended + flushed per ETF
  progress.json              - tickers already processed (reruns skip them)

Usage:
  python fetch_holdings.py --test        # dry run on ~10 diverse ETFs
  python fetch_holdings.py              # full run
  python fetch_holdings.py --limit 50    # first 50 unprocessed ETFs
  python fetch_holdings.py --reset       # wipe progress + holdings csv, start over
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE = Path(__file__).resolve().parent
ETF_LIST_CSV = BASE / "canadian_etf_list.csv"
HOLDINGS_CSV = BASE / "canadian_etf_holdings.csv"
PROGRESS_FILE = BASE / "progress.json"

WIKI_URL = "https://en.wikipedia.org/wiki/List_of_Canadian_exchange-traded_funds"
HOLDINGS_URL = "https://finance-query.com/v2/etf-profile/{symbol}"
COVERAGE = "top_10"  # finance-query only exposes the top 10 holdings

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36 "
        "personal-research-etf-holdings-script"
    )
}

HOLDINGS_COLUMNS = [
    "etf_ticker", "etf_exchange", "etf_name", "provider",
    "holding_ticker", "holding_name", "weight_pct", "market_value",
    "shares", "change_shares_pct", "change_shares", "pct_owned",
    "data_as_of", "source", "coverage", "fetched_at", "status",
]

TEST_TICKERS = ["XIU", "VCN", "ZSP", "XEQT", "FIE", "HXT", "VFV", "ZAG", "XIC", "CASH"]


def get_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


# ---------------------------------------------------------------- ETF list --
def fetch_etf_list(session: requests.Session) -> list[dict]:
    """Parse the Wikipedia list of Canadian ETFs into ticker records."""
    r = session.get(WIKI_URL, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    etfs: list[dict] = []
    seen: set[str] = set()

    # The page is organized as provider headings followed by bullet lists like
    # "- TSX: HHL - Harvest Healthcare Leaders Income ETF".
    content = soup.find("div", {"class": "mw-parser-output"}) or soup
    provider = ""
    # Skip reference/footnote lists - they contain date-like junk matches.
    for junk in content.select(".reflist, .references, .navbox"):
        junk.decompose()

    def clean_provider(raw: str) -> str:
        p = raw.replace("[edit]", "").strip()
        # Junk like "May 6", "Apr 14 2015" comes from citation remnants.
        if re.fullmatch(r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*"
                        r"\s+\d{1,2}(,?\s+\d{4})?", p, re.IGNORECASE):
            return ""
        return p

    def handle_text(text: str, prov: str) -> None:
        m = re.search(r"\b(TSX|NEO|CBOE|CSE)\s*:\s*([A-Z][A-Z0-9.\-]{0,7})", text)
        if not m:
            return
        exchange, ticker = m.group(1).upper(), m.group(2).upper().rstrip(".-")
        name = text[m.end():].strip()
        name = re.sub(r"^[\-–—:;.]+\s*", "", name)
        name = re.sub(r"\s+", " ", name).strip()[:200]
        key = f"{exchange}:{ticker}"
        if key in seen:
            return
        seen.add(key)
        etfs.append({"ticker": ticker, "exchange": exchange,
                     "name": name, "provider": prov})

    for el in content.find_all(["h2", "h3", "h4", "li", "tr"]):
        if el.name in ("h2", "h3", "h4"):
            provider = clean_provider(el.get_text(" ", strip=True)) or provider
            continue
        if el.name == "li":
            handle_text(el.get_text(" ", strip=True), provider)
        elif el.name == "tr":
            # Some provider sections use tables: ticker usually in first cell.
            cells = [c.get_text(" ", strip=True)
                     for c in el.find_all(["td", "th"])]
            if cells:
                handle_text(" ".join(cells), provider)
    return etfs


def save_etf_list(etfs: list[dict]) -> None:
    with open(ETF_LIST_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["ticker", "exchange", "name", "provider"])
        w.writeheader()
        w.writerows(etfs)


# --------------------------------------------------------------- holdings --
def candidate_symbols(ticker: str, exchange: str) -> list[str]:
    """finance-query symbol variants to try for an ETF."""
    suffix = {"TSX": ".TO", "NEO": ".NE", "CBOE": ".NE", "CSE": ".CN"}.get(
        exchange, ".TO")
    variants = [f"{ticker}{suffix}"]
    # USD series like DLR.U -> Yahoo style DLR-U.TO
    if "." in ticker:
        variants.append(f"{ticker.replace('.', '-')}{suffix}")
    variants.append(ticker)  # bare, just in case
    # dedupe, preserve order
    return list(dict.fromkeys(variants))


def parse_etf_profile(data: dict) -> tuple[list[dict], str, str]:
    """Return (holdings rows, etf name, asset type) from finance-query JSON."""
    holdings = []
    for h in data.get("holdings") or []:
        weight = h.get("weight")
        try:
            weight_pct = round(float(weight) * 100, 4) if weight is not None else ""
        except (TypeError, ValueError):
            weight_pct = ""
        holdings.append({
            "holding_ticker": h.get("symbol") or "",
            "holding_name": h.get("description") or "",
            "weight_pct": weight_pct,
            "market_value": "",
            "shares": "",
            "change_shares_pct": "",
            "change_shares": "",
            "pct_owned": "",
        })
    return holdings, data.get("name") or "", data.get("assetType") or ""


def fetch_with_retry(session: requests.Session, url: str,
                     retries: int = 3) -> requests.Response | None:
    for attempt in range(retries):
        try:
            r = session.get(url, timeout=25)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(2 ** attempt * 2)
                continue
            return r
        except requests.RequestException:
            time.sleep(2 ** attempt * 2)
    return None


def fetch_holdings(session: requests.Session, ticker: str,
                   exchange: str) -> tuple[list[dict], str, str, str]:
    """Return (holdings, as_of, etf_name, status)."""
    tried: list[str] = []
    for symbol in candidate_symbols(ticker, exchange):
        url = HOLDINGS_URL.format(symbol=symbol)
        r = fetch_with_retry(session, url)
        if r is None:
            tried.append(f"{symbol}:no-response")
            continue
        if r.status_code == 404:
            tried.append(f"{symbol}:404")
            continue
        if r.status_code != 200:
            tried.append(f"{symbol}:http-{r.status_code}")
            continue
        try:
            data = r.json()
        except ValueError:
            tried.append(f"{symbol}:bad-json")
            continue
        holdings, api_name, _asset = parse_etf_profile(data)
        if holdings:
            return holdings, "", api_name, "ok"
        if data.get("symbol") or data.get("name"):
            tried.append(f"{symbol}:200-no-holdings")
        else:
            tried.append(f"{symbol}:200-empty")
    return [], "", "", "no_holdings_found [" + " ".join(tried) + "]"


def probe(session: requests.Session, ticker: str, exchange: str = "TSX") -> None:
    """Diagnostic: show what happens when fetching one ticker."""
    for symbol in candidate_symbols(ticker, exchange):
        url = HOLDINGS_URL.format(symbol=symbol)
        print(f"GET {url}")
        try:
            r = session.get(url, timeout=25)
        except requests.RequestException as exc:
            print(f"  request failed: {exc}")
            continue
        print(f"  HTTP {r.status_code}, {len(r.text)} chars")
        if r.status_code != 200:
            print(f"  body snippet: {r.text[:200]!r}")
            continue
        try:
            data = r.json()
        except ValueError:
            print("  not JSON")
            continue
        holdings, api_name, asset = parse_etf_profile(data)
        print(f"  name={api_name!r} asset={asset!r} holdings={len(holdings)}")
        for h in holdings[:5]:
            print(f"    {h['holding_ticker']}: {h['holding_name']} "
                  f"{h['weight_pct']}%")
        if holdings:
            return


# ------------------------------------------------------------------ main ----
def load_progress() -> set[str]:
    if PROGRESS_FILE.exists():
        try:
            return set(json.loads(PROGRESS_FILE.read_text()).get("done", []))
        except (json.JSONDecodeError, OSError):
            return set()
    return set()


def save_progress(done: set[str]) -> None:
    PROGRESS_FILE.write_text(json.dumps(
        {"done": sorted(done),
         "updated_at": datetime.now(timezone.utc).isoformat()}, indent=1))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true",
                    help="run on a small diverse set of ETFs only")
    ap.add_argument("--limit", type=int, default=0,
                    help="max number of (unprocessed) ETFs to handle")
    ap.add_argument("--delay", type=float, default=0.5,
                    help="seconds between requests")
    ap.add_argument("--reset", action="store_true",
                    help="wipe progress + holdings CSV and start over")
    ap.add_argument("--probe", metavar="TICKER",
                    help="diagnose fetching for one ticker, then exit")
    args = ap.parse_args()

    session = get_session()

    if args.probe:
        probe(session, args.probe.upper())
        return 0

    if args.reset:
        for p in (HOLDINGS_CSV, PROGRESS_FILE):
            if p.exists():
                p.unlink()
        print("progress + holdings CSV wiped")

    # --- ETF list (fresh each run; cheap, keeps names/providers current) ---
    print("fetching ETF list from Wikipedia ...", flush=True)
    etfs = fetch_etf_list(session)
    print(f"found {len(etfs)} Canadian ETF listings")
    if not etfs:
        print("ERROR: no ETFs parsed from Wikipedia; aborting")
        return 1
    save_etf_list(etfs)

    if args.test:
        wanted = set(TEST_TICKERS)
        etfs = [e for e in etfs if e["ticker"] in wanted]
        # include any test ticker missing from Wikipedia anyway
        have = {e["ticker"] for e in etfs}
        for t in TEST_TICKERS:
            if t not in have:
                etfs.append({"ticker": t, "exchange": "TSX",
                             "name": "", "provider": "test-fallback"})

    done = load_progress()
    todo = [e for e in etfs if f'{e["exchange"]}:{e["ticker"]}' not in done]
    if args.limit:
        todo = todo[:args.limit]
    print(f"{len(done)} already done, {len(todo)} to process", flush=True)

    new_file = not HOLDINGS_CSV.exists()
    out = open(HOLDINGS_CSV, "a", newline="", encoding="utf-8")
    writer = csv.DictWriter(out, fieldnames=HOLDINGS_COLUMNS)
    if new_file:
        writer.writeheader()
        out.flush()

    ok_count = fail_count = holding_rows = 0
    try:
        for i, etf in enumerate(todo, 1):
            key = f'{etf["exchange"]}:{etf["ticker"]}'
            fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            try:
                holdings, as_of, api_name, status = fetch_holdings(
                    session, etf["ticker"], etf["exchange"])
            except Exception as exc:  # never let one ETF kill the run
                holdings, as_of, api_name, status = (
                    [], "", "", f"error: {type(exc).__name__}")

            base = {
                "etf_ticker": etf["ticker"], "etf_exchange": etf["exchange"],
                "etf_name": api_name or etf["name"], "provider": etf["provider"],
                "data_as_of": as_of, "source": "finance-query",
                "coverage": COVERAGE, "fetched_at": fetched_at,
            }
            if holdings:
                ok_count += 1
                for h in holdings:
                    writer.writerow({**base, **h, "status": status})
                    holding_rows += 1
            else:
                fail_count += 1
                writer.writerow({**base,
                                 "holding_ticker": "", "holding_name": "",
                                 "weight_pct": "", "market_value": "",
                                 "shares": "", "change_shares_pct": "",
                                 "change_shares": "", "pct_owned": "",
                                 "status": status})
            out.flush()
            done.add(key)
            if i % 10 == 0:
                save_progress(done)
            print(f"[{i}/{len(todo)}] {key}: {status} "
                  f"({len(holdings)} holdings)", flush=True)
            time.sleep(args.delay)
    finally:
        save_progress(done)
        out.close()

    print(f"\nDONE: {ok_count} ETFs with holdings, {fail_count} without, "
          f"{holding_rows} holding rows total")
    print(f"holdings CSV: {HOLDINGS_CSV}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
