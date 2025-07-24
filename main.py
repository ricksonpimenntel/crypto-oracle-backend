from flask import Flask, request, jsonify
from flask_cors import CORS
from coinmarketcap_api import get_coin_price

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return '✅ CryptoOracle Flask backend is running!'

@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json()
    coin = data.get('coin')
    if not coin:
        return jsonify({'error': 'Coin symbol is required.'}), 400
    try:
        price = get_coin_price(coin)
        return jsonify({
            'symbol': coin,
            'current_price': price
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/scan', methods=['GET'])
def scan():
    coins = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'ADA/USDT', 'XRP/USDT']
    results = []
    for coin in coins:
        try:
            price = get_coin_price(coin)
            results.append({
                'symbol': coin,
                'current_price': price
            })
        except Exception as e:
            results.append({
                'symbol': coin,
                'error': str(e)
            })
    return jsonify(results)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
