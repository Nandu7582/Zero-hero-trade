# Zero Hero Dashboard

Streamlit dashboard for Zero Hero expiry trades (NIFTY, BANKNIFTY, FINNIFTY).  
Works on desktop and mobile browsers.  
Features:

- Live free option chain data from NSE (auto-refresh on page reload)
- Deep OTM "zero hero" signals with confidence %
- Mark signals as Success/Fail and track stats in "Performance Stats"
- Mobile-friendly layout

## How to use

1. On Replit/Render, upload all files in this repo.
2. Install dependencies automatically or via:
    ```
    pip install -r requirements.txt
    ```
3. Run the app:
    ```
    streamlit run dashboard.py
    ```
4. Use your browser (mobile or desktop) to access the dashboard!

## Note

- For analysis only. No auto-trading.
- NSE may block excessive requests—refresh as needed.