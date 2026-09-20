#!/usr/bin/env python3
"""Collect COMPLETE holdings (ticker + weight) from Canadian ETF issuers'
official websites.

Covers the 4 providers with verified scriptable sources:
  Harvest ETFs      - HTML table, publishes holding TICKERS (complete)
  Hamilton ETFs     - HTML table, publishes holding TICKERS (complete for
                      small portfolios, top-10 for large ones)
  First Trust       - HTML table, names + weights (tickers resolved via
                      name->ticker mapping)
  Global X Canada   - HTML divs, top-10 names + weights (tickers resolved)

Evolve ETFs blocks scripted fetching (HTTP 403) -> marked source_blocked,
needs the live-browser phase. BMO / iShares / Vanguard / Purpose / CI need
live-browser work too (see provider_holdings_sources.json).

Outputs (in this script's directory):
  canadian_etf_holdings_full.csv - one row per holding, appended+flushed per ETF
  progress_full.json             - tickers already processed (reruns skip them)
  ticker_cache.json              - name -> ticker resolutions (Yahoo + seed)

Columns: etf_ticker, etf_exchange, etf_name, provider, holding_ticker,
holding_name, weight_pct, data_as_of, source, coverage, ticker_source,
fetched_at, status

ticker_source: issuer | seed | yahoo | n/a  ("" when unresolved)
coverage:      complete | top_10 | source_blocked | terminated | ...
"""

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
SEED_CSV = BASE / "canadian_etf_holdings.csv"
OUT_CSV = BASE / "canadian_etf_holdings_full.csv"
PROGRESS_FILE = BASE / "progress_full.json"
CACHE_FILE = BASE / "ticker_cache.json"

TERMINATED = {"QCD", "QUS", "FDE", "EUR", "PLV"}

OUT_COLUMNS = [
    "etf_ticker", "etf_exchange", "etf_name", "provider",
    "holding_ticker", "holding_name", "weight_pct",
    "data_as_of", "source", "coverage", "ticker_source",
    "fetched_at", "status",
]

TEST_TICKERS = ["HHL", "HTA", "HCA", "HFG", "FST", "FINT", "HXS", "HXQ"]


# ------------------------------------------------------------------ http ----
def get_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/126.0.0.0 Safari/537.36"),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-CA,en;q=0.9",
    })
    return s


def fetch_with_retry(session: requests.Session, url: str,
                     retries: int = 3) -> requests.Response | None:
    for attempt in range(retries):
        try:
            r = session.get(url, timeout=30)
            if r.status_code == 403:
                return r  # don't retry blocks; caller decides
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(2 ** attempt * 2)
                continue
            return r
        except requests.RequestException:
            time.sleep(2 ** attempt * 2)
    return None


# ------------------------------------------------------- name -> ticker ----
def normalize_name(name: str) -> str:
    n = name.upper()
    n = re.sub(r"[^A-Z0-9 ]", " ", n)
    return re.sub(r"\s+", " ", n).strip()


SUFFIX_MAP = [
    (r"\bINCORPORATED\b", "INC"),
    (r"\bCORPORATION\b", "CORP"),
    (r"\bPUBLIC LIMITED COMPANY\b", "PLC"),
    (r"\bLIMITED\b", "LTD"),
    (r"\bCOMPANY\b", "CO"),
    (r"\bHOLDINGS\b", "HLDG"),
]


def canon_company(name: str) -> str:
    """Canonical form for fuzzy company-name matching."""
    n = normalize_name(name)
    for pat, rep in SUFFIX_MAP:
        n = re.sub(pat, rep, n)
    return re.sub(r"\s+", " ", n).strip()


# Manual overrides for renamed companies / stale ETF names Yahoo can't match
MANUAL_TICKERS = {
    "COCA COLA EUROPEAN PARTNERS PLC": "CCEP",  # now Coca-Cola Europacific
    "BMO EMERGING MARKETS BOND HEDGED TO CAD INDEX ETF": "ZEF.TO",
    "ISHARES ADVANTAGED CONVERTIBLE BOND INDEX ETF": "CVD.TO",
    "ISHARES CANADIAN CORPORATE BOND INDEX ETF": "XCB.TO",
    "ISHARES CORE S&P/TSX COMPOSITE HIGH DIVIDEND INDEX ETF": "XEI.TO",
    "ISHARES CANADIAN GOVERNMENT BOND INDEX ETF": "XGB.TO",
}


def load_seed_map() -> dict[str, str]:
    """holding_name -> holding_ticker from the top-10 CSV we already have."""
    seed: dict[str, str] = {}
    seed.update({normalize_name(k): v for k, v in MANUAL_TICKERS.items()})
    if not SEED_CSV.exists():
        return seed
    with open(SEED_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            t, n = (row.get("holding_ticker") or "").strip(), \
                   (row.get("holding_name") or "").strip()
            if t and n:
                seed.setdefault(normalize_name(n), t)
    return seed


def load_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_cache(cache: dict) -> None:
    CACHE_FILE.write_text(json.dumps(cache, indent=1, sort_keys=True))


class TickerResolver:
    def __init__(self, session: requests.Session, delay: float = 0.25):
        self.session = session
        self.delay = delay
        self.seed = load_seed_map()
        self.cache = load_cache()
        # drop stale "unresolved" entries so they are retried with the
        # improved lookup instead of being stuck forever
        self.cache = {k: v for k, v in self.cache.items()
                      if not (isinstance(v, dict)
                              and v.get("source") == "unresolved")}
        self._saved = 0

    def _yahoo_lookup(self, name: str) -> tuple[str, str]:
        """Return (ticker, source_note). May be ('', 'unresolved')."""
        # query variants: full name, then with corporate suffixes stripped
        # ("Tetra Tech, Inc." confuses Yahoo; "Tetra Tech" nails it)
        base = re.sub(r"\s*\([^)]*\)\s*", " ", name).strip()
        base = re.sub(r"\s+\d+$", "", base).strip()
        variants = [base]
        no_comma = base.replace(",", "")
        if no_comma != base:
            variants.append(no_comma)
        nosuffix = re.sub(
            r",?\s+(INCORPORATED|CORPORATION|PUBLIC LIMITED COMPANY|"
            r"LIMITED|COMPANY|HOLDINGS|INC|CORP|PLC|LTD|CO)\.?$", "",
            base, flags=re.IGNORECASE).strip(" ,")
        if nosuffix and normalize_name(nosuffix) != normalize_name(base):
            variants.append(nosuffix)
        want = canon_company(name)
        for query in variants:
            time.sleep(self.delay)  # politeness BEFORE the request
            quotes = []
            for attempt in range(3):
                try:
                    r = self.session.get(
                        "https://query1.finance.yahoo.com/v1/finance/search",
                        params={"q": query, "quotesCount": 8}, timeout=20)
                except (requests.RequestException, ValueError):
                    return "", "unresolved"
                if r.status_code == 429:
                    time.sleep(5 * (attempt + 1))
                    continue
                if r.status_code != 200:
                    return "", "unresolved"
                try:
                    quotes = [q for q in r.json().get("quotes", [])
                              if q.get("quoteType") in ("EQUITY", "ETF")
                              and q.get("symbol")]
                except ValueError:
                    return "", "unresolved"
                break
            exact, partial = [], []
            for q in quotes:
                qn = canon_company(
                    q.get("longname") or q.get("shortname") or "")
                if not qn:
                    continue
                if qn == want:
                    exact.append(q["symbol"])
                elif want in qn or qn in want:
                    partial.append(q["symbol"])
            # first exact name match wins (no exchange preference: keeps us
            # consistent with the seed dictionary, which is market-correct)
            if exact:
                return exact[0], "yahoo"
            if partial:
                return partial[0], "yahoo"
        return "", "unresolved"

    def resolve(self, name: str) -> tuple[str, str]:
        """Return (ticker, ticker_source)."""
        key = normalize_name(name)
        if not key:
            return "", ""
        # ticker embedded in the name, e.g. "... ETF (QQQX.U)"
        m = re.search(r"\(([A-Z][A-Z0-9.\-]{1,10})\)", name.upper())
        if m:
            return m.group(1), "name_embedded"
        if key in self.seed:
            return self.seed[key], "seed"
        if key in self.cache:
            c = self.cache[key]
            return c.get("ticker", ""), c.get("source", "")
        # skip obvious non-equity rows (but not bond ETFs, which resolve)
        if "ETF" not in key and (
                re.search(r"\b(cash|forward|option|swap|t-bill|tbill|"
                          r"treasury|billet)\b", key, re.IGNORECASE)
                or re.search(r"\b(GOVERNMENT OF CANADA|GOV OF CANADA|"
                             r"CANADIAN GOVERNMENT BOND|"
                             r"PROV(\.|INCE)? OF|HIS MAJESTY|"
                             r"CITY OF|MUNICIPAL)\b", key)):
            self.cache[key] = {"ticker": "", "source": "n/a"}
            return "", "n/a"
        ticker, source = self._yahoo_lookup(name)
        self.cache[key] = {"ticker": ticker, "source": source}
        self._saved += 1
        if self._saved % 25 == 0:
            save_cache(self.cache)
        return ticker, source

    def flush(self):
        save_cache(self.cache)


# ------------------------------------------------------------------ parse ----
def parse_weight(raw: str) -> str:
    s = raw.strip()
    neg = s.startswith("(")
    s = s.strip("()% ").replace(",", ".")
    m = re.search(r"-?\d+(\.\d+)?", s)
    if not m:
        return ""
    try:
        v = float(m.group(0))
        return str(-v if neg else v)
    except ValueError:
        return ""


def clean_issuer_ticker(raw: str) -> str:
    """'REGN US' -> 'REGN'; 'TBIL CN' -> 'TBIL'."""
    t = raw.strip().upper()
    t = re.sub(r"\s+(US|CN|CA)$", "", t)
    return t


def load_etf_name_map() -> dict[str, str]:
    """ETF name -> ticker from our own ETF list (for fund-of-funds)."""
    m: dict[str, str] = {}
    if not ETF_LIST_CSV.exists():
        return m
    with open(ETF_LIST_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            n, t = (row.get("name") or "").strip(), \
                   (row.get("ticker") or "").strip()
            if n and t:
                # strip class suffixes: "Foo ETF A" / "Foo ETF (A)" -> base
                key = normalize_name(re.sub(r"\s+[\(\[]?[A-Z][\)\]]?$", "", n))
                m.setdefault(key, t)
    return m


ETF_NAME_MAP = load_etf_name_map()


def resolve_etf_name(name: str) -> str:
    """Map a holding name like 'Harvest Tech Leaders Income ETF 2' to a ticker."""
    key = normalize_name(re.sub(r"\s*\d+$", "", name))  # drop footnote digits
    if key in ETF_NAME_MAP:
        return ETF_NAME_MAP[key]
    # try without trailing class letter in parens, e.g. "Foo ETF (A)"
    key2 = normalize_name(re.sub(r"\s*\([A-Z]\)$", "", name))
    return ETF_NAME_MAP.get(key2, "")


# --------------------------------------------------------------- adapters --
def adapt_harvest(session, ticker, resolver=None):
    """ticker/name/weight table. Returns (holdings, as_of, coverage, status)."""
    base = ticker.split(".")[0].lower()
    tried = []
    for url in (f"https://harvestportfolios.com/etf/{base}/",
                f"https://harvestportfolios.com/fr-CA/etf/{base}/"):
        r = fetch_with_retry(session, url)
        if r is None or r.status_code != 200:
            tried.append(f"{url}:{(r.status_code if r else 'no-response')}")
            continue
        soup = BeautifulSoup(r.text, "html.parser")
        for tbl in soup.find_all("table"):
            rows = tbl.find_all("tr")
            if not rows:
                continue
            heads = [c.get_text(" ", strip=True).lower()
                     for c in rows[0].find_all(["td", "th"])]
            if "weight" in heads and ("name" in heads or "etf name" in heads):
                # Ticker column is optional (e.g. TBIL's table is Name|Weight)
                name_h = "etf name" if "etf name" in heads else "name"
                hi = {"name": heads.index(name_h),
                      "weight": heads.index("weight")}
                ti = heads.index("ticker") if "ticker" in heads else None
                holdings = []
                for tr in rows[1:]:
                    cells = [c.get_text(" ", strip=True)
                             for c in tr.find_all(["td", "th"])]
                    if len(cells) <= max(hi.values()):
                        continue
                    name, wt = cells[hi["name"]], cells[hi["weight"]]
                    if not name:
                        continue
                    tick = clean_issuer_ticker(cells[ti]) \
                        if ti is not None and len(cells) > ti else ""
                    tsrc = "issuer" if tick else "n/a"
                    if not tick:
                        # fund-of-funds: resolve via our ETF list, then Yahoo
                        tick = resolve_etf_name(name)
                        if tick:
                            tsrc = "etf_list"
                        elif resolver is not None:
                            tick, tsrc = resolver.resolve(name)
                            if not tick:
                                tsrc = "n/a"
                    holdings.append({
                        "holding_ticker": tick,
                        "holding_name": name,
                        "weight_pct": parse_weight(wt),
                        "ticker_source": tsrc,
                    })
                m = re.search(r"As at ([\d/]+)", r.text)
                if holdings:
                    return holdings, (m.group(1) if m else ""), \
                        "complete", "ok"
        tried.append(f"{url}:no-holdings-table")
    return [], "", "", "no_holdings_table [" + " ".join(tried) + "]"


def adapt_hamilton(session, ticker):
    base = ticker.lower().replace(".", "-")
    url = f"https://hamiltonetfs.com/etf/{base}/"
    r = fetch_with_retry(session, url)
    if r is None:
        return [], "", "", "no-response"
    if r.status_code != 200:
        return [], "", "", f"http-{r.status_code}"
    soup = BeautifulSoup(r.text, "html.parser")
    coverage = "complete"
    for h in soup.find_all(["h2", "h3", "h4"]):
        t = h.get_text(strip=True).lower()
        if "holding" in t:
            if "top" in t:
                coverage = "top_10"
            tbl = h.find_next("table")
            if not tbl:
                continue
            rows = tbl.find_all("tr")
            heads = [c.get_text(" ", strip=True).lower()
                     for c in rows[0].find_all(["td", "th"])] if rows else []
            if "ticker" in heads and "weight" in heads:
                hi = {h_: heads.index(h_) for h_ in ("ticker", "name", "weight")
                      if h_ in heads}
                holdings = []
                for tr in rows[1:]:
                    cells = [c.get_text(" ", strip=True)
                             for c in tr.find_all(["td", "th"])]
                    if len(cells) <= max(hi.values()):
                        continue
                    tick = clean_issuer_ticker(cells[hi["ticker"]])
                    name = cells[hi["name"]] if "name" in hi else ""
                    if not tick and not name:
                        continue
                    holdings.append({
                        "holding_ticker": tick,
                        "holding_name": name,
                        "weight_pct": parse_weight(cells[hi["weight"]]),
                        "ticker_source": "issuer" if tick else "n/a",
                    })
                m = re.search(
                    r"As at ([A-Z][a-z]+ \d{1,2},? \d{4}|\d{4}/\d{2}/\d{2})",
                    r.text)
                if holdings:
                    return holdings, (m.group(1) if m else ""), \
                        coverage, "ok"
            return [], "", "", "holdings-table-unparseable"
    return [], "", "", "no-holdings-section"


def _generic_name_weight_table(session, url, name_headers, weight_headers,
                               resolver):
    """Parse a 2-col name/weight table; resolve tickers."""
    r = fetch_with_retry(session, url)
    if r is None:
        return [], "", "no-response"
    if r.status_code != 200:
        return [], "", f"http-{r.status_code}"
    soup = BeautifulSoup(r.text, "html.parser")
    for tbl in soup.find_all("table"):
        rows = tbl.find_all("tr")
        if not rows:
            continue
        heads = [c.get_text(" ", strip=True).lower()
                 for c in rows[0].find_all(["td", "th"])]
        name_i = next((i for i, h in enumerate(heads)
                       if any(k in h for k in name_headers)), None)
        wt_i = next((i for i, h in enumerate(heads)
                     if any(k in h for k in weight_headers)), None)
        if name_i is None or wt_i is None:
            continue
        holdings = []
        for tr in rows[1:]:
            cells = [c.get_text(" ", strip=True)
                     for c in tr.find_all(["td", "th"])]
            if len(cells) <= max(name_i, wt_i) or not cells[name_i]:
                continue
            name = cells[name_i]
            tick, tsrc = resolver.resolve(name)
            holdings.append({
                "holding_ticker": tick,
                "holding_name": name,
                "weight_pct": parse_weight(cells[wt_i]),
                "ticker_source": tsrc,
            })
        if holdings:
            return holdings, "", "ok"
    return [], "", "no-holdings-table"


def adapt_firsttrust(session, ticker, resolver):
    # class tickers (FST.A) usually only resolve under the base ticker
    candidates = [ticker]
    base = ticker.split(".")[0]
    if base != ticker:
        candidates.append(base)
    tried = []
    for cand in candidates:
        url = ("https://www.firsttrust.ca/Retail/Etf/EtfHoldingsListing.aspx"
               f"?Ticker={cand}")
        holdings, as_of, status = _generic_name_weight_table(
            session, url, ("security name",), ("net assets",), resolver)
        if status == "ok":
            m = None
            r = fetch_with_retry(session, url)
            if r is not None:
                m = re.search(
                    r"[Aa]s of ([A-Z][a-z]+ \d{1,2},? \d{4}|\d{4}-\d{2}-\d{2})",
                    r.text)
            return holdings, (m.group(1) if m else ""), "complete", "ok"
        tried.append(f"{cand}:{status}")
    return [], "", "", "no-holdings-table [" + " ".join(tried) + "]"


def adapt_globalx(session, ticker, resolver):
    slug = ticker.lower().replace(".", "-")
    tried = []
    for url in (f"https://www.globalx.ca/product/{ticker}",
                f"https://www.globalx.ca/product/{slug}"):
        r = fetch_with_retry(session, url)
        if r is None or r.status_code != 200:
            tried.append(f"{url}:{(r.status_code if r else 'no-response')}")
            continue
        soup = BeautifulSoup(r.text, "html.parser")
        holdings = []

        def collect_from(container):
            for div in container.find_all("div", recursive=False):
                ps = div.find_all("p", recursive=False)
                if len(ps) != 2:
                    continue
                name = ps[0].get_text(" ", strip=True)
                wt = ps[1].get_text(" ", strip=True)
                if not name or "security name" in name.lower():
                    continue
                if not re.search(r"\d", wt):
                    continue
                tick, tsrc = resolver.resolve(name)
                holdings.append({
                    "holding_ticker": tick,
                    "holding_name": name,
                    "weight_pct": parse_weight(wt),
                    "ticker_source": tsrc,
                })

        for div in soup.find_all("div"):
            ps = div.find_all("p", recursive=False)
            if len(ps) == 2 and \
                    "security name" in ps[0].get_text(strip=True).lower() and \
                    "weight" in ps[1].get_text(strip=True).lower():
                # holdings are this header's following siblings, plus an
                # optional second column next to the header's parent
                collect_from(div.parent)
                parent_sib = div.parent.find_next_sibling("div")
                if parent_sib:
                    collect_from(parent_sib)
                break
        m = re.search(r"As at ([A-Z][a-z]+ \d{1,2},? \d{4})", r.text)
        if holdings:
            return holdings, (m.group(1) if m else ""), "top_10", "ok"
        tried.append(f"{url}:no-holdings-divs")
    return [], "", "", "no_holdings_found [" + " ".join(tried) + "]"


ADAPTERS = {
    "Harvest ETFs": ("harvest", adapt_harvest),
    "Hamilton ETFs (Hamilton Capital Partners Inc.)": ("hamilton", adapt_hamilton),
    "First Trust": ("firsttrust", adapt_firsttrust),
    "Horizons ETFs Management": ("globalx", adapt_globalx),
}


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
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--delay", type=float, default=0.6)
    ap.add_argument("--reset", action="store_true")
    ap.add_argument("--probe", metavar="TICKER")
    args = ap.parse_args()

    session = get_session()
    resolver = TickerResolver(session)

    if args.probe:
        tick = args.probe.upper()
        for prov, (src, fn) in ADAPTERS.items():
            print(f"--- {prov} ({src}) ---")
            try:
                if src in ("firsttrust", "globalx", "harvest"):
                    h, as_of, cov, st = fn(session, tick, resolver)
                else:
                    h, as_of, cov, st = fn(session, tick)
                print(f"status={st} as_of={as_of!r} coverage={cov} "
                      f"holdings={len(h)}")
                for x in h[:6]:
                    print(f"  {x['holding_ticker'] or '?':12s} "
                          f"{x['weight_pct']:>8s}%  {x['holding_name'][:50]} "
                          f"[{x['ticker_source']}]")
            except Exception as exc:
                print(f"  ERROR {type(exc).__name__}: {exc}")
        resolver.flush()
        return 0

    if args.reset:
        for p in (OUT_CSV, PROGRESS_FILE):
            if p.exists():
                p.unlink()
        print("progress + full holdings CSV wiped")

    with open(ETF_LIST_CSV, newline="", encoding="utf-8") as f:
        etfs = list(csv.DictReader(f))
    print(f"{len(etfs)} ETFs in list; adapters cover "
          f"{sum(1 for e in etfs if e['provider'] in ADAPTERS)}")

    if args.test:
        wanted = set(TEST_TICKERS)
        etfs = [e for e in etfs if e["ticker"] in wanted]

    done = load_progress()
    todo = [e for e in etfs if f'{e["exchange"]}:{e["ticker"]}' not in done]
    if args.limit:
        todo = todo[:args.limit]
    print(f"{len(done)} already done, {len(todo)} to process", flush=True)

    new_file = not OUT_CSV.exists()
    out = open(OUT_CSV, "a", newline="", encoding="utf-8")
    writer = csv.DictWriter(out, fieldnames=OUT_COLUMNS)
    if new_file:
        writer.writeheader()
        out.flush()

    ok_count = fail_count = holding_rows = 0
    try:
        for i, etf in enumerate(todo, 1):
            key = f'{etf["exchange"]}:{etf["ticker"]}'
            fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            base = {
                "etf_ticker": etf["ticker"], "etf_exchange": etf["exchange"],
                "etf_name": etf["name"], "provider": etf["provider"],
                "fetched_at": fetched_at,
            }
            if etf["ticker"] in TERMINATED:
                fail_count += 1
                writer.writerow({**base, "coverage": "terminated",
                                 "status": "terminated"})
            elif etf["provider"] not in ADAPTERS:
                fail_count += 1
                writer.writerow({**base, "coverage": "no_adapter",
                                 "status": f"no_adapter [{etf['provider']}]"})
            else:
                src, fn = ADAPTERS[etf["provider"]]
                try:
                    if src in ("firsttrust", "globalx", "harvest"):
                        holdings, as_of, cov, status = fn(
                            session, etf["ticker"], resolver)
                    else:
                        holdings, as_of, cov, status = fn(
                            session, etf["ticker"])
                except Exception as exc:
                    holdings, as_of, cov, status = (
                        [], "", "", f"error: {type(exc).__name__}")
                row_base = {**base, "data_as_of": as_of, "source": src,
                            "coverage": cov}
                if holdings:
                    ok_count += 1
                    for h in holdings:
                        writer.writerow({**row_base, **h, "status": status})
                        holding_rows += 1
                else:
                    fail_count += 1
                    writer.writerow({**row_base, "holding_ticker": "",
                                     "holding_name": "", "weight_pct": "",
                                     "ticker_source": "", "status": status})
            out.flush()
            done.add(key)
            if i % 10 == 0:
                save_progress(done)
                print(f"[{i}/{len(todo)}] ... {ok_count} ok, "
                      f"{fail_count} without", flush=True)
            time.sleep(args.delay)
    finally:
        save_progress(done)
        resolver.flush()
        out.close()

    print(f"\nDONE: {ok_count} ETFs with holdings, {fail_count} without, "
          f"{holding_rows} holding rows total")
    print(f"holdings CSV: {OUT_CSV}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
