# coinmarketcap_api.py

import os
import requests
from dotenv import load_dotenv

# Load .env variables (API key will be loaded from .env)
load_dotenv()
API_KEY = os.getenv("CMC_API_KEY")  # You named it CMC_API_KEY in your .env

# Base URL for CoinMarketCap API
BASE_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"

def get_coin_price(coin_pair: str) -> float:
    """
    Receives coin_pair in the format 'BTC/USDT'
    Returns the current price as float.
    """
    if not API_KEY:
        raise ValueError("CMC_API_KEY not found in environment variables!")

    try:
        symbol, convert = coin_pair.split("/")
    except Exception:
        raise ValueError("coin_pair must be in format 'BTC/USDT'")

    params = {
        "symbol": symbol,
        "convert": convert
    }
    headers = {
        "Accepts": "application/json",
        "X-CMC_PRO_API_KEY": API_KEY
    }

    response = requests.get(BASE_URL, params=params, headers=headers)
    response.raise_for_status()
    data = response.json().get("data", {})

    # Defensive check for missing data
    if symbol not in data or convert not in data[symbol]["quote"]:
        raise ValueError(f"Could not retrieve price for {coin_pair}.")

    price = data[symbol]["quote"][convert]["price"]
    return float(price)
