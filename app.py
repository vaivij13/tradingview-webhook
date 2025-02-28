from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Alpaca API credentials (set these in Render environment variables)
ALPACA_BASE_URL = "https://api.alpaca.markets"
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

HEADERS = {
    "APCA-API-KEY-ID": ALPACA_API_KEY,
    "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY
}


# Function to get available USD balance
def get_available_funds():
    response = requests.get(f"{ALPACA_BASE_URL}/v2/account", headers=HEADERS)
    if response.status_code == 200:
        account_info = response.json()
        return float(account_info.get("buying_power", 0))  # Buying power for crypto
    else:
        print(f"❌ Failed to fetch account info: {response.text}")
        return 0  # Default to 0 if request fails


# Function to get available BTC balance
def get_available_crypto(symbol):
    url = f"{ALPACA_BASE_URL}/v2/positions/{symbol}"
    response = requests.get(url, headers=HEADERS)

    if response.status_code == 200:
        position_data = response.json()
        return float(position_data.get("qty_available", 0))  # Get available BTC quantity
    elif response.status_code == 404:
        print(f"🚨 No position found for {symbol}. You may not own any.")
        return 0
    else:
        print(f"❌ Failed to fetch crypto balance: {response.text}")
        return 0


def get_current_btc_price():
    url = f"{ALPACA_BASE_URL}/v2/assets/BTC"
    response = requests.get(url, headers=HEADERS)

    if response.status_code == 200:
        asset_data = response.json()
        if asset_data.get("tradable", False):
            # Fetch the latest BTC/USD price using market data
            price_url = f"{ALPACA_BASE_URL}/v2/marketdata/crypto/BTCUSD/trades/latest"
            price_response = requests.get(price_url, headers=HEADERS)

            if price_response.status_code == 200:
                btc_price = price_response.json().get("trade", {}).get("p", None)  # Last trade price
                if btc_price:
                    return float(btc_price)

    print(f"❌ Failed to fetch BTC price: {response.text}")
    return None


# Function to place orders on Alpaca
def place_order(symbol, side):
    btc_price = get_current_btc_price()

    if not btc_price:
        print("🚨 BTC price unavailable! Cannot place order.")
        return {"error": "BTC price unavailable"}

    if side == "buy":
        available_funds = get_available_funds()
        if available_funds < 1:
            print("🚨 Not enough funds to buy BTC!")
            return {"error": "Insufficient USD balance"}

        btc_quantity = round(available_funds / btc_price, 6)  # Buy as much BTC as possible

    elif side == "sell":
        available_btc = get_available_crypto(symbol)
        if available_btc < 0.0001:  # Avoid placing tiny sell orders
            print("🚨 Not enough BTC to sell!")
            return {"error": "Insufficient BTC balance"}

        btc_quantity = available_btc  # Sell entire BTC balance

    else:
        print("🚨 Invalid order side received!")
        return {"error": "Invalid order side"}

    print(f"⚡ Placing order: {side} {btc_quantity} {symbol}")

    url = f"{ALPACA_BASE_URL}/v2/orders"
    order_data = {
        "symbol": symbol,
        "qty": btc_quantity,
        "side": side,
        "type": "market",
        "time_in_force": "gtc"
    }

    response = requests.post(url, json=order_data, headers=HEADERS)
    print(f"✅ Alpaca Order Response: {response.status_code}, {response.text}")

    return response.json()


# Webhook endpoint for TradingView
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print(f"📩 Received webhook data: {data}")

    try:
        ticker = data.get("ticker")
        action = data.get("action")

        if not ticker or not action:
            print("🚨 Missing required fields in webhook data!")
            return jsonify({"error": "Missing required fields"}), 400

        alpaca_response = place_order(ticker, action)

        return jsonify(alpaca_response)

    except Exception as e:
        print(f"❌ Exception: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
