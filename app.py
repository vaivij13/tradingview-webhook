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

def place_order(symbol, action):
    """
    Places an order on Alpaca.
    - For buy: Uses USD balance to determine how much BTC to buy.
    - For sell: Uses BTC balance to determine how much BTC to sell.
    """
    available_funds = get_available_funds()  # USD balance
    btc_price = get_current_btc_price()  # Latest BTC price
    available_btc = get_available_crypto(symbol)  # BTC balance

    if action == "buy":
        if available_funds < 1:  # Ensure at least $1 for trade
            print("🚨 Not enough USD to buy BTC!")
            return {"error": "Insufficient USD balance"}

        btc_quantity = (available_funds * 0.5) / btc_price  # Buy with 50% of balance
        btc_quantity = round(btc_quantity, 6)  # Round to 6 decimals

    elif action == "sell":
        if available_btc < 0.0001:  # Ensure at least a small BTC amount
            print("🚨 Not enough BTC to sell!")
            return {"error": "Insufficient BTC balance"}

        btc_quantity = available_btc  # Sell entire BTC balance

    else:
        print("🚨 Invalid action type!")
        return {"error": "Invalid action"}

    print(f"⚡ Placing {action} order for {btc_quantity} BTC ({symbol})")

    # Send order to Alpaca
    url = f"{ALPACA_BASE_URL}/v2/orders"
    order_data = {
        "symbol": symbol,
        "qty": btc_quantity,
        "side": action,
        "type": "market",
        "time_in_force": "gtc"
    }

    response = requests.post(url, json=order_data, headers=headers)
    print(f"✅ Alpaca Order Response: {response.status_code}, {response.text}")
    return response.json()

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
