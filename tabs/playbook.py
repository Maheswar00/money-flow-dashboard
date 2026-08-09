import streamlit as st

def render():
    st.subheader("📘 Capital Flow Playbook — How Smart Money Rotates")

    st.markdown("""
**Where this shows up in the dashboard:** #2 (Relative Strength) and #3 (Volume + Price) feed
the **Overview** verdict scores directly. #5 (Sector Rotation) and #6 (Macro/Liquidity) are on
**Overview**. #7 (Positioning) is the COT chart on **Evidence**. #8 (Bitcoin Dominance) is on
**Evidence** for Bitcoin/Ethereum. #4 (ETF Flows) is approximated via dollar-volume flow, not
real creation/redemption data — true flow data needs a paid vendor (ETF.com/Lipper/EPFR).
""")

    with st.expander("Open Playbook", expanded=True):
        st.markdown("""
## 1️⃣ Inter‑Market Analysis (Top‑Down View)

Big money moves between asset classes based on **risk, inflation, growth, and interest rates**.

### Common Capital Rotations
| Market Condition | Capital Moves Toward |
|------------------|----------------------|
| **Risk‑on (growth, optimism)** | Stocks → Crypto |
| **Inflation rising** | Commodities (oil, gold) |
| **Rate hikes** | Bonds → Cash → Value stocks |
| **Recession fear** | Bonds → Gold |
| **Liquidity expansion** | Crypto → Growth stocks |

📌 **Key insight:** Capital rarely disappears — **it rotates**.

---

## 2️⃣ Track Relative Strength (Where Money Is Winning)

Smart money chases **outperformance**, not narratives.

Compare:
- S&P 500 vs Gold  
- Nasdaq vs Dow  
- Bitcoin vs S&P 500  
- Energy stocks vs Market  

If **Asset A consistently outperforms Asset B**, capital is flowing into **A**.

📈 Tools:
- RS charts  
- Ratio charts (BTC/SPX, XLE/SPY)

---

## 3️⃣ Follow Volume + Price Together (Most Important)

Price alone lies.  
**Price + Volume reveals intent.**

**Accumulation signs:**
- Price rising with increasing volume  
- Breakouts on strong volume  
- Tight consolidation + volume expansion  

**Distribution signs:**
- Price flat but volume high  
- Sharp drops on heavy volume  

📌 **Big money cannot hide volume.**

---

## 4️⃣ Watch ETF Flows (Very Powerful)

Institutions move money via ETFs:

- SPY / QQQ → Stocks  
- GLD / SLV → Gold & Silver  
- USO → Oil  
- IBIT / GBTC → Bitcoin  
- TLT → Bonds  

➡️ **Net inflows = capital entering**  
➡️ **Net outflows = capital leaving**

---

## 5️⃣ Observe Sector Rotation (Inside Stocks)

Even if money stays in stocks, it rotates **between sectors**.

Typical sequence:
1. Defensive (Utilities, Staples)  
2. Cyclical (Industrials, Financials)  
3. Growth (Tech)  
4. Speculative (Small caps, Crypto)

📌 Early rotation often signals macro changes **before headlines**.

---

## 6️⃣ Monitor Macro Drivers (Capital Controllers)

Capital follows **policy and liquidity**, not opinions.

Track:
- Interest rates (10Y Treasury)  
- Central bank balance sheets  
- Inflation data (CPI)  
- USD Index (DXY)

Examples:
- **Falling DXY → Crypto & Commodities benefit**  
- **Rising rates → Growth stocks suffer**  
- **QE → Risk assets rise**

---

## 7️⃣ Use Sentiment & Positioning (Contrarian Clue)

- When **everyone is bullish → smart money exits**  
- When **everyone is bearish → smart money accumulates**

Tools:
- Fear & Greed Index  
- Commitment of Traders (COT)  
- Crypto funding rates  

---

## 8️⃣ Crypto‑Specific Capital Flow Signals

- **Bitcoin dominance ↑** → capital moving from altcoins → BTC  
- **Stablecoin supply ↑** → capital waiting to enter risk  
- **Exchange inflows ↑** → selling pressure  
- **Exchange outflows ↑** → accumulation  

---

## 9️⃣ Simple Weekly Capital Flow Checklist ✅

Ask:
- Which asset is outperforming others?  
- Where is volume expanding?  
- Which ETFs have net inflows?  
- What is the macro regime?  
- Is sentiment extreme?  

If **3–4 line up → that’s where capital is moving**.
""")
