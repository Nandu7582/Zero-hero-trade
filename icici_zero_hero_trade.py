import requests

def place_order_icici(api_key, access_token, symbol, strike, option_type, qty):
    url = "https://api.icicidirect.com/equity/placeOrder"
    headers = {
        "apikey": api_key,
        "access_token": access_token,
        "Content-Type": "application/json"
    }
    payload = {
        "symbol": symbol,
        "strikePrice": strike,
        "optionType": option_type, # 'CE' or 'PE'
        "quantity": qty,
        "orderType": "BUY",
        "productType": "INTRADAY",
        # ... other required parameters
    }
    resp = requests.post(url, headers=headers, json=payload)
    return resp.json()

# Use your zero hero signal logic here, and call place_order_icici when you want to execute the trade.