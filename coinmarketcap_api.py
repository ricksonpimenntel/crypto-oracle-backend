# coinmarketcap_api.py

import os
import requests
from dotenv import load_dotenv

# 1) Carrega sua chave do arquivo .env
load_dotenv()
API_KEY = os.getenv("CMC_API_KEY")

# 2) URL base da CoinMarketCap
BASE_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"

def get_coin_price(coin_pair: str) -> float:
    """
    Recebe coin_pair no formato 'BTC/USDT'
    Retorna o preço atual como float.
    """
    # separa 'BTC' e 'USDT'
    symbol, convert = coin_pair.split("/")

    # parâmetros e cabeçalhos da requisição
    params = {
        "symbol": symbol,
        "convert": convert
    }
    headers = {
        "Accepts": "application/json",
        "X-CMC_PRO_API_KEY": API_KEY
    }

    # faz a chamada HTTP
    response = requests.get(BASE_URL, params=params, headers=headers)
    response.raise_for_status()  # levanta erro se status != 200
    data = response.json().get("data", {})

    # extrai o preço da moeda convertida
    price = data[symbol]["quote"][convert]["price"]
    return float(price)
