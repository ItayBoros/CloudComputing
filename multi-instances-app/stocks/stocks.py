import os
import pymongo
from flask import Flask, jsonify, request
import uuid
from datetime import datetime
import re
import requests

app = Flask(__name__)

# Get the database name from the environment variable
db_name = os.environ.get("MONGO_DB_NAME")

# Check if the value is properly set
if not db_name:
    raise ValueError("Environment variable MONGO_DB_NAME is not set or empty")

# Initialize the MongoDB client and database
client = pymongo.MongoClient("mongodb://mongo:27017/")
db = client[db_name]  # db_name must be a string
inv = db["inventory"]

Stocks = {}
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

        #check if there is Malformed data
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Malformed data"}), 400
        
        #check if symbol is not a string
        if not isinstance(data['symbol'], str):
                return jsonify({"error": "Invalid stock symbol"}), 400
        
        # check if shares is not a positive integer
        if not isinstance(data['shares'], int) or data['shares'] <= 0:
            return jsonify({"error": "Shares must be a positive integer"}), 400

        # check if purchase price is not a positive number
        if not isinstance(data['purchase price'], (int, float)) or data['purchase price'] <= 0:
            return jsonify({"error": "Purchase price must be a positive number"}), 400
        # generate UUID
        new_id = genID()

        # check if name field enter in the POST
        if 'name' not in data:
            name = "NA"
        else:
            if not isinstance(data['name'], str):
                return jsonify({"error": "name must be a string"}), 400
            name = data['name']

        # check if purchase date field enter in the POST
        doc = inv.find_one({"symbol": data['symbol'].upper()})
        if doc:
            return jsonify({"error": "Stock symbol already exists for this account"}), 400

        # Set optional fields
        name = data.get('name', "NA")
        purchase_date = data.get('purchase date', "NA")
        if purchase_date != "NA" and not validate_date_format(purchase_date):
            return jsonify({"error": "Invalid date format. Use DD-MM-YYYY"}), 400

        stock = {'_id': new_id,
                 'name': name,
                 'symbol': data['symbol'].upper(),
                 'purchase price': round(data['purchase price'], 2),
                 'purchase date': purchase_date,
                 'shares': data['shares']
                }
        inv.insert_one(stock)
        response_data = {'_id': new_id}
        return jsonify(response_data), 201
    except Exception as e:
        return jsonify({"server error": str(e)}), 500


@app.route('/stocks', methods=['GET'])
def getStocks():
    try:
        #moves the filters into dic
        query = request.args.to_dict()
        
        #in case there is no filters, return all
        if not query:
            all_stocks = list(inv.find())
            return jsonify(all_stocks), 200
        for field in query.keys():
            if field not in ['_id','name','symbol','shares', 'purchase price', 'purchase date']:
                return jsonify({'error': 'invalid query field'}), 422

        # Fetch filtered results
        stocks = inv.find(query)

        # Convert cursor to list
        filtered_stocks = list(stocks)

        #in case there is no filtered items
        if not filtered_stocks:
            return jsonify({"error": "No stocks match the given filters"}), 404

        return jsonify(filtered_stocks), 200

    except Exception as e:
        return jsonify({"server error": str(e)}), 500


@app.route('/stocks/<string:stockId>', methods=['GET'])
def getStock(stockId):
    #try to return the object by id
    try:
        stock = inv.find_one({'_id': stockId})
        return jsonify(stock), 200
    # return Key error in case there is no id such the input
    except KeyError:
       return jsonify({"error": "No such ID"}), 404
    except Exception as e:
        return jsonify({"server error": str(e)}), 500


@app.route('/stocks/<string:stockId>', methods=['DELETE'])
def deleteStock(stockId):
    try:
        # try to get the stock that want to delete using their id
        stock = inv.find_one({'_id': stockId})
        if not stock:
            return jsonify({"error": "No such ID"}), 404
        resp = inv.delete_one({'_id': stockId})
        if resp.deleted_count == 1:  # deleted
            return '', 204
    except KeyError:
        return jsonify({"error": "No such ID"}), 404
    except Exception as e:
        return jsonify({"server error": str(e)}), 500


@app.route('/stocks/<string:stockId>', methods=['PUT'])
def updateStock(stockId):
    try:
        content_type = request.headers.get('Content-Type')
        if content_type != 'application/json':
            return jsonify({"error": "expected application/json media type"}), 415
        data = request.get_json()

        #Check if required fields are present (all fields must appear in the request)
        required_fields = ['_id', 'name', 'symbol', 'purchase price', 'purchase date', 'shares']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Malformed data"}), 400

        stock = inv.find_one({'_id': stockId})
        # changing ID isn't possible
        curr_id = stock['_id']
        if data['_id'] != curr_id:
            return jsonify({"error": "Stock ID can not be change"}),400
        
        # changing symbol isn't possible
        symbol = stock['symbol']
        if not isinstance(data['symbol'],str):
            return jsonify({"error": "Invalid stock symbol"}), 400
        if data['symbol'].upper() != symbol:
            return jsonify({"error": "Stock symbol can not be change"})

        # validating data format
        if not isinstance(data['shares'], int) or (data['shares'] <= 0):
            return jsonify({"error": "Shares must be a positive integer"}), 400

        if not isinstance(data['purchase price'], (int, float)) or data['purchase price'] <= 0:
            return jsonify({"error": "Purchase price must be a positive number"}), 400

        # adding a name field
        if stock['name'] == "NA" and data['name'] != "NA":
            if not isinstance(data['name'], str):
                return jsonify({"error": "name must be a string"}), 400
        # name field is already exits but was not updated, the current name remains the same
        if stock['name'] != "NA" and data['name'] == "NA":
            name = stock['name']
        else:
            if not isinstance(data['name'], str):
                return jsonify({"error": "name must be a string"}), 400
            name = data['name']

        # adding a date field
        if stock['purchase date'] == "NA" and data['purchase date'] != "NA":
            if not validate_date_format(data['purchase date']):
                return jsonify({"error": "Invalid date format. Use DD-MM-YYYY"}), 400
            purchase_date = data['purchase date']
        # date field is already exits but was not updated, the current date remains the same
        elif stock['purchase date'] != "NA" and data['purchase date'] == "NA":
            purchase_date = stock['purchase date']
        # adding date field
        elif stock['purchase date'] != "NA" and data['purchase date'] != "NA":
            if not validate_date_format(data['purchase date']):
                return jsonify({"error": "Invalid date format. Use DD-MM-YYYY"}), 400
            purchase_date = data['purchase date']
        else:
            purchase_date = stock['purchase date']

        found = inv.find_one({'_id': stockId})
        # ID isn't valid
        if not found:
            return jsonify({"error": "Not found"}), 404

        updated_fields = {'name': name,
                 'purchase price': round(data['purchase price'], 2),
                 'purchase date': purchase_date,
                 'shares': data['shares']
                 }

        inv.update_one({'_id': stockId}, {'$set': updated_fields})
        response_data = {'_id': stockId}
        return jsonify(response_data), 200

    except Exception as e:
        return jsonify({"server error": str(e)}), 500


def validate_date_format(date_string):
    #build a valid pattern to date input
    pattern = r"^\d{2}-\d{2}-\d{4}$"
    if not re.match(pattern, date_string):
        return False
    try:
        #attempt to parse the date with the expected format
        datetime.strptime(date_string, "%d-%m-%Y")
        return True
    except ValueError:
        #raised when the format does not match
        return False


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


@app.route('/stock-value/<string:stockId>', methods=['GET'])
def get_stock_value(stockId):
    try:
        stock = inv.find_one({'_id': stockId})
        if not stock:
            return jsonify({"error": "Not found"}), 404

        #retrieve the current ticker price
        ticker_price = get_ticker_price(stock['symbol'])
        if ticker_price is None:
            return jsonify({"error": "Failed to retrieve ticker price"}), 500

        #calculate the stock value
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

        # iterate over all stocks in the portfolio
        stocks = inv.find()
        for stock in stocks: # fetch the current ticker price for the stock
            ticker_price = get_ticker_price(stock['symbol'])
            if ticker_price is None:
                return jsonify({"error": "Failed to retrieve ticker price"}), 500

        # calculate the stock value and add it to the portfolio value
            portfolio_value += ticker_price * stock['shares']

        # get the current date
        current_date = datetime.now().strftime('%Y-%m-%d')

        # return the portfolio value and date
        return jsonify({
            "date": current_date,
            "portfolio value": portfolio_value
        }), 200

    except Exception as e:
        return jsonify({"server error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)

