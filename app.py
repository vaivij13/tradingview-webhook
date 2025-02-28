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

def get_available_funds():
    """Fetch the available buying power from Alpaca."""
    try:
        response = requests.get(f"{ALPACA_BASE_URL}/v2/account", headers=HEADERS)
        if response.status_code == 200:
            account_info = response.json()
            return float(account_info.get("buying_power", 0))  # Use buying power for crypto
        else:
            print(f"❌ Failed to fetch account info: {response.text}")
            return 0  # Default to 0 if request fails
    except Exception as e:
        print(f"❌ Exception getting funds: {e}")
        return 0


def get_current_btc_price():
    """Fetch the latest BTC/USD price from Alpaca."""
    try:
        url = "https://data.alpaca.markets/v1beta1/crypto/latest?symbols=BTC/USD"
        response = requests.get(url, headers=HEADERS)

        if response.status_code == 200:
            btc_price_data = response.json()
            print(f"🔍 BTC Price API Response: {btc_price_data}")  # Debugging log

            # Ensure correct parsing of API response
            try:
                btc_price = float(btc_price_data["crypto"]["BTC/USD"]["latestTrade"]["p"])
                return btc_price
            except KeyError as e:
                print(f"❌ KeyError fetching BTC price: {e}")
                return None
        else:
            print(f"❌ Failed to fetch BTC price: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Exception getting BTC price: {e}")
        return None


def calculate_trade_size():
    """Calculate trade size based on available funds and BTC price."""
    try:
        available_funds = get_available_funds()
        btc_price = get_current_btc_price()

        if btc_price and available_funds > 1:  # Ensure we have enough funds to trade
            trade_size = round((available_funds * 0.5) / btc_price, 6)  # Use 50% of balance
            print(f"💰 Available Funds: ${available_funds}, BTC Price: ${btc_price}, Trade Size: {trade_size} BTC")
            return trade_size
        else:
            print("🚨 Not enough funds to place an order!")
            return 0
    except Exception as e:
        print(f"❌ Error calculating trade size: {e}")
        return 0


def place_order(symbol, quantity, side):
    """Places an order on Alpaca."""
    if quantity <= 0:
        print("🚨 Order quantity too small, skipping order.")
        return None

    print(f"⚡ Placing order: {side} {quantity} {symbol}")

    order_data = {
        "symbol": symbol,
        "qty": quantity,
        "side": side,
        "type": "market",
        "time_in_force": "gtc"
    }

    try:
        response = requests.post(f"{ALPACA_BASE_URL}/v2/orders", json=order_data, headers=HEADERS)
        print(f"✅ Alpaca Order Response: {response.status_code}, {response.text}")
        return response.json()
    except Exception as e:
        print(f"❌ Exception placing order: {e}")
        return None


@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook to receive TradingView alerts and execute trades."""
    data = request.json
    print(f"📩 Received webhook data: {data}")

    try:
        ticker = data.get("ticker")
        action = data.get("action")

        if not ticker or not action:
            print("🚨 Missing required fields in webhook data!")
            return jsonify({"error": "Missing required fields"}), 400

        # Automatically calculate quantity based on available funds
        quantity = calculate_trade_size()

        if quantity > 0:
            alpaca_response = place_order(ticker, quantity, action)
            return jsonify(alpaca_response)
        else:
            return jsonify({"error": "Not enough funds to place an order"}), 400

    except Exception as e:
        print(f"❌ Exception: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
