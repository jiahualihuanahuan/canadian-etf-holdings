#!/usr/bin/env python3
"""Build partial universe-expansion CSV from topforeignstocks.com lists (RBC, TD, Lysander, Mackenzie)."""
import csv, re, os

HERE = os.path.dirname(os.path.abspath(__file__))
RBC_URL = "https://topforeignstocks.com/etf-lists/the-complete-list-of-rbc-etfs-trading-on-the-toronto-stock-exchange/"
TD_URL = "https://topforeignstocks.com/etf-lists/the-complete-list-of-td-etfs-trading-on-the-toronto-stock-exchange/"
LYS_URL = "https://topforeignstocks.com/the-complete-list-of-lysander-funds-etfs-trading-on-the-toronto-stock-exchange/"
MACK_URL = "https://topforeignstocks.com/the-complete-list-of-mackenzie-investments-etfs-trading-on-the-toronto-stock-exchange/"

ISHARES = "BlackRock/iShares"
RBC = "RBC Global Asset Management"
TD = "TD Asset Management"
LYS = "Lysander Funds"
MACK = "Mackenzie Investments"

# (ticker, name, provider, source) - tickers WITHOUT .TO suffix
DATA = """\
CBH|iShares 1-10 Year Laddered Corporate Bond Index ETF|{i}|{r}
CBO|iShares 1-5 Year Laddered Corporate Bond Index ETF|{i}|{r}
CDZ|iShares S&P/TSX Canadian Dividend Aristocrats Index ETF|{i}|{r}
CEW|iShares Equal Weight Banc & Lifeco ETF|{i}|{r}
CGL|iShares Gold Bullion ETF|{i}|{r}
CGL-C|iShares Gold Bullion ETF|{i}|{r}
CGR|iShares Global Real Estate Index ETF|{i}|{r}
CIF|iShares Global Infrastructure Index ETF|{i}|{r}
CLF|iShares 1-5 Year Laddered Government Bond Index ETF|{i}|{r}
CLG|iShares 1-10 Year Laddered Government Bond Index ETF|{i}|{r}
CMR|iShares Premium Money Market ETF|{i}|{r}
COW|iShares Global Agriculture Index ETF|{i}|{r}
CPD|iShares S&P/TSX Canadian Preferred Share Index ETF|{i}|{r}
CUD|iShares US Dividend Growers Index ETF (CAD-Hedged)|{i}|{r}
CVD|iShares Convertible Bond Index ETF|{i}|{r}
CWW|iShares Global Water Index ETF|{i}|{r}
CYH|iShares Global Monthly Dividend Index ETF (CAD-Hedged)|{i}|{r}
FIE|iShares Canadian Financial Monthly Income ETF|{i}|{r}
GBAL|iShares ESG Balanced ETF Portfolio|{i}|{r}
GCNS|iShares ESG Conservative Balanced ETF Portfolio|{i}|{r}
GEQT|iShares ESG Equity ETF Portfolio|{i}|{r}
GGRO|iShares ESG Growth ETF Portfolio|{i}|{r}
RBNK|RBC Canadian Bank Yield Index ETF|{b}|{r}
RBO|RBC 1-5 Year Laddered Canadian Corporate Bond ETF|{b}|{r}
RCD|RBC Quant Canadian Dividend Leaders ETF|{b}|{r}
RCDC|RBC Canadian Dividend Covered Call ETF|{b}|{r}
RDBH|RBC U.S. Discount Bond (CAD Hedged) ETF|{b}|{r}
RGQN|RBC Target 2025 Canadian Government Bond ETF|{b}|{r}
RGQO|RBC Target 2026 Canadian Government Bond ETF|{b}|{r}
RGQP|RBC Target 2027 Canadian Government Bond ETF|{b}|{r}
RGQQ|RBC Target 2028 Canadian Government Bond ETF|{b}|{r}
RGQR|RBC Target 2029 Canadian Government Bond ETF|{b}|{r}
RGQS|RBC Target 2030 Canadian Government Bond ETF|{b}|{r}
RID|RBC Quant EAFE Dividend Leaders ETF|{b}|{r}
RID-U|RBC Quant EAFE Dividend Leaders ETF|{b}|{r}
RIDH|RBC Quant EAFE Dividend Leaders (CAD Hedged) ETF|{b}|{r}
RLB|RBC 1-5 Year Laddered Canadian Bond ETF|{b}|{r}
RPD|RBC Quant European Dividend Leaders ETF|{b}|{r}
RPD-U|RBC Quant European Dividend Leaders ETF|{b}|{r}
RPDH|RBC Quant European Dividend Leaders (CAD Hedged) ETF|{b}|{r}
RPF|RBC Canadian Preferred Share ETF|{b}|{r}
RPSB|RBC PH&N Short Term Canadian Bond ETF|{b}|{r}
RQN|RBC Target 2025 Canadian Corporate Bond Index ETF|{b}|{r}
RQO|RBC Target 2026 Canadian Corporate Bond Index ETF|{b}|{r}
RQP|RBC Target 2027 Canadian Corporate Bond Index ETF|{b}|{r}
RQQ|RBC Target 2028 Canadian Corporate Bond Index ETF|{b}|{r}
RQR|RBC Target 2029 Canadian Corporate Bond Index ETF|{b}|{r}
RQS|RBC Target 2030 Canadian Corporate Bond Index ETF|{b}|{r}
RUBH|RBC U.S. Banks Yield (CAD Hedged) Index ETF|{b}|{r}
RUBY|RBC U.S. Banks Yield Index ETF|{b}|{r}
RUBY-U|RBC U.S. Banks Yield Index ETF|{b}|{r}
RUD|RBC Quant U.S. Dividend Leaders ETF|{b}|{r}
RUD-U|RBC Quant U.S. Dividend Leaders ETF|{b}|{r}
RUDB|RBC U.S. Discount Bond ETF|{b}|{r}
RUDB-U|RBC U.S. Discount Bond ETF|{b}|{r}
RUDC|RBC U.S. Dividend Covered Call ETF|{b}|{r}
RUDC-U|RBC U.S. Dividend Covered Call ETF|{b}|{r}
RUDH|RBC Quant U.S. Dividend Leaders (CAD Hedged) ETF|{b}|{r}
RUQN|RBC Target 2025 U.S. Corporate Bond ETF|{b}|{r}
RUQN-U|RBC Target 2025 U.S. Corporate Bond ETF|{b}|{r}
RUQO|RBC Target 2026 U.S. Corporate Bond ETF|{b}|{r}
RUQO-U|RBC Target 2026 U.S. Corporate Bond ETF|{b}|{r}
RUQP|RBC Target 2027 U.S. Corporate Bond ETF|{b}|{r}
RUQP-U|RBC Target 2027 U.S. Corporate Bond ETF|{b}|{r}
RUQQ|RBC Target 2028 U.S. Corporate Bond ETF|{b}|{r}
RUQQ-U|RBC Target 2028 U.S. Corporate Bond ETF|{b}|{r}
RUQR|RBC Target 2029 U.S. Corporate Bond ETF|{b}|{r}
RUQR-U|RBC Target 2029 U.S. Corporate Bond ETF|{b}|{r}
RUQS|RBC Target 2030 U.S. Corporate Bond ETF|{b}|{r}
RUQS-U|RBC Target 2030 U.S. Corporate Bond ETF|{b}|{r}
RUSB|RBC Short Term U.S. Corporate Bond ETF|{b}|{r}
RUSB-U|RBC Short Term U.S. Corporate Bond ETF|{b}|{r}
RXD|RBC Quant Emerging Markets Dividend Leaders ETF|{b}|{r}
RXD-U|RBC Quant Emerging Markets Dividend Leaders ETF|{b}|{r}
SVR|iShares Silver Bullion ETF|{i}|{r}
SVR.C|iShares Silver Bullion ETF|{i}|{r}
XAD|iShares U.S. Aerospace & Defense Index ETF|{i}|{r}
XAGG|iShares U.S. Aggregate Bond Index ETF|{i}|{r}
XAGG-U|iShares U.S. Aggregate Bond Index ETF|{i}|{r}
XAGH|iShares U.S. Aggregate Bond Index ETF (CAD-Hedged)|{i}|{r}
XAW|iShares Core MSCI All Country World ex Canada Index ETF|{i}|{r}
XAW-U|iShares Core MSCI All Country World ex Canada Index ETF|{i}|{r}
XBAL|iShares Core Balanced ETF Portfolio|{i}|{r}
XBB|iShares Core Canadian Universe Bond Index ETF|{i}|{r}
XBM|iShares S&P/TSX Global Base Metals Index ETF|{i}|{r}
XCB|iShares Core Canadian Corporate Bond Index ETF|{i}|{r}
XCBG|iShares ESG Advanced Canadian Corporate Bond Index ETF|{i}|{r}
XCBU|iShares U.S. IG Corporate Bond Index ETF|{i}|{r}
XCBU-U|iShares U.S. IG Corporate Bond Index ETF|{i}|{r}
XCD|iShares S&P Global Consumer Discretionary Index ETF (CAD-Hedged)|{i}|{r}
XCG|iShares Canadian Growth Index ETF|{i}|{r}
XCH|iShares China Index ETF|{i}|{r}
XCHP|iShares Semiconductor Index ETF|{i}|{r}
XCLN|iShares Global Clean Energy Index ETF|{i}|{r}
XCNS|iShares Core Conservative Balanced ETF Portfolio|{i}|{r}
XCS|iShares S&P/TSX SmallCap Index ETF|{i}|{r}
XCSR|iShares ESG Advanced MSCI Canada Index ETF|{i}|{r}
XCV|iShares Canadian Value Index ETF|{i}|{r}
XDG|iShares Core MSCI Global Quality Dividend Index ETF|{i}|{r}
XDG-U|iShares Core MSCI Global Quality Dividend Index ETF|{i}|{r}
XDGH|iShares Core MSCI Global Quality Dividend Index ETF (CAD-Hedged)|{i}|{r}
XDIV|iShares Core MSCI Canadian Quality Dividend Index ETF|{i}|{r}
XDNA|iShares Genomics Immunology and Healthcare Index ETF|{i}|{r}
XDRV|iShares Global Electric and Autonomous Vehicles Index ETF|{i}|{r}
XDSR|iShares ESG Advanced MSCI EAFE Index ETF|{i}|{r}
XDU|iShares Core MSCI US Quality Dividend Index ETF|{i}|{r}
XDU-U|iShares Core MSCI US Quality Dividend Index ETF|{i}|{r}
XDUH|iShares Core MSCI US Quality Dividend Index ETF (CAD-Hedged)|{i}|{r}
XDV|iShares Canadian Select Dividend Index ETF|{i}|{r}
XEB|iShares J.P. Morgan USD Emerging Markets Bond Index ETF (CAD-Hedged)|{i}|{r}
XEC|iShares Core MSCI Emerging Markets IMI Index ETF|{i}|{r}
XEC-U|iShares Core MSCI Emerging Markets IMI Index ETF|{i}|{r}
XEF|iShares Core MSCI EAFE IMI Index ETF|{i}|{r}
XEF-U|iShares Core MSCI EAFE IMI Index ETF|{i}|{r}
XEG|iShares S&P/TSX Capped Energy Index ETF|{i}|{r}
XEH|iShares MSCI Europe IMI Index ETF (CAD-Hedged)|{i}|{r}
XEI|iShares S&P/TSX Composite High Dividend Index ETF|{i}|{r}
XEM|iShares MSCI Emerging Markets Index ETF|{i}|{r}
XEMC|iShares MSCI Emerging Markets ex China Index ETF|{i}|{r}
XEN|iShares Jantzi Social Index ETF|{i}|{r}
XEQT|iShares Core Equity ETF Portfolio|{i}|{r}
XESG|iShares ESG Aware MSCI Canada Index ETF|{i}|{r}
XETM|iShares S&P/TSX Energy Transition Materials Index ETF|{i}|{r}
XEU|iShares MSCI Europe IMI Index ETF|{i}|{r}
XEXP|iShares Exponential Technologies Index ETF|{i}|{r}
XFH|iShares Core MSCI EAFE IMI Index ETF (CAD-Hedged)|{i}|{r}
XFLB|iShares Core Canadian 15+ Year Federal Bond Index ETF|{i}|{r}
XFN|iShares S&P/TSX Capped Financials Index ETF|{i}|{r}
XFR|iShares Floating Rate Index ETF|{i}|{r}
XGB|iShares Core Canadian Government Bond Index ETF|{i}|{r}
XGD|iShares S&P/TSX Global Gold Index ETF|{i}|{r}
XGI|iShares S&P Global Industrials Index ETF(CAD-Hedged)|{i}|{r}
XGRO|iShares Core Growth ETF Portfolio|{i}|{r}
XHAK|iShares Cybersecurity and Tech Index ETF|{i}|{r}
XHB|iShares Canadian HYBrid Corporate Bond Index ETF|{i}|{r}
XHC|iShares Global Healthcare Index ETF (CAD-Hedged)|{i}|{r}
XHD|iShares U.S. High Dividend Equity Index ETF (CAD-Hedged)|{i}|{r}
XHU|iShares U.S. High Dividend Equity Index ETF|{i}|{r}
XHY|iShares U.S. High Yield Bond Index ETF (CAD-Hedged)|{i}|{r}
XIC|iShares Core S&P/TSX Capped Composite Index ETF|{i}|{r}
XID|iShares India Index ETF|{i}|{r}
XIG|iShares U.S. IG Corporate Bond Index ETF (CAD-Hedged)|{i}|{r}
XIGS|iShares 1-5 Year U.S. IG Corporate Bond Index ETF (CAD-Hedged)|{i}|{r}
XIN|iShares MSCI EAFE Index ETF (CAD-Hedged)|{i}|{r}
XINC|iShares Core Income Balanced ETF Portfolio|{i}|{r}
XIT|iShares S&P/TSX Capped Information Technology Index ETF|{i}|{r}
XIU|iShares S&P/TSX 60 Index ETF|{i}|{r}
XLB|iShares Core Canadian Long Term Bond Index ETF|{i}|{r}
XMA|iShares S&P/TSX Capped Materials Index ETF|{i}|{r}
XMC|iShares S&P U.S. Mid-Cap Index ETF|{i}|{r}
XMC-U|iShares S&P U.S. Mid-Cap Index ETF|{i}|{r}
XMD|iShares S&P/TSX Completion Index ETF|{i}|{r}
XMH|iShares S&P U.S. Mid-Cap Index ETF (CAD-Hedged)|{i}|{r}
XMI|iShares MSCI Min Vol EAFE Index ETF|{i}|{r}
XML|iShares MSCI Min Vol EAFE Index ETF (CAD-Hedged)|{i}|{r}
XMM|iShares MSCI Min Vol Emerging Markets Index ETF|{i}|{r}
XMS|iShares MSCI Min Vol USA Index ETF (CAD-Hedged)|{i}|{r}
XMTM|iShares MSCI USA Momentum Factor Index ETF|{i}|{r}
XMU|iShares MSCI Min Vol USA Index ETF|{i}|{r}
XMU-U|iShares MSCI Min Vol USA Index ETF|{i}|{r}
XMV|iShares MSCI Min Vol Canada Index ETF|{i}|{r}
XMW|iShares MSCI Min Vol Global Index ETF|{i}|{r}
XMY|iShares MSCI Min Vol Global Index ETF (CAD-Hedged)|{i}|{r}
XPF|iShares S&P/TSX North American Preferred Stock Index ETF (CAD-Hedged)|{i}|{r}
XQB|iShares High Quality Canadian Bond Index ETF|{i}|{r}
XQLT|iShares MSCI USA Quality Factor Index ETF|{i}|{r}
XQQ|iShares NASDAQ 100 Index ETF (CAD-Hedged)|{i}|{r}
XQQU|iShares NASDAQ 100 Index ETF|{i}|{r}
XQQU-U|iShares NASDAQ 100 Index ETF|{i}|{r}
XRB|iShares Canadian Real Return Bond Index ETF|{i}|{r}
XRE|iShares S&P/TSX Capped REIT Index ETF|{i}|{r}
XSAB|iShares ESG Aware Canadian Aggregate Bond Index ETF|{i}|{r}
XSB|iShares Core Canadian Short Term Bond Index ETF|{i}|{r}
XSC|iShares Conservative Short Term Strategic Fixed Income ETF|{i}|{r}
XSE|iShares Conservative Strategic Fixed Income ETF|{i}|{r}
XSEA|iShares ESG Aware MSCI EAFE Index ETF|{i}|{r}
XSEM|iShares ESG Aware MSCI Emerging Markets Index ETF|{i}|{r}
XSH|iShares Core Canadian Short Term Corporate Bond Index ETF|{i}|{r}
XSHG|iShares ESG Advanced 1-5 Year Canadian Corporate Bond Index ETF|{i}|{r}
XSHU|iShares 1-5 Year U.S. IG Corporate Bond Index ETF|{i}|{r}
XSHU-U|iShares 1-5 Year U.S. IG Corporate Bond Index ETF|{i}|{r}
XSI|iShares Short Term Strategic Fixed Income ETF|{i}|{r}
XSMC|iShares S&P U.S. Small-Cap Index ETF|{i}|{r}
XSMH|iShares S&P U.S. Small-Cap Index ETF (CAD-Hedged)|{i}|{r}
XSP|iShares Core S&P 500 Index ETF (CAD-Hedged)|{i}|{r}
XSPC|iShares S&P 500 3% Capped Index ETF (CAD-Hedged)|{i}|{r}
XST|iShares S&P/TSX Capped Consumer Staples Index ETF|{i}|{r}
XSTB|iShares ESG Aware Canadian Short Term Bond Index ETF|{i}|{r}
XSTH|iShares 0-5 Year TIPS Bond Index ETF (CAD-Hedged)|{i}|{r}
XSTP|iShares 0-5 Year TIPS Bond Index ETF|{i}|{r}
XSTP-U|iShares 0-5 Year TIPS Bond Index ETF|{i}|{r}
XSU|iShares U.S. Small Cap Index ETF (CAD-Hedged)|{i}|{r}
XSUS|iShares ESG Aware MSCI USA Index ETF|{i}|{r}
XTLH|iShares 20+ Year U.S. Treasury Bond Index ETF (CAD-Hedged)|{i}|{r}
XTLT|iShares 20+ Year U.S. Treasury Bond Index ETF|{i}|{r}
XTLT-U|iShares 20+ Year U.S. Treasury Bond Index ETF|{i}|{r}
XTR|iShares Diversified Monthly Income ETF|{i}|{r}
XUH|iShares Core S&P U.S. Total Market Index ETF (CAD-Hedged)|{i}|{r}
XUS|iShares Core S&P 500 Index ETF|{i}|{r}
XUS-U|iShares Core S&P 500 Index ETF|{i}|{r}
XUSC|iShares S&P 500 3% Capped Index ETF|{i}|{r}
XUSC-U|iShares S&P 500 3% Capped Index ETF|{i}|{r}
XUSF|iShares S&P U.S. Financials Index ETF|{i}|{r}
XUSR|iShares ESG Advanced MSCI USA Index ETF|{i}|{r}
XUT|iShares S&P/TSX Capped Utilities Index ETF|{i}|{r}
XUU|iShares Core S&P U.S. Total Market Index ETF|{i}|{r}
XUU-U|iShares Core S&P U.S. Total Market Index ETF|{i}|{r}
XVLU|iShares MSCI USA Value Factor Index ETF|{i}|{r}
XWD|iShares MSCI World Index ETF|{i}|{r}
TBAL|TD Balanced ETF Portfolio|{t}|{d}
TCON|TD Conservative ETF Portfolio|{t}|{d}
TGRO|TD Growth ETF Portfolio|{t}|{d}
TCSH|TD Cash Management ETF|{t}|{d}
TUSD-U|TD U.S. Cash Management ETF|{t}|{d}
TBNK|TD Canadian Bank Dividend Index ETF|{t}|{d}
TCLV|TD Q Canadian Low Volatility ETF|{t}|{d}
TDNA|TD North American Dividend Fund|{t}|{d}
TDOC|TD Global Healthcare Leaders Index ETF|{t}|{d}
TDOC-U|TD Global Healthcare Leaders Index ETF|{t}|{d}
TEC|TD Global Technology Leaders Index ETF|{t}|{d}
TEC-U|TD Global Technology Leaders Index ETF|{t}|{d}
TECI|TD Global Technology Innovators Index ETF|{t}|{d}
TECX|TD Global Technology Leaders CAD Hedged Index ETF|{t}|{d}
TEQT|TD All-Equity ETF Portfolio|{t}|{d}
TGED|TD Active Global Enhanced Dividend ETF|{t}|{d}
TGED-U|TD Active Global Enhanced Dividend ETF|{t}|{d}
TGGR|TD Active Global Equity Growth ETF|{t}|{d}
TGRE|TD Active Global Real Estate Equity ETF|{t}|{d}
THE|TD International Equity CAD Hedged Index ETF|{t}|{d}
THU|TD U.S. Equity CAD Hedged Index ETF|{t}|{d}
TILV|TD Q International Low Volatility ETF|{t}|{d}
TINF|TD Active Global Infrastructure Equity ETF|{t}|{d}
TPE|TD International Equity Index ETF|{t}|{d}
TPU|TD U.S. Equity Index ETF|{t}|{d}
TPU.U|TD U.S. Equity Index ETF|{t}|{d}
TQCD|TD Q Canadian Dividend ETF|{t}|{d}
TQGD|TD Q Global Dividend ETF|{t}|{d}
TQGM|TD Q Global Multifactor ETF|{t}|{d}
TQSM|TD Q U.S. Small-Mid-Cap Equity ETF|{t}|{d}
TQSM-U|TD Q U.S. Small-Mid-Cap Equity ETF|{t}|{d}
TTP|TD Canadian Equity Index ETF|{t}|{d}
TUED|TD Active U.S. Enhanced Dividend ETF|{t}|{d}
TUED-U|TD Active U.S. Enhanced Dividend ETF|{t}|{d}
TUEX|TD Active U.S. Enhanced Dividend CAD Hedged ETF|{t}|{d}
TULV|TD Q U.S. Low Volatility ETF|{t}|{d}
TBCF|TD Target 2026 Investment Grade Bond ETF|{t}|{d}
TBCG|TD Target 2027 Investment Grade Bond ETF|{t}|{d}
TBCH|TD Target 2028 Investment Grade Bond ETF|{t}|{d}
TBCI|TD Target 2029 Investment Grade Bond ETF|{t}|{d}
TBCJ|TD Target 2030 Investment Grade Bond ETF|{t}|{d}
TBUF-U|TD Target 2026 U.S. Investment Grade Bond ETF|{t}|{d}
TBUG-U|TD Target 2027 U.S. Investment Grade Bond ETF|{t}|{d}
TCLB|TD Canadian Long Term Federal Bond ETF|{t}|{d}
TCSB|TD Select Short Term Corporate Bond Ladder ETF|{t}|{d}
TDB|TD Canadian Aggregate Bond Index ETF|{t}|{d}
TGFI|TD Active Global Income ETF|{t}|{d}
TUHY|TD Active U.S. High Yield Bond ETF|{t}|{d}
TULB|TD U.S. Long Term Treasury Bond ETF|{t}|{d}
TUSB|TD Select U.S. Short Term Corporate Bond Ladder ETF|{t}|{d}
TUSB-U|TD Select U.S. Short Term Corporate Bond Ladder ETF|{t}|{d}
TPRF|TD Active Preferred Share ETF|{t}|{d}
PR|Lysander-Slater Preferred Share ActivETF|{l}|{u}
MKB|Mackenzie Core Plus Canadian Fixed Income ETF|{m}|{k}
MGB|Mackenzie Core Plus Global Fixed Income ETF|{m}|{k}
MFT|Mackenzie Floating Rate Income ETF|{m}|{k}
MXU|Mackenzie Maximum Diversification All World Developed ex North America Index ETF|{m}|{k}
MWD|Mackenzie Maximum Diversification All World Developed Index ETF|{m}|{k}
MKC|Mackenzie Maximum Diversification Canada Index ETF|{m}|{k}
MEU|Mackenzie Maximum Diversification Developed Europe Index ETF|{m}|{k}
MUB|Mackenzie Unconstrained Bond ETF|{m}|{k}
""".format(i=ISHARES, b=RBC, t=TD, d=TD_URL, r=RBC_URL, l=LYS, u=LYS_URL, m=MACK, k=MACK_URL)


def base(ticker):
    t = ticker.strip().upper()
    t = re.sub(r"\.TO$", "", t)
    t = re.sub(r"[.\-]?(U|B|F|C)$", "", t)
    return t


def main():
    existing = set()
    with open(os.path.join(HERE, "canadian_etf_list.csv")) as f:
        for row in csv.DictReader(f):
            t = (row.get("ticker") or "").strip()
            if t and t.lower() != "ticker":
                existing.add(base(t))
    out = []
    seen = set()
    for line in DATA.strip().split("\n"):
        ticker, name, provider, source = line.split("|")
        if base(ticker) in existing:
            continue
        if ticker in seen:
            continue
        seen.add(ticker)
        out.append({"ticker": ticker, "etf_name": name, "provider": provider, "source": source})
    path = os.path.join(HERE, "universe_expansion_tfs.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["ticker", "etf_name", "provider", "source"])
        w.writeheader()
        w.writerows(out)
    print(f"wrote {len(out)} new ETFs to {path}")


if __name__ == "__main__":
    main()
