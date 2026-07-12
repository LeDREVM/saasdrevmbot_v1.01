# data_engine.py
import requests
import pandas as pd

API_KEY = "YOUR_TWELVEDATA_KEY"

PAIRS = ["EUR/USD", "GBP/JPY", "XAU/USD", "USD/CAD"]

def get_data(symbol, interval="5min"):
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&apikey={API_KEY}&outputsize=200"
    data = requests.get(url).json()["values"]

    df = pd.DataFrame(data)
    df = df.iloc[::-1]
    df["close"] = df["close"].astype(float)

    return df