import os
from dotenv import load_dotenv

load_dotenv()

from flask import Flask, request, jsonify
from flask_cors import CORS
from pycoingecko import CoinGeckoAPI  # <-- CORRECT IMPORT
import requests
import pandas as pd
import pandas_ta as ta
from werkzeug.exceptions import BadRequest

app = Flask(__name__)
CORS(app)

# Supported coins mapping (API expects IDs like 'bitcoin', not 'BTC/USDT')
SYMBOL_TO_ID = {
    'BTC/USDT': 'bitcoin',
    'ETH/USDT': 'ethereum',
    'SOL/USDT': 'solana',
    'ADA/USDT': 'cardano',
    'XRP/USDT': 'ripple',
    'BTCUSDT': 'bitcoin',
    'ETHUSDT': 'ethereum',
    'SOLUSDT': 'solana',
    'ADAUSDT': 'cardano',
    'XRPUSDT': 'ripple',
    'BTC': 'bitcoin',
    'ETH': 'ethereum',
    'SOL': 'solana',
    'ADA': 'cardano',
    'XRP': 'ripple',
}

SUPPORTED_COINS = list(SYMBOL_TO_ID.keys())

def make_response(success, data=None, error=None):
    return {
        "success": success,
        "data": data,
        "error": error
    }

@app.errorhandler(BadRequest)
def handle_bad_request(e):
    return jsonify(make_response(
        False,
        error={"type": "BadRequest", "message": "Invalid or malformed JSON payload."}
    )), 400

def get_coin_price(symbol, vs_currency='usd'):
    # Map symbol to CoinGecko ID
    coin_id = SYMBOL_TO_ID.get(symbol.upper())
    if not coin_id:
        raise ValueError(f"Coin '{symbol}' not supported or not mapped to CoinGecko ID.")
    cg = CoinGeckoAPI()
    data = cg.get_price(ids=coin_id, vs_currencies=vs_currency)
    return data.get(coin_id, {}).get(vs_currency)

@app.route('/')
def home():
    return '✅ CryptoOracle Flask backend is running!'

@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json(silent=True)
    if not data or 'coin' not in data:
        return jsonify(make_response(
            False, 
            error={"type": "MissingField", "message": "Field 'coin' is required."}
        )), 400
    coin = data.get('coin')
    # Accept coin in any of the supported formats
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
    for coin in SUPPORTED_COINS[:5]:  # Only first 5 unique coins (for now)
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
    data = request.get_json(silent=True)
    if not data or 'symbol' not in data:
        return jsonify(make_response(
            False,
            error={"type": "MissingField", "message": "Field 'symbol' is required."}
        )), 400
    symbol = data.get('symbol', 'BTCUSDT').replace('/', '').upper()
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
        if not isinstance(klines, list):
            raise ValueError("Invalid response from Binance API.")
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
# Teste para forçar alteração
"# MUDANCA RADICAL" 
