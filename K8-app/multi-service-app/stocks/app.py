import os
import pymongo
from pymongo.errors import DuplicateKeyError 
from flask import Flask, jsonify, request
import uuid
from datetime import datetime
import re
import requests

app = Flask(__name__)

# Get the database name from the environment variable
db_name = os.environ.get("MONGO_DB_NAME")
if not db_name:
    raise ValueError("Environment variable MONGO_DB_NAME is not set or empty")

# Initialize MongoDB client and database
client = pymongo.MongoClient("mongodb://mongo:27017/")
db = client[db_name]
inv = db["inventory"]

# create a unique index on 'symbol'
inv.create_index([("symbol", 1)], unique=True)


def genID():
    return str(uuid.uuid4())


@app.route('/kill', methods=['GET'])
def kill_container():
    os._exit(1)


@app.route('/stocks', methods=['POST'])
def addStock():
    try:
        content_type = request.headers.get('Content-Type')
        if content_type != 'application/json':
            return jsonify({"error": "Expected application/json media type"}), 415

        data = request.get_json()
        required_fields = ['symbol', 'purchase price', 'shares']

        # Check if required fields exist
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Malformed data"}), 400

        # Check if symbol is a string
        if not isinstance(data['symbol'], str):
            return jsonify({"error": "Invalid stock symbol"}), 400

        # Check if shares is a positive integer
        if not isinstance(data['shares'], int) or data['shares'] <= 0:
            return jsonify({"error": "Shares must be a positive integer"}), 400

        # Check if purchase price is a positive number
        if not isinstance(data['purchase price'], (int, float)) or data['purchase price'] <= 0:
            return jsonify({"error": "Purchase price must be a positive number"}), 400

        # Generate a new UUID for "id"
        new_id = genID()

        # Check if name field is in the POST
        if 'name' not in data:
            name = "NA"
        else:
            if not isinstance(data['name'], str):
                return jsonify({"error": "name must be a string"}), 400
            name = data['name']

        # Validate purchase date if provided
        purchase_date = data.get('purchase date', "NA")
        if purchase_date != "NA" and not validate_date_format(purchase_date):
            return jsonify({"error": "Invalid date format. Use DD-MM-YYYY"}), 400

        # Build the stock document
        stock = {
            "id": new_id,
            "name": name,
            "symbol": data['symbol'].upper(),
            "purchase price": round(data['purchase price'], 2),
            "purchase date": purchase_date,
            "shares": data['shares']
        }

        # Try inserting - if there's a duplicate symbol, catch DuplicateKeyError
        try:
            inv.insert_one(stock)
        except DuplicateKeyError:
            return jsonify({"error": "Stock symbol already exists"}), 400

        response_data = {"id": new_id}
        return jsonify(response_data), 201

    except Exception as e:
        return jsonify({"server error": str(e)}), 400


@app.route('/stocks', methods=['GET'])
def getStocks():
    """
    If no query parameters, return all.
    Otherwise, allow filter only by these fields: id, name, symbol, shares, purchase price, purchase date.
    """
    try:
        query_params = request.args.to_dict()

        if not query_params:
            # No filters; return everything
            all_stocks = list(inv.find({}, {"_id": 0}))  # exclude Mongo's internal _id
            return jsonify(all_stocks), 200

        allowed_fields = ['id', 'name', 'symbol', 'shares', 'purchase price', 'purchase date']
        for field in query_params.keys():
            if field not in allowed_fields:
                return jsonify({'error': 'invalid query field'}), 422

        stocks_cursor = inv.find(query_params, {"_id": 0})
        filtered_stocks = list(stocks_cursor)

        if not filtered_stocks:
            return jsonify({"error": "No stocks match the given filters"}), 404

        return jsonify(filtered_stocks), 200

    except Exception as e:
        return jsonify({"server error": str(e)}), 500


@app.route('/stocks/<string:stockId>', methods=['GET'])
def getStock(stockId):
    try:
        stock = inv.find_one({"id": stockId}, {"_id": 0})
        if stock is None:
            return jsonify({"error": "No such ID"}), 404
        return jsonify(stock), 200

    except Exception as e:
        return jsonify({"server error": str(e)}), 500


@app.route('/stocks/<string:stockId>', methods=['DELETE'])
def deleteStock(stockId):
    try:
        stock = inv.find_one({"id": stockId})
        if not stock:
            return jsonify({"error": "No such ID"}), 404

        resp = inv.delete_one({"id": stockId})
        if resp.deleted_count == 1:
            return '', 204

    except Exception as e:
        return jsonify({"server error": str(e)}), 500


@app.route('/stocks/<string:stockId>', methods=['PUT'])
def updateStock(stockId):
    try:
        content_type = request.headers.get('Content-Type')
        if content_type != 'application/json':
            return jsonify({"error": "expected application/json media type"}), 415

        data = request.get_json()

        required_fields = ['id', 'name', 'symbol', 'purchase price', 'purchase date', 'shares']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Malformed data"}), 400

        stock = inv.find_one({'id': stockId})
        if not stock:
            return jsonify({"error": "Not found"}), 404

        # Check if the client is trying to change "id"
        if data['id'] != stockId:
            return jsonify({"error": "Stock ID cannot be changed"}), 400

        # Check if the client is trying to change the symbol
        if not isinstance(data['symbol'], str):
            return jsonify({"error": "Invalid stock symbol"}), 400
        if data['symbol'].upper() != stock['symbol']:
            return jsonify({"error": "Stock symbol cannot be changed"}), 400

        # Validate shares
        if not isinstance(data['shares'], int) or data['shares'] <= 0:
            return jsonify({"error": "Shares must be a positive integer"}), 400

        # Validate purchase price
        if not isinstance(data['purchase price'], (int, float)) or data['purchase price'] <= 0:
            return jsonify({"error": "Purchase price must be a positive number"}), 400

        # Validate name
        if not isinstance(data['name'], str):
            return jsonify({"error": "name must be a string"}), 400

        # Validate date (only if it's not "NA")
        if data['purchase date'] != "NA":
            if not validate_date_format(data['purchase date']):
                return jsonify({"error": "Invalid date format. Use DD-MM-YYYY"}), 400
            purchase_date = data['purchase date']
        else:
            purchase_date = stock['purchase date']

        updated_fields = {
            'name': data['name'],
            'purchase price': round(data['purchase price'], 2),
            'purchase date': purchase_date,
            'shares': data['shares']
        }

        inv.update_one({'id': stockId}, {'$set': updated_fields})
        return jsonify({"id": stockId}), 200

    except Exception as e:
        return jsonify({"server error": str(e)}), 400


def validate_date_format(date_string):
    pattern = r"^\d{2}-\d{2}-\d{4}$"
    if not re.match(pattern, date_string):
        return False
    try:
        datetime.strptime(date_string, "%d-%m-%Y")
        return True
    except ValueError:
        return False


def get_ticker_price(symbol):
    """
    Use external API to retrieve the current ticker price.
    """
    try:
        api_url = f"https://api.api-ninjas.com/v1/stockprice?ticker={symbol}"
        headers = {'X-Api-Key': 'ADD YOUR API KEY HERE'} # CHANGE TO YOUR NINJA API KEY
        response = requests.get(api_url, headers=headers)
        if response.status_code == requests.codes.ok:
            data = response.json()
            return data.get('price')
        else:
            print(f"Error: {response.status_code}, {response.text}")
            return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None


@app.route('/stock-value/<string:stockId>', methods=['GET'])
def get_stock_value(stockId):
    try:
        stock = inv.find_one({'id': stockId})
        if not stock:
            return jsonify({"error": "Not found"}), 404

        ticker_price = get_ticker_price(stock['symbol'])
        if ticker_price is None:
            return jsonify({"error": "Failed to retrieve ticker price"}), 500

        stock_value = ticker_price * stock['shares']
        return jsonify({
            "symbol": stock['symbol'],
            "ticker": ticker_price,
            "stock value": stock_value
        }), 200

    except Exception as e:
        return jsonify({"server error": str(e)}), 500


@app.route('/portfolio-value', methods=['GET'])
def get_portfolio_value():
    try:
        portfolio_value = 0.0
        stocks = inv.find()
        for stock in stocks:
            ticker_price = get_ticker_price(stock['symbol'])
            if ticker_price is None:
                return jsonify({"error": f"Failed to retrieve ticker price for {stock['symbol']}"}), 500
            portfolio_value += ticker_price * stock['shares']

        current_date = datetime.now().strftime('%Y-%m-%d')

        return jsonify({
            "date": current_date,
            "portfolio value": portfolio_value
        }), 200

    except Exception as e:
        return jsonify({"server error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)
