from flask import Flask, request, jsonify
from flask_cors import CORS
from coinmarketcap_api import get_coin_price  # Mantém para predict/scan
import requests
import pandas as pd
import pandas_ta as ta

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

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.get_json()
    symbol = data.get('symbol', 'BTCUSDT').replace('/', '').upper()  # Binance não usa barra
    interval = data.get('interval', '1h')
    limit = int(data.get('limit', 100))

    # Intervalos válidos para Binance API
    valid_intervals = ['1m','3m','5m','15m','30m','1h','2h','4h','6h','8h','12h','1d']
    if interval not in valid_intervals:
        return jsonify({"error": "Invalid interval"}), 400

    # Busca candles da Binance
    url = f"https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }
    try:
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        klines = resp.json()
    except Exception as e:
        return jsonify({"error": f"Error fetching candles: {str(e)}"}), 500

    # Monta DataFrame
    columns = ['timestamp','open','high','low','close','volume','close_time','qav','trades','taker_base_vol','taker_quote_vol','ignore']
    df = pd.DataFrame(klines, columns=columns)
    df['open'] = df['open'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['close'] = df['close'].astype(float)
    df['volume'] = df['volume'].astype(float)
    df['timestamp'] = df['timestamp'] // 1000  # ms para segundos

    # Calcula indicadores
    last = 50
    rsi = ta.rsi(df['close'], length=14).fillna(0).round(2).tolist()
    macd_all = ta.macd(df['close'])
    macd = macd_all['MACD_12_26_9'].fillna(0).round(4).tolist()
    macd_signal = macd_all['MACDs_12_26_9'].fillna(0).round(4).tolist()
    macd_hist = macd_all['MACDh_12_26_9'].fillna(0).round(4).tolist()

    response = {
        "symbol": symbol,
        "interval": interval,
        "candles": df[['timestamp','open','high','low','close','volume']].tail(last).to_dict(orient='records'),
        "indicators": {
            "rsi": rsi[-last:],
            "macd": macd[-last:],
            "macd_signal": macd_signal[-last:],
            "macd_hist": macd_hist[-last:]
        }
    }
    return jsonify(response)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
