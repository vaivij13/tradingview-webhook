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
def get_available_crypto():
    """Fetch the current BTC holdings in Alpaca."""
    url = f"{ALPACA_BASE_URL}/v2/positions"
    response = requests.get(url, headers=HEADERS)

    if response.status_code == 200:
        positions = response.json()

        print(f"🔍 Raw Positions Data: {positions}")  # Debugging step

        for position in positions:
            if position["asset_class"] == "crypto" and position["symbol"] in ["BTC/USD", "BTCUSD"]:
                btc_available = float(position["qty"])
                print(f"✅ Available BTC: {btc_available}")
                return btc_available

        print("🚨 No BTC position found. You may not own any.")
        return 0
    else:
        print(f"❌ Failed to fetch positions: {response.text}")
        return 0


# Function to get the latest BTC price
def get_current_btc_price():
    url = "https://data.alpaca.markets/v1beta3/crypto/us/latest/trades?symbols=BTC/USD"

    response = requests.get(url, headers=HEADERS)

    if response.status_code == 200:
        try:
            btc_price = response.json()["trades"]["BTC/USD"]["p"]
            print(f"✅ BTC Price Fetched: ${btc_price}")
            return float(btc_price)
        except KeyError:
            print(f"❌ Unexpected Response Format: {response.json()}")
            return None
    else:
        print(f"❌ Failed to fetch BTC price: {response.text}")
        return None


# Function to place orders on Alpaca
def place_order(symbol, action):
    btc_price = get_current_btc_price()
    if btc_price is None:
        print("🚨 BTC price unavailable! Cannot place order.")
        return None

    if action == "buy":
        available_funds = get_available_funds()
        if available_funds <= 1:
            print("🚨 Not enough USD to buy BTC!")
            return None

        # Use 'notional' (dollar amount) for buys
        order_data = {
            "symbol": symbol,
            "notional": available_funds,  # Spend 50% of available funds
            "side": "buy",
            "type": "market",
            "time_in_force": "gtc"
        }

    elif action == "sell":
        btc_quantity = get_available_crypto()
        if btc_quantity <= 0:
            print("🚨 Not enough BTC to sell!")
            return None

        order_data = {
            "symbol": symbol,
            "qty": btc_quantity,  # Selling uses 'qty' (BTC amount)
            "side": "sell",
            "type": "market",
            "time_in_force": "gtc"
        }

    else:
        print("❌ Invalid action!")
        return None

    url = f"{ALPACA_BASE_URL}/v2/orders"
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
