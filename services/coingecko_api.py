import requests
import pandas as pd
import time

def find_coin_id(query: str) -> str | None:

    query = query.lower().strip()
    url = "https://api.coingecko.com/api/v3/search"
    params = {"query": query}
    try:
        r = requests.get(url, params=params)
        r.raise_for_status()
        data = r.json()
        time.sleep(1)
        coins = data.get("coins", [])
        if not coins:
            return None
        for coin in coins:
            if coin["id"].lower() == query:
                return coin["id"]
            if coin["symbol"].lower() == query:
                return coin["id"]
        return coins[0]["id"]
    except requests.exceptions.RequestException as e:
        print(f"Error searching coin: {e}")
        return None

def fetch_price_history(coin_id: str, days: int = 14) -> pd.DataFrame:

    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {"vs_currency": "usd", "days": days}
    try:
        r = requests.get(url, params=params)
        r.raise_for_status()
        data = r.json()
        time.sleep(1)
        prices = data.get("prices", [])
        df = pd.DataFrame(prices, columns=["timestamp", "price"])
        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching price history: {e}")
        return pd.DataFrame()
    return df

def fetch_market_data(coin_id: str) -> dict | None:

    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {"vs_currency": "usd", "ids": coin_id}
    try:
        r = requests.get(url, params=params)
        r.raise_for_status()
        data = r.json()
        time.sleep(1)
        if data:
            return data[0]
    except requests.exceptions.RequestException as e:
        print(f"Error fetching market data: {e}")
        return None
    return None

def fetch_ohlc_history(coin_id: str, days: int) -> pd.DataFrame:

    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc"
    params = {"vs_currency": "usd", "days": days}
    try:
        r = requests.get(url, params=params)
        r.raise_for_status()
        data = r.json()
        time.sleep(1)
        df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close"])
        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching OHLC data: {e}")
        return pd.DataFrame()
    return df
