import os

from flask import Flask, jsonify, request
import requests

app = Flask(__name__)

# Base URLs for the stocks services
STOCKS1_URL = "http://stocks1-a:8000"
STOCKS2_URL = "http://stocks2:8000"


def fetch_stocks(portfolio):
    if portfolio == "stocks1":
        response = requests.get(f"{STOCKS1_URL}/stocks")
    elif portfolio == "stocks2":
        response = requests.get(f"{STOCKS2_URL}/stocks")
    else:
        return []

    if response.status_code == 200:
        return response.json()
    return []


@app.route('/capital-gains', methods=['GET'])
def get_capital_gains():
    try:
        # Parse query parameters
        portfolio = request.args.get("portfolio")
        numsharesgt = request.args.get("numsharesgt", type=int)
        numshareslt = request.args.get("numshareslt", type=int)

        # Fetch stocks based on the portfolio
        stocks = []
        if portfolio:
            stocks = fetch_stocks(portfolio)
        else:
            stocks = fetch_stocks("stocks1") + fetch_stocks("stocks2")

        # Filter stocks based on query parameters
        if numsharesgt is not None:
            stocks = [stock for stock in stocks if stock["shares"] > numsharesgt]
        if numshareslt is not None:
            stocks = [stock for stock in stocks if stock["shares"] < numshareslt]

        # Calculate capital gains
        capital_gains = 0.0
        gains_by_stock = []

        for stock in stocks:
            # Fetch current stock price
            ticker_price = get_ticker_price(stock["symbol"])
            stock_gain = ticker_price - stock["purchase price"]
            stock_gain = stock_gain * stock["shares"]
            gains_by_stock.append({"symbol": stock["symbol"], "capital_gain": stock_gain})
            capital_gains += stock_gain

        return jsonify({"total_capital_gain": capital_gains}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def get_ticker_price(symbol):
    try:
        api_url = f"https://api.api-ninjas.com/v1/stockprice?ticker={symbol}"
        headers = {'X-Api-Key': 'ADD YOUR API KEY HERE'} # CHANGE TO YOUR NINJA API KEY
        response = requests.get(api_url, headers=headers)

        #make an api call using symbol
        if response.status_code == requests.codes.ok:
            data = response.json()
            return data.get('price')
        else:
            print(f"Error: {response.status_code}, {response.text}")
            return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
