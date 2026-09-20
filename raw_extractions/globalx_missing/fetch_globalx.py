#!/usr/bin/env python3
"""Fetch Global X Canada fund pages and parse Top Holdings tables.

Saves raw HTML to raw_extractions/globalx_missing/html/ and writes a parsed
intermediate JSON. Completeness is decided later; this script only fetches+parses.
"""
import csv, json, os, re, sys, time
import requests

WORK = os.path.expanduser("~/workspace/your_files/canadian-etf-holdings/raw_extractions/globalx_missing")
HTML_DIR = os.path.join(WORK, "html")
os.makedirs(HTML_DIR, exist_ok=True)

TICKERS = """AGCC AIQ BCCC BCCL BITI BKCC BKCL BNKL CANL CFOD CFOU CHPS CHQQ CMCC CMCL
CNCC CNCL CNDD CNDI CNDU CNDX COMX COPP CPCC DIVY ENCC ENCL EQCC EQCL ETHI GDXD GDXU
GLCC GLCL GLDD GLDU GLDX GRCC HAC HAL HAZ HBAL HBGD HBNK HCON HCRE HEQL HEQT HEWB
HGRW HGY HLIT HMMJ HQD HSAV HSH HSUV HUC HUG HULC HUN HURA HUZ HXCN HXDM HXE HXEM
HXF HXH HXX INOC MART MEDX MTRX NRGD NRGU NRGY NYSX ORBX PAVE PPLN QQCC QQCL QQI
QQQL QQQX QQU RBOT REIT RING RNCC RNCL RSCC RSCL RSSX SAFE SCND SHLD SLVD SLVU SLVX
SOXL SOXS SPXD SPXI SPXU SQQQ SSPX SVCC SVCL TCND TOKN TQQQ TSPX TTTX UBNK UMRT
URCC USCC USCL USSL USSX UTIL""".split()
BOND_CANDIDATES = "CASH CBIL UBIL UCSH LPAY MPAY PAYL PAYM PAYS SPAY STLT TTLT VOLX".split()

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}

def fetch(ticker):
    url = f"https://www.globalx.ca/product/{ticker.lower()}"
    path = os.path.join(HTML_DIR, f"{ticker}.html")
    if os.path.exists(path) and os.path.getsize(path) > 10000:
        return open(path, encoding="utf-8", errors="replace").read(), "cached"
    try:
        r = requests.get(url, headers=UA, timeout=45, allow_redirects=True)
        html = r.text
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        return html, f"http-{r.status_code}"
    except Exception as e:
        return "", f"error:{e}"

def parse(ticker, html):
    out = {"ticker": ticker, "fund_name": None, "as_of": None, "holdings": [],
           "sections": [], "page_ok": False, "notes": []}
    if not html or len(html) < 10000:
        out["notes"].append("page too small / fetch failed")
        return out
    if "Page not found" in html and "404" in html[:5000]:
        out["notes"].append("possible 404")
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    if m:
        out["fund_name"] = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        out["fund_name"] = re.sub(r"\s+", " ", out["fund_name"])
    idx = html.find("Top Holdings")
    if idx < 0:
        out["notes"].append("no Top Holdings section")
        # check if main content rendered at all
        out["page_ok"] = 'id="holdings"' in html or 'holdings-tab' in html
        return out
    out["page_ok"] = True
    seg = html[idx:idx + 40000]
    m2 = re.search(r"As at\s+([A-Z][a-z]+ \d{1,2}, \d{4})", seg)
    if m2:
        out["as_of"] = m2.group(1)
    # find section headers and rows in order
    tokens = []
    for m3 in re.finditer(r"<h3[^>]*>\s*(Long Positions|Short Positions)", seg):
        tokens.append((m3.start(), "section", m3.group(1)))
    for m3 in re.finditer(
        r'<div[^>]*class="w-full flex justify-between border-b border-gray-lighter py-2 text-granite"[^>]*>\s*<p>(.*?)</p>\s*<p>(.*?)</p>',
        seg, re.S):
        name = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m3.group(1))).strip()
        wt = re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", m3.group(2))).strip()
        tokens.append((m3.start(), "row", (name, wt)))
    tokens.sort()
    section = "long"
    for _, kind, val in tokens:
        if kind == "section":
            section = "long" if val == "Long Positions" else "short"
            if val not in out["sections"]:
                out["sections"].append(val)
        else:
            name, wt = val
            # strip footnote markers like trailing "1,2" or "1"
            name = re.sub(r"\s+\d+(,\d+)*$", "", name).strip()
            # split "(TICKER)" suffix
            mt = re.search(r"\(([A-Za-z0-9.\-^]+)\)\s*$", name)
            hticker = mt.group(1) if mt else ""
            if mt:
                name = name[:mt.start()].strip()
            wm = re.search(r"(-?[\d,]+\.?\d*)\s*%", wt)
            weight = wm.group(1).replace(",", "") if wm else ""
            if weight.startswith("-"):
                section = "short"
            out["holdings"].append({"name": name, "ticker": hticker,
                                    "weight": weight, "section": section})
    return out

def main():
    all_t = TICKERS + [b for b in BOND_CANDIDATES if b not in TICKERS]
    results = []
    for i, t in enumerate(all_t):
        html, how = fetch(t)
        rec = parse(t, html)
        rec["fetch"] = how
        rec["is_bond_candidate"] = t in BOND_CANDIDATES
        results.append(rec)
        n = len(rec["holdings"])
        print(f"[{i+1}/{len(all_t)}] {t}: {how} rows={n} asof={rec['as_of']} name={(rec['fund_name'] or '?')[:50]} {' '.join(rec['notes'])}", flush=True)
        time.sleep(1.2)
    with open(os.path.join(WORK, "parsed.json"), "w") as f:
        json.dump(results, f, indent=1)
    print("saved parsed.json")

if __name__ == "__main__":
    main()
