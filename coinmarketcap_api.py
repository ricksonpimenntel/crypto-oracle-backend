# coingecko_api.py

from pycoingecko import CoinGeckoAPI

cg = CoinGeckoAPI()

# Map your supported coins (no slashes, all upper for consistency)
SYMBOL_MAP = {
    'BTCUSDT': 'bitcoin',
    'ETHUSDT': 'ethereum',
    'SOLUSDT': 'solana',
    'ADAUSDT': 'cardano',
    'XRPUSDT': 'ripple',
    # Add more as you like
}

def get_coin_price(symbol):
    """
    symbol: str, accepts 'BTC/USDT' or 'BTCUSDT'
    returns: float, price in USD
    """
    # Allow both 'BTCUSDT' and 'BTC/USDT'
    key = symbol.replace('/', '').upper()
    cg_id = SYMBOL_MAP.get(key)
    if not cg_id:
        raise Exception(f"Coin {symbol} not supported.")
    try:
        result = cg.get_price(ids=cg_id, vs_currencies='usd')
        return float(result[cg_id]['usd'])
    except Exception as e:
        raise Exception(f"Error retrieving price for {symbol}: {str(e)}")
