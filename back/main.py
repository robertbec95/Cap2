import requests
import json
from flask import Flask, jsonify, render_template, url_for, request, redirect, session
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash

# Initialize the Flask app
app = Flask(__name__)
CORS(app, supports_credentials=True)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///yourdatabase.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your_secret_key_here'

db = SQLAlchemy(app)


# Define models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

    def __repr__(self):
        return '<User %r>' % self.username

# Load the database contents
with open("database.json", "r") as file:
    database = json.load(file)

### Oracle database credentials
#un = 'ADMIN'
#pw = 'Capstone123!'
#dsn = '(description= (retry_count=20)(retry_delay=3)(address=(protocol=tcps)(port=1521)(host=adb.eu-madrid-1.oraclecloud.com))(connect_data=(service_name=g4bbbc586754471_bfxn1ww61tnq3w1j_high.adb.oraclecloud.com))(security=(ssl_server_dn_match=yes)))'
        
@app.route('/create-user', methods=['POST'])
def create_user():
    try:
        username = request.json['username']
        password = request.json['password']

        # Check if user exists
        user_exists = User.query.filter_by(username=username).first()
        if user_exists:
            return jsonify({'status': 'error', 'message': 'Username already exists'}), 409

        # Hashing the password for security
        hashed_password = generate_password_hash(password)

        # Create new user
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        return jsonify({'status': 'success', 'message': 'User created successfully'}), 201
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

#Login
@app.route('/handle-login', methods=['POST'])
def handle_login():
    data = request.get_json()
    username = data['username']
    password = data['password']
    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password, password):
        session['username'] = username
        return jsonify({'status': 'success'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'Invalid credentials'}), 401

#Logout
@app.route('/logout')
def logout():
    session.pop('username', None)  # Remove the username from session
    return redirect(url_for('login'))

# Function to get the latest quote for a given stock symbol
def get_latest_quote(symbol):
    api_key = "OMLTKM3U67PVKJVJ"
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={api_key}"
    response = requests.get(url)

    if response.status_code != 200:
        return None

    data = response.json()
    if "Global Quote" not in data:
        return None

    if "Error Message" in data["Global Quote"]:
        return None
    
    return data["Global Quote"]

# Route to get information for a specific stock
@app.route('/stock/<symbol>')
def stock(symbol):
    api_key = "OMLTKM3U67PVKJVJ"
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={api_key}"
    response = requests.get(url)

    if response.status_code != 200:
        return "Error: Unable to fetch stock data."

    data = json.loads(response.text)

    if "Error Message" in data:
        return jsonify({"error": data["Error Message"]}), 400

    return jsonify(data)

# Route to get user information by user_id
@app.route('/user/<user_id>')
def user(user_id):
    if user_id not in database:
        return jsonify({"error": "User not found."}), 400

    user_data = database[user_id]
    total_stock_value = 0
    holdings = []

    for symbol, quantity in zip(user_data["symbols"], user_data["quantity"]):
        api_key = "OMLTKM3U67PVKJVJ"
        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={api_key}"
        response = requests.get(url)

        if response.status_code != 200:
            return "Error: Unable to fetch stock data."

        stock_data = json.loads(response.text)

        if "Error Message" in stock_data:
            return jsonify({"error": stock_data["Error Message"]}), 400
        latest_date = list(stock_data["Time Series (Daily)"].keys())[1]

        stock_value = float(stock_data["Time Series (Daily)"][latest_date]["4. close"]) * quantity
        total_stock_value += stock_value



        holdings.append({"symbol": symbol, "stock_value": stock_value})

    return jsonify({"user_id": user_id, "total_stock_value": total_stock_value, "holdings": holdings})

# Define the route for user portfolio pages
# @app.route('/portfolio/<user_id>')
# def portfolio(user_id):
#     if user_id not in database:
#         return jsonify({"error": "User not found."}), 400

#     user_data = database[user_id]
#     total_stock_value = 0
#     holdings = []

#     for symbol, weight in zip(user_data["symbols"], user_data["weights"]):
#         api_key = "OMLTKM3U67PVKJVJ"
#         url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={api_key}"
#         response = requests.get(url)

#         if response.status_code != 200:
#             return "Error: Unable to fetch stock data."

#         stock_data = json.loads(response.text)

#         if "Error Message" in stock_data:
#             return jsonify({"error": stock_data["error"]["message"]}), 400

#         latest_date = list(stock_data["Time Series (Daily)"].keys())[-1]

#         stock_value = float(stock_data["Time Series (Daily)"][latest_date]["4. close"]) * weight
#         total_stock_value += stock_value

#         holdings.append({"symbol": symbol, "stock_value": stock_value})

#     return render_template('portfolio.html', user_id=user_id, total_stock_value=total_stock_value, holdings=holdings)

if __name__ == '__main__':
    app.run(debug=True)

    for user_id in database:
        print(url_for('portfolio', user_id=user_id))