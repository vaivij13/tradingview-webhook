from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Alpaca API credentials (set these in Render environment variables)
ALPACA_BASE_URL = "https://paper-api.alpaca.markets"
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

# Function to place orders on Alpaca
def place_order(symbol, qty, side):
    print(f"⚡ Placing order: {side} {qty} of {symbol}")  # Confirm function runs
    url = f"{ALPACA_BASE_URL}/v2/orders"
    headers = {
        "APCA-API-KEY-ID": ALPACA_API_KEY,
        "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY,
        "Content-Type": "application/json"
    }
    order_data = {
        "symbol": symbol,
        "qty": qty,
        "side": side,
        "type": "market",
        "time_in_force": "gtc"
    }
    response = requests.post(url, json=order_data, headers=headers)
    print(f"✅ Alpaca Order Response: {response.status_code}, {response.text}")  # Log full response
    return response.json()


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
