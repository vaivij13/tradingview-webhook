from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Alpaca API credentials (set these in Render environment variables)
ALPACA_BASE_URL = "https://api.alpaca.markets"
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

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
    
# Function to place orders on Alpaca
def place_order(symbol, side):
    available_funds = get_available_funds()
    btc_price = get_current_btc_price()

    if btc_price and available_funds > 1:  # Avoid placing tiny orders
        btc_quantity = available_funds / btc_price  # Convert USD to BTC
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

# Webhook endpoint for TradingView
@app.route('/webhook', methods=['POST'])
def webhook():
    """ Handles incoming TradingView alerts and places an order on Alpaca """
    data = request.json
    print(f"Received webhook data: {data}")

    ticker = data.get("ticker")  # Example: "BTCUSD"
    action = data.get("action")  # Example: "buy" or "sell"
    quantity = data.get("quantity")  # Example: 0.01

    if action not in ["buy", "sell"]:
        print("Invalid action received.")
        return jsonify({"error": "Invalid action"}), 400

    # Place order on Alpaca
    alpaca_response = place_order(ticker, quantity, action)
    return jsonify(alpaca_response), 200

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
