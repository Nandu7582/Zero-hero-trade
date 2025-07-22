import streamlit as st
import datetime
import pandas as pd
import os
from dotenv import load_dotenv
from breeze_connect import BreezeConnect

# Configuration
INDEX_INFO = {
    "NIFTY": {"symbol": "NIFTY", "expiry_weekday": 3},
    "BANKNIFTY": {"symbol": "BANKNIFTY", "expiry_weekday": 3},
    "FINNIFTY": {"symbol": "FINNIFTY", "expiry_weekday": 1},
}
ZERO_PRICE_MAX = 5
OTM_STRIKE_OFFSET = 200

st.set_page_config(page_title="Zero Hero Dashboard", layout="wide")

# Load environment variables
load_dotenv()
BREEZE_API_KEY = os.getenv("BREEZE_API_KEY")
BREEZE_API_SECRET = os.getenv("BREEZE_API_SECRET")
BREEZE_SESSION_TOKEN = os.getenv("BREEZE_SESSION_TOKEN")

# Initialize BreezeConnect
breeze = BreezeConnect(api_key=BREEZE_API_KEY)
breeze.generate_session(api_secret=BREEZE_API_SECRET, session_token=BREEZE_SESSION_TOKEN)

def get_option_chain(index):
    try:
        # Map index to ICICI Breeze API exchange and symbol
        symbol_map = {
            "NIFTY": {"exchange": "NSE", "symbol": "NIFTY"},
            "BANKNIFTY": {"exchange": "NSE", "symbol": "BANKNIFTY"},
            "FINNIFTY": {"exchange": "NSE", "symbol": "FINNIFTY"},
        }
        exchange = symbol_map[index]["exchange"]
        symbol = symbol_map[index]["symbol"]
        
        # Get expiry date
        expiry = get_expiry_date(index)
        expiry_str = expiry.strftime("%Y-%m-%d")
        
        # Fetch option chain data
        option_data = breeze.get_option_chain_quotes(
            stock_code=symbol,
            exchange_code=exchange,
            product_type="options",
            expiry_date=expiry_str
        )
        
        if option_data["Status"] != 200 or not option_data.get("Success"):
            st.error("Failed to fetch option chain data from ICICI Breeze API.")
            return None
        
        # Process the data into the required format
        records = {
            "underlyingValue": float(option_data["Success"][0]["underlying_spot_price"]),
            "data": []
        }
        
        for option in option_data["Success"]:
            records["data"].append({
                "strikePrice": float(option["strike_price"]),
                "expiryDate": option["expiry_date"],
                "callOption": {
                    "lastPrice": float(option["ltp"]) if option["right"] == "Call" else 0,
                    "openInterest": float(option["oi"]) if option["right"] == "Call" else 0,
                    "volume": float(option["volume"]) if option["right"] == "Call" else 0
                },
                "putOption": {
                    "lastPrice": float(option["ltp"]) if option["right"] == "Put" else 0,
                    "openInterest": float(option["oi"]) if option["right"] == "Put" else 0,
                    "volume": float(option["volume"]) if option["right"] == "Put" else 0
                }
            })
        
        return records
    
    except Exception as e:
        st.error(f"Error fetching option chain data: {str(e)}")
        return None

def get_expiry_date(index):
    today = datetime.date.today()
    weekday = today.weekday()
    expiry_weekday = INDEX_INFO[index]["expiry_weekday"]
    days_ahead = expiry_weekday - weekday if weekday <= expiry_weekday else 7 - weekday + expiry_weekday
    expiry = today + datetime.timedelta(days=days_ahead)
    return expiry

def signal_confidence(signal, records, underlying):
    strike = signal["Strike"]
    ltp = signal["LTP"]
    oi = signal["OI"]
    volume = signal["Volume"]
    expiry = get_expiry_date(signal["Index"])
    today = datetime.date.today()
    days_to_expiry = (expiry - today).days

    proximity_factor = max(0, 1 - abs(strike - underlying) / (OTM_STRIKE_OFFSET * 2))
    oi_factor = min(1, oi / 5000)
    volume_factor = min(1, volume / 500)
    expiry_factor = 1 if days_to_expiry == 0 else 0.5 if days_to_expiry == 1 else 0.2

    score = (0.3 * proximity_factor) + (0.3 * oi_factor) + (0.2 * volume_factor) + (0.2 * expiry_factor)
    conf_pct = round(score * 100, 1)
    return conf_pct

def analyze_zero_hero(records, index):
    underlying = records["underlyingValue"]
    data = records["data"]
    ce_zero = []
    
    for option in data:
        strike = option["strikePrice"]
        call_ltp = option["callOption"]["lastPrice"]
        call_oi = option["callOption"]["openInterest"]
        call_volume = option["callOption"]["volume"]
        
        if call_ltp <= ZERO_PRICE_MAX:
            ce_zero.append({
                "Index": index,
                "Strike": strike,
                "LTP": call_ltp,
                "OI": call_oi,
                "Volume": call_volume
            })
    
    # Calculate confidence for each signal
    for signal in ce_zero:
        signal["Confidence"] = signal_confidence(signal, records, underlying)
    
    return ce_zero

# Streamlit UI
st.title("Zero Hero Dashboard")

# Index selection
index = st.selectbox("Select Index", options=["NIFTY", "BANKNIFTY", "FINNIFTY"])

# Fetch and display option chain
if st.button("Fetch Option Chain"):
    records = get_option_chain(index)
    if records:
        st.write(f"Underlying Value: {records['underlyingValue']}")
        zero_hero_signals = analyze_zero_hero(records, index)
        
        if zero_hero_signals:
            df = pd.DataFrame(zero_hero_signals)
            st.write("Zero Hero Signals (Call Options with LTP <= 5)")
            st.dataframe(df)
        else:
            st.write("No Zero Hero signals found.")
