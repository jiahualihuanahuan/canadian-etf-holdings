#!/usr/bin/env python3
"""Re-parse saved Global X HTML with direct/underlying table attribution."""
import json, os, re

WORK = os.path.expanduser("~/workspace/your_files/canadian-etf-holdings/raw_extractions/globalx_missing")
HTML_DIR = os.path.join(WORK, "html")

ROW_RE = re.compile(
    r'<div[^>]*class="w-full flex justify-between border-b border-gray-lighter py-2 text-granite"[^>]*>\s*<p>(.*?)</p>\s*<p>(.*?)</p>',
    re.S)

def clean_name(s):
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\s+\d+(,\d+)*$", "", s).strip()  # footnote markers
    return s

def parse_file(ticker):
    path = os.path.join(HTML_DIR, f"{ticker}.html")
    html = open(path, encoding="utf-8", errors="replace").read()
    out = {"ticker": ticker, "fund_name": None, "as_of": None,
           "direct": [], "underlying": [], "notes": []}
    if len(html) < 10000:
        out["notes"].append("fetch failed / page too small")
        return out
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    if m:
        out["fund_name"] = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1))).strip()
    idx = html.find("Top Holdings")
    if idx < 0:
        out["notes"].append("no Top Holdings section")
        # detect 404
        if re.search(r"404|Page not found", html[:8000]):
            out["notes"].append("looks like 404")
        return out
    seg = html[idx:idx + 60000]
    m2 = re.search(r"As at\s+([A-Z][a-z]+ \d{1,2}, \d{4})", seg)
    if m2:
        out["as_of"] = m2.group(1)
    uh = seg.find("Top Underlying Holdings")
    # section headers
    events = []
    for m3 in re.finditer(r"<h3[^>]*>\s*(Long Positions|Short Positions)", seg):
        events.append((m3.start(), "sec", m3.group(1)))
    for m3 in ROW_RE.finditer(seg):
        name = clean_name(m3.group(1))
        wt = re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", m3.group(2)))
        events.append((m3.start(), "row", (name, wt)))
    events.sort()
    section = "long"
    for pos, kind, val in events:
        if kind == "sec":
            section = "long" if val == "Long Positions" else "short"
        else:
            name, wt = val
            mt = re.search(r"\(([A-Za-z0-9.\-^]+)\)\s*$", name)
            hticker = mt.group(1) if mt else ""
            if mt:
                name = name[:mt.start()].strip()
            wm = re.search(r"(-?[\d,]+\.?\d*)\s*%", wt)
            weight = wm.group(1).replace(",", "") if wm else ""
            if weight.startswith("-"):
                section = "short"
            table = "underlying" if (uh >= 0 and pos > uh) else "direct"
            out[table].append({"name": name, "ticker": hticker,
                               "weight": weight, "section": section})
    return out

def main():
    data = json.load(open(os.path.join(WORK, "parsed.json")))
    out = []
    for r in data:
        rec = parse_file(r["ticker"])
        rec["fetch"] = r.get("fetch")
        rec["is_bond_candidate"] = r.get("is_bond_candidate", False)
        out.append(rec)
    json.dump(out, open(os.path.join(WORK, "parsed2.json"), "w"), indent=1)
    # summary
    for r in out:
        ds = sum(float(h["weight"]) for h in r["direct"] if h["weight"])
        us = sum(float(h["weight"]) for h in r["underlying"] if h["weight"])
        print(f"{r['ticker']:<6} d={len(r['direct']):>2} dsum={ds:>7.2f}  u={len(r['underlying']):>2} usum={us:>7.2f}  asof={r['as_of']}  {(r['fund_name'] or '?')[:42]} {' '.join(r['notes'])}")

if __name__ == "__main__":
    main()
