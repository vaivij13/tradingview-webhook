from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Alpaca API credentials (set these in Render environment variables)
ALPACA_BASE_URL = "https://api.alpaca.markets"
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

# Common headers for Alpaca API requests
HEADERS = {
    "APCA-API-KEY-ID": ALPACA_API_KEY,
    "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY,
    "Content-Type": "application/json"
}

def calculate_trade_size(ticker):
    """ Calculate how much of an asset can be bought with available cash balance. """
    try:
        # Fetch account balance from Alpaca
        response = requests.get(f"{ALPACA_BASE_URL}/v2/account", headers=HEADERS)
        account_data = response.json()

        # Get available cash balance (use buying_power for margin accounts)
        cash_balance = float(account_data.get("buying_power", 0))

        if cash_balance <= 0:
            print("🚨 Error: No available cash balance.")
            return 0

        # Fetch the latest BTC/USD price from Alpaca
        btc_price_url = "https://data.alpaca.markets/v1beta1/crypto/latest?symbols=BTC/USD"
        btc_price_response = requests.get(btc_price_url, headers=HEADERS)
        btc_price_data = btc_price_response.json()
        btc_price = float(btc_price_data["crypto"]["BTC/USD"]["latestTrade"]["p"])

        if btc_price == 0:
            print("🚨 Error: BTC price could not be fetched.")
            return 0

        # Calculate trade size
        trade_size = round(cash_balance / btc_price, 6)  # Round to 6 decimal places
        print(f"💰 Cash balance: ${cash_balance}, BTC Price: ${btc_price}, Trade Size: {trade_size} BTC")

        return trade_size

    except Exception as e:
        print(f"❌ Error calculating trade size: {e}")
        return 0

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

        if quantity == 0:
            print("🚨 Not enough funds to place an order!")
            return jsonify({"error": "Insufficient funds"}), 400

        print(f"⚡ Placing order: {action} {quantity} {ticker}")
        alpaca_response = place_order(ticker, quantity, action)

        return jsonify(alpaca_response)

    except Exception as e:
        print(f"❌ Exception: {e}")
        return jsonify({"error": str(e)}), 500

# Function to place orders on Alpaca
def place_order(symbol, quantity, side):
    """ Places an order on Alpaca """
    try:
        order_data = {
            "symbol": symbol.replace("/", ""),  # Convert BTC/USD -> BTCUSD
            "qty": quantity,
            "side": side,
            "type": "market",
            "time_in_force": "gtc"
        }

        response = requests.post(f"{ALPACA_BASE_URL}/v2/orders", json=order_data, headers=HEADERS)
        print(f"✅ Alpaca Order Response: {response.status_code}, {response.text}")
        return response.json()

    except Exception as e:
        print(f"❌ Error placing order: {e}")
        return {"error": str(e)}

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
