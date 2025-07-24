from flask import Flask, request, jsonify
from flask_cors import CORS
from coinmarketcap_api import get_coin_price  # Mantém para predict/scan
import requests
import pandas as pd
import pandas_ta as ta

app = Flask(__name__)
CORS(app)

# Helper universal de resposta padronizada
def make_response(success, data=None, error=None):
    return {
        "success": success,
        "data": data,
        "error": error
    }

SUPPORTED_COINS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'ADA/USDT', 'XRP/USDT']

@app.route('/')
def home():
    return '✅ CryptoOracle Flask backend is running!'

@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json()
    coin = data.get('coin')
    if not coin:
        return jsonify(make_response(
            False, 
            error={"type": "MissingField", "message": "Coin symbol is required."}
        )), 400
    if coin.upper() not in [c.replace('/', '') for c in SUPPORTED_COINS] and coin.upper() not in SUPPORTED_COINS:
        return jsonify(make_response(
            False, 
            error={"type": "InvalidCoin", "message": f"Moeda '{coin}' não suportada."}
        )), 400
    try:
        price = get_coin_price(coin)
        return jsonify(make_response(
            True, 
            data={"symbol": coin, "current_price": price}
        ))
    except Exception as e:
        return jsonify(make_response(
            False, 
            error={"type": "ServerError", "message": str(e)}
        )), 500

@app.route('/scan', methods=['GET'])
def scan():
    results = []
    for coin in SUPPORTED_COINS:
        try:
            price = get_coin_price(coin)
            results.append({
                "symbol": coin,
                "current_price": price,
                "error": None
            })
        except Exception as e:
            results.append({
                "symbol": coin,
                "current_price": None,
                "error": {"type": "ServerError", "message": str(e)}
            })
    return jsonify(make_response(True, data={"prices": results}))

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.get_json()
    symbol = data.get('symbol', 'BTCUSDT').replace('/', '').upper()  # Binance não usa barra
    interval = data.get('interval', '1h')
    limit = int(data.get('limit', 100))

    valid_intervals = ['1m','3m','5m','15m','30m','1h','2h','4h','6h','8h','12h','1d']
    if interval not in valid_intervals:
        return jsonify(make_response(
            False, 
            error={"type": "InvalidInterval", "message": "Invalid interval"}
        )), 400

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
        return jsonify(make_response(
            False, 
            error={"type": "ExternalAPIError", "message": f"Error fetching candles: {str(e)}"}
        )), 500

    columns = ['timestamp','open','high','low','close','volume','close_time','qav','trades','taker_base_vol','taker_quote_vol','ignore']
    try:
        df = pd.DataFrame(klines, columns=columns)
        df['open'] = df['open'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['close'] = df['close'].astype(float)
        df['volume'] = df['volume'].astype(float)
        df['timestamp'] = df['timestamp'] // 1000  # ms para segundos

        last = min(50, len(df))  # Garante não dar erro se houver poucos candles
        rsi = ta.rsi(df['close'], length=14).fillna(0).round(2).tolist()
        macd_all = ta.macd(df['close'])
        macd = macd_all['MACD_12_26_9'].fillna(0).round(4).tolist()
        macd_signal = macd_all['MACDs_12_26_9'].fillna(0).round(4).tolist()
        macd_hist = macd_all['MACDh_12_26_9'].fillna(0).round(4).tolist()

        result = {
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
        return jsonify(make_response(True, data=result))
    except Exception as e:
        return jsonify(make_response(
            False, 
            error={"type": "ProcessingError", "message": f"Error processing data: {str(e)}"}
        )), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
