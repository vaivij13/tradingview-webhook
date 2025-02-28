from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Alpaca API credentials (set these in Render environment variables)
ALPACA_BASE_URL = "https://api.alpaca.markets"
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

def calculate_trade_size(ticker):
    """ Calculate how much of an asset can be bought with available cash balance. """
    try:
        # Fetch account balance from Alpaca
        alpaca_url = "https://paper-api.alpaca.markets/v2/account"
        headers = {
            "APCA-API-KEY-ID": "YOUR_ALPACA_API_KEY",
            "APCA-API-SECRET-KEY": "YOUR_ALPACA_SECRET_KEY"
        }
        response = requests.get(alpaca_url, headers=headers)
        account_data = response.json()

        cash_balance = float(account_data["cash"])  # Available cash

        # Fetch the latest BTC/USD price from Alpaca
        btc_price_url = "https://paper-api.alpaca.markets/v2/assets/BTC/USD"
        btc_price_response = requests.get(btc_price_url, headers=headers)
        btc_price = float(btc_price_response.json().get("price", 0))

        if btc_price == 0:
            print("🚨 Error: BTC price could not be fetched.")
            return 0

        # Calculate quantity based on available balance
        trade_size = round(cash_balance / btc_price, 6)  # Round to 6 decimal places
        print(f"💰 Cash balance: ${cash_balance}, BTC Price: ${btc_price}, Trade Size: {trade_size} BTC")

        return trade_size

    except Exception as e:
        print(f"❌ Error calculating trade size: {e}")
        return 0

def get_available_funds():
    response = requests.get(f"{ALPACA_BASE_URL}/v2/account", headers=headers)
    if response.status_code == 200:
        account_info = response.json()
        return float(account_info["buying_power"])  # Buying power for crypto
    else:
        print(f"❌ Failed to fetch account info: {response.text}")
        return 0  # Default to 0 if request fails


def get_current_btc_price():
    url = "https://data.alpaca.markets/v1beta1/crypto/latest?symbols=BTC/USD"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        btc_price = response.json()["crypto"]["BTC/USD"]["latestTrade"]["p"]
        return float(btc_price)
    else:
        print(f"❌ Failed to fetch BTC price: {response.text}")
        return None
    
# Webhook endpoint for TradingView
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print(f"📩 Received webhook data: {data}")

    try:
        ticker = data.get("ticker")
        action = data.get("action")
        quantity = data.get("quantity", None)  # Optional, since we now auto-calculate

        if not ticker or not action:
            print("🚨 Missing required fields in webhook data!")
            return jsonify({"error": "Missing required fields"}), 400

        # If quantity is None, use available balance to calculate it
        if not quantity:
            quantity = calculate_trade_size(ticker)

        print(f"⚡ Placing order: {action} {quantity} {ticker}")
        alpaca_response = place_order(ticker, quantity, action)

        return jsonify(alpaca_response)

    except Exception as e:
        print(f"❌ Exception: {e}")
        return jsonify({"error": str(e)}), 500


# Function to place orders on Alpaca
def place_order(symbol, side):
    available_funds = get_available_funds()
    btc_price = get_current_btc_price()

    if btc_price and available_funds > 1:  # Avoid placing tiny orders
        btc_quantity = (available_funds * 0.5) / btc_price  # Use 50% of balance
        btc_quantity = round(btc_quantity, 6)  # Round to 6 decimals

        print(f"⚡ Placing order: {side} ${available_funds} worth of {symbol} (~{btc_quantity} BTC)")

        url = f"{ALPACA_BASE_URL}/v2/orders"
        order_data = {
            "symbol": symbol,
            "qty": btc_quantity,
            "side": side,
            "type": "market",
            "time_in_force": "gtc"
        }

        response = requests.post(url, json=order_data, headers=headers)
        print(f"✅ Alpaca Order Response: {response.status_code}, {response.text}")
        return response.json()
    else:
        print("🚨 Not enough funds or BTC price unavailable!")
        return None

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
