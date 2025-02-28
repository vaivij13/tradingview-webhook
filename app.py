from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Alpaca API credentials (set these in Render environment variables)
ALPACA_BASE_URL = "https://paper-api.alpaca.markets"
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

# Function to place orders on Alpaca
def place_order(ticker, action, quantity):
    url = f"{ALPACA_BASE_URL}/v2/orders"
    headers = {
        "APCA-API-KEY-ID": ALPACA_API_KEY,
        "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY,
        "Content-Type": "application/json",
    }
    data = {
        "symbol": ticker,
        "side": action,
        "qty": quantity,
        "type": "market",
        "time_in_force": "gtc"
    }
    response = requests.post(url, json=data, headers=headers)
    return response.json()

# Webhook endpoint for TradingView
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if not data or 'ticker' not in data or 'action' not in data or 'quantity' not in data:
        return jsonify({"error": "Invalid data"}), 400

    ticker = data['ticker']
    action = data['action']
    quantity = int(data['quantity'])

    if action not in ["buy", "sell"]:
        return jsonify({"error": "Invalid action"}), 400

    response = place_order(ticker, action, quantity)
    return jsonify(response)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
