import streamlit as st
import requests
import datetime
import pandas as pd
import json
import os

# Constants
INDEX_INFO = {
    "NIFTY": {"symbol": "NIFTY", "expiry_weekday": 3},
    "BANKNIFTY": {"symbol": "BANKNIFTY", "expiry_weekday": 3},
    "FINNIFTY": {"symbol": "FINNIFTY", "expiry_weekday": 1},
}
ZERO_PRICE_MAX = 5
OTM_STRIKE_OFFSET = 200
API_URL = "https://www.nseindia.com/api/option-chain-indices?symbol={}"

# Page config
st.set_page_config(page_title="Zero Hero Dashboard", layout="wide")

# Fetch option chain data
def get_option_chain(index):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Referer": f"https://www.nseindia.com/option-chain",
    }
    session = requests.Session()
    session.get("https://www.nseindia.com", headers=headers)
    url = API_URL.format(INDEX_INFO[index]['symbol'])
    resp = session.get(url, headers=headers)
    if resp.status_code != 200:
        st.error("Failed to fetch option chain data. Try again later.")
        return None
    return resp.json()

# Calculate expiry date
def get_expiry_date(index):
    today = datetime.date.today()
    weekday = today.weekday()
    expiry_weekday = INDEX_INFO[index]['expiry_weekday']
    days_ahead = expiry_weekday - weekday if weekday <= expiry_weekday else 7 - weekday + expiry_weekday
    expiry = today + datetime.timedelta(days=days_ahead)
    return expiry

# Confidence score
def signal_confidence(signal, records, underlying):
    strike = signal['Strike']
    ltp = signal['LTP']
    oi = signal['OI']
    volume = signal['Volume']
    expiry = get_expiry_date(signal['Index'])
    today = datetime.date.today()
    days_to_expiry = (expiry - today).days

    proximity_factor = max(0, 1 - abs(strike - underlying) / (OTM_STRIKE_OFFSET * 2))
    oi_factor = min(1, oi / 5000)
    volume_factor = min(1, volume / 500)
    expiry_factor = 1 if days_to_expiry == 0 else 0.5 if days_to_expiry == 1 else 0.2

    score = (0.3 * proximity_factor) + (0.3 * oi_factor) + (0.2 * volume_factor) + (0.2 * expiry_factor)
    conf_pct = round(score * 100, 1)
    return conf_pct

# Analyze signals
def analyze_zero_hero(records, index):
    underlying = records['underlyingValue']
    data = records['data']
    ce_zero = []
    pe_zero = []
    for rec in data:
        strike = rec['strikePrice']
        if 'CE' in rec and rec['CE']['lastPrice'] <= ZERO_PRICE_MAX and strike > underlying + OTM_STRIKE_OFFSET:
            ce_signal = {
                "Index": index,
                "Type": "CE",
                "Strike": strike,
                "LTP": rec['CE']['lastPrice'],
                "OI": rec['CE']['openInterest'],
                "Volume": rec['CE']['totalTradedVolume'],
            }
            ce_signal['Confidence (%)'] = signal_confidence(ce_signal, records, underlying)
            ce_zero.append(ce_signal)
        if 'PE' in rec and rec['PE']['lastPrice'] <= ZERO_PRICE_MAX and strike < underlying - OTM_STRIKE_OFFSET:
            pe_signal = {
                "Index": index,
                "Type": "PE",
                "Strike": strike,
                "LTP": rec['PE']['lastPrice'],
                "OI": rec['PE']['openInterest'],
                "Volume": rec['PE']['totalTradedVolume'],
            }
            pe_signal['Confidence (%)'] = signal_confidence(pe_signal, records, underlying)
            pe_zero.append(pe_signal)
    return pd.DataFrame(ce_zero + pe_zero)

# Save performance
def save_performance(signal, result):
    stats_file = "zerohero_stats.json"
    if os.path.exists(stats_file):
        with open(stats_file, "r") as f:
            stats = json.load(f)
    else:
        stats = []
    signal_entry = dict(signal)
    signal_entry["Result"] = result
    signal_entry["Date"] = str(datetime.date.today())
    stats.append(signal_entry)
    with open(stats_file, "w") as f:
        json.dump(stats, f)

# Load performance
def load_performance():
    stats_file = "zerohero_stats.json"
    if os.path.exists(stats_file):
        with open(stats_file, "r") as f:
            stats = json.load(f)
        return pd.DataFrame(stats)
    return pd.DataFrame([])

# Tabs
tab1, tab2 = st.tabs(["📈 Signals & Analysis", "📊 Performance Stats"])

# Tab 1: Signal Analysis
with tab1:
    st.title("Zero Hero Options Dashboard (NSE Indices)")
    index = st.selectbox("Select Index", list(INDEX_INFO.keys()))
    show_all = st.checkbox("Show All Options", value=False)
    st.write(f"**Expiry Date:** {get_expiry_date(index)}")
    records = get_option_chain(index)
    if records:
        underlying = records['records']['underlyingValue']
        st.write(f"**Current {index} Spot:** {underlying}")
        st.subheader("Zero Hero Opportunities")
        zero_df = analyze_zero_hero(records['records'], index)
        if not zero_df.empty:
            st.dataframe(zero_df, use_container_width=True)
            st.markdown("#### Mark Signal Result")
            for i, row in zero_df.iterrows():
                cols = st.columns([4, 1, 1])
                cols[0].write(f"{row['Type']} {row['Strike']} @ {row['LTP']} | Confidence: {row['Confidence (%)']}%")
                if cols[1].button(f"Success {i}", key=f"s{i}"):
                    save_performance(row, "Success")
                    st.success(f"Marked as Success: {row['Type']} {row['Strike']}")
                if cols[2].button(f"Fail {i}", key=f"f{i}"):
                    save_performance(row, "Fail")
                    st.error(f"Marked as Fail: {row['Type']} {row['Strike']}")
        else:
            st.info("No Zero Hero options found at this moment.")

        if show_all:
            st.subheader("Full Option Chain (Sorted by ATM Distance)")
            data = []
            for rec in records['records']['data']:
                strike = rec['strikePrice']
                ce_ltp = rec['CE']['lastPrice'] if 'CE' in rec else None
                pe_ltp = rec['PE']['lastPrice'] if 'PE' in rec else None
                ce_oi = rec['CE']['openInterest'] if 'CE' in rec else None
                pe_oi = rec['PE']['openInterest'] if 'PE' in rec else None
                data.append({
                    "Strike": strike,
                    "CE LTP": ce_ltp,
                    "CE OI": ce_oi,
                    "PE LTP": pe_ltp,
                    "PE OI": pe_oi,
                })
            df = pd.DataFrame(data)
            df["ATM Distance"] = abs(df["Strike"] - underlying)
            st.dataframe(df.sort_values("ATM Distance"), use_container_width=True)
            st.subheader("Open Interest by Strike")
            st.line_chart(df.set_index("Strike")[["CE OI", "PE OI"]])
    st.caption("Live free data: Powered by NSE option chain API. For analysis only. Click rerun/refresh for latest data.")

# Tab 2: Performance Stats
with tab2:
    st.title("Zero Hero Performance Stats")
    perf_df = load_performance()
    if not perf_df.empty:
        st.write(f"Total Trades: {len(perf_df)}")
        succ = perf_df[perf_df["Result"] == "Success"]
        fail = perf_df[perf_df["Result"] == "Fail"]
        st.write(f"✅ Success: {len(succ)} | ❌ Fail: {len(fail)}")
        win_rate = round(100 * len(succ) / len(perf_df), 2) if len(perf_df) > 0 else 0
        st.metric("Win Rate (%)", win_rate)
        st.dataframe(perf_df.sort_values("Date", ascending=False), use_container_width=True)
        st.subheader("Confidence vs Result")
        st.bar_chart(perf_df.groupby("Confidence (%)")["Result"].value_counts().unstack().fillna(0))
    else:
        st.info("No performance stats yet. Mark signals in tab 1 to begin tracking.")
