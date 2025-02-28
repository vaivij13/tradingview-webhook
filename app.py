from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Alpaca API credentials (Set these in your environment variables)
ALPACA_BASE_URL = "https://api.alpaca.markets"
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

# Headers for Alpaca API authentication
HEADERS = {
    "APCA-API-KEY-ID": ALPACA_API_KEY,
    "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY
}

def get_available_funds():
    """Fetch available funds from Alpaca account."""
    try:
        url = f"{ALPACA_BASE_URL}/v2/account"
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            account_info = response.json()
            return float(account_info.get("buying_power", 0))  # Adjusted for live funds
        else:
            print(f"❌ Failed to fetch account info: {response.text}")
            return 0
    except Exception as e:
        print(f"❌ Error fetching available funds: {e}")
        return 0

def get_current_btc_price():
    """Fetch latest BTC/USD price from Alpaca."""
    try:
        url = f"https://data.alpaca.markets/v1beta3/crypto/us/latest/trades?symbols=BTC/USD"
        response = requests.get(url, headers=HEADERS)

        if response.status_code == 200:
            btc_price = response.json()["trades"]["BTC/USD"]["p"]
            return float(btc_price)
        else:
            print(f"❌ Failed to fetch BTC price: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error fetching BTC price: {e}")
        return None

def calculate_trade_size():
    """Calculate how much BTC can be bought based on available funds."""
    try:
        available_funds = get_available_funds()
        btc_price = get_current_btc_price()

        if available_funds > 1 and btc_price:
            trade_size = round((available_funds * 0.5) / btc_price, 6)  # Use 50% of balance
            print(f"💰 Available Funds: ${available_funds}, BTC Price: ${btc_price}, Trade Size: {trade_size} BTC")
            return trade_size
        else:
            print("🚨 Not enough funds or BTC price unavailable!")
            return 0
    except Exception as e:
        print(f"❌ Error calculating trade size: {e}")
        return 0

def place_order(symbol, side):
    """Place an order on Alpaca."""
    quantity = calculate_trade_size()

    if quantity > 0:
        print(f"⚡ Placing order: {side} {quantity} {symbol}")

        order_data = {
            "symbol": symbol,
            "qty": quantity,
            "side": side,
            "type": "market",
            "time_in_force": "gtc"
        }

        url = f"{ALPACA_BASE_URL}/v2/orders"
        response = requests.post(url, json=order_data, headers=HEADERS)

        print(f"✅ Alpaca Order Response: {response.status_code}, {response.text}")
        return response.json()
    else:
        print("🚨 Not enough funds to place an order!")
        return {"error": "Not enough funds"}

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle webhook requests from TradingView."""
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
