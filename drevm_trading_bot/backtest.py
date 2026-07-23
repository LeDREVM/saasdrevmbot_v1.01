# backtest.py
def backtest(df):
    wins = 0
    losses = 0

    for i in range(50, len(df)-1):
        rsi = df["rsi"].iloc[i]
        price = df["close"].iloc[i]

        future = df["close"].iloc[i+1]

        if rsi < 30:
            if future > price:
                wins += 1
            else:
                losses += 1

        elif rsi > 70:
            if future < price:
                wins += 1
            else:
                losses += 1

    return {
        "wins": wins,
        "losses": losses,
        "winrate": wins / (wins + losses) * 100
    }