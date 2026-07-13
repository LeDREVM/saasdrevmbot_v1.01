# dashboard.py
from fastapi import FastAPI
import sqlite3
import plotly.graph_objects as go



app = FastAPI()

@app.get("/status")
def status():
    return {"bot": "running", "mode": "NY SMART MONEY SYSTEM"}


@app.get("/signals")
def get_signals():
    conn = sqlite3.connect("db.sqlite")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM signals ORDER BY id DESC LIMIT 20")
    data = cursor.fetchall()

    return {"signals": data}

@app.get("/chart")
def chart():

    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df["datetime"],
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"]
    ))

    # SUPPLY / DEMAND
    fig.add_hline(y=supply, line_dash="dash", line_color="red")
    fig.add_hline(y=demand, line_dash="dash", line_color="green")

    return fig.to_json()