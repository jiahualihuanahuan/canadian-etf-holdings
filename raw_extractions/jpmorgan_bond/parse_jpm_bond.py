#!/usr/bin/env python3
"""Parse JPMorgan JPIE + JPST daily holdings PDFs (fund-of-funds wrappers)
and merge direct holdings into the master CSV."""
import pymupdf, re, csv, os, glob

REPO = "/home/hatch/workspace/your_files/canadian-etf-holdings"
DL = "/home/hatch/workspace/browser_downloads/sess-2947907445"
AS_OF = "2026-09-18"
SOURCE = "am.jpmorgan.com"
PROVIDER = "J.P. Morgan Asset Management"

FUNDS = {
    "JPIE": ("JPMorgan Income Active ETF",
             sorted(glob.glob(DL + "/*15-JPMorgan-Income-Active-ETF*"))[0]),
    "JPST": ("JPMorgan US Ultra-Short Income Active ETF",
             sorted(glob.glob(DL + "/*16-JPMorgan-US-Ultra-Short*"))[0]),
}

SECID = re.compile(r"^((?=[A-Z0-9]*[A-Z])(?=[A-Z0-9]*[0-9])[A-Z0-9]{9}|CCTUSD|CCTCAD|USD|CASH)$")
PCT = re.compile(r"^(-?\d+(?:\.\d+)?)%$")

def is_anchor(lines, idx):
    if not SECID.match(lines[idx]):
        return False
    if lines[idx] == "USD":
        # disambiguate from the USD currency line: cash row is followed by its description
        return idx + 1 < len(lines) and lines[idx + 1] == "UNITED STATES DOLLAR"
    if lines[idx] == "CASH":
        # disambiguate from the CASH ticker line: secid is followed by the ticker line
        return idx + 1 < len(lines) and lines[idx + 1] == "CASH"
    return True

def smart_join(parts):
    out = ""
    for p in parts:
        if out and out.endswith("-"):
            out += p
        else:
            out = (out + " " + p).strip() if out else p
    return out

def parse_pdf(path):
    doc = pymupdf.open(path)
    lines = []
    for page in doc:
        lines += page.get_text().splitlines()
    lines = [l.strip() for l in lines if l.strip()]
    rows = []
    i = 0
    while i < len(lines):
        if not is_anchor(lines, i):
            i += 1
            continue
        secid = lines[i]
        j = i + 1
        desc_parts = []
        while j < len(lines) and lines[j] != "Physical":
            desc_parts.append(lines[j])
            j += 1
        j += 1  # skip 'Physical'
        k = j
        while k < len(lines) and not is_anchor(lines, k):
            k += 1
        pcts = [x for x in lines[j:k] if PCT.match(x)]
        weight = float(PCT.match(pcts[-1]).group(1)) if pcts else None
        if secid in ("CCTUSD", "CCTCAD"):
            ticker = secid
            name = "CURRENCY CONTRACT - %s FORWARD CONTRACTS" % secid[3:]
        elif secid == "USD":
            ticker = "USD"
            name = "UNITED STATES DOLLAR CASH OR CASH COLLATERAL"
        elif secid == "CASH":
            ticker = "CASH"
            name = "CASH OR CASH COLLATERAL"
        else:
            ticker = desc_parts[0]
            # description line(s) + security-type token (e.g. 'ETP')
            name = smart_join(desc_parts[1:3])
        rows.append({"secid": secid, "ticker": ticker, "name": name,
                     "weight": weight})
        i = k
    return rows

out_rows = []
for etf, (etf_name, path) in FUNDS.items():
    rows = parse_pdf(path)
    print("== %s (%s) -> %d rows" % (etf, os.path.basename(path)[:60], len(rows)))
    s = 0.0
    for r in rows:
        w = r["weight"]
        assert w is not None, "missing weight: %r" % r
        s += w
        print("   %-8s %-52s %s" % (r["ticker"], r["name"][:52], w))
    print("   NET-ASSETS SUM = %.4f%%" % s)
    for r in rows:
        out_rows.append([etf, etf_name, r["ticker"], r["name"],
                         r["weight"], AS_OF, SOURCE, PROVIDER])

with open("/tmp/jpm/jpm_bond_new.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["etf_ticker","etf_name","holding_ticker","holding_name",
                "weight_pct","as_of_date","source","provider"])
    w.writerows(out_rows)
print("wrote /tmp/jpm/jpm_bond_new.csv with %d data rows" % len(out_rows))
