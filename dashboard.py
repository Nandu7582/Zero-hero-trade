# Adding unique keys to buttons in the sidebar and footer to prevent StreamlitDuplicateElementId errors.

import streamlit as st
import requests
import datetime
import pandas as pd
import json
import os

INDEX_INFO = {
    "NIFTY": {"symbol": "NIFTY", "expiry_weekday": 3},
    "BANKNIFTY": {"symbol": "BANKNIFTY", "expiry_weekday": 3},
    "FINNIFTY": {"symbol": "FINNIFTY", "expiry_weekday": 1},
}
ZERO_PRICE_MAX = 5
OTM_STRIKE_OFFSET = 200
API_URL = "https://www.nseindia.com/api/option-chain-indices?symbol={}"

st.set_page_config(page_title="Zero Hero Dashboard", layout="wide")

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

def get_expiry_date(index):
    today = datetime.date.today()
    weekday = today.weekday()
    expiry_weekday = INDEX_INFO[index]['expiry_weekday']
    days_ahead = expiry_weekday - weekday if weekday <= expiry_weekday else 7 - weekday + expiry_weekday
    expiry = today + datetime.timedelta(days=days_ahead)
    return expiry

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

def analyze_zero_hero(records, index):
    underlying = records['underlyingValue']
    data = records['data']
    ce_zero = []
