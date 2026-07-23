# scoring_engine.py



def ny_killzone():
    from datetime import datetime
    hour = datetime.utcnow().hour
    return 13 <= hour <= 16

def score_signal(data, df):
    score = 0

    rsi = data["rsi"]
    price = data["price"]

    high = df["close"].rolling(20).max().iloc[-1]
    low = df["close"].rolling(20).min().iloc[-1]

    # RSI EXTREME
    if rsi < 30 or rsi > 70:
        score += 2

    # LIQUIDITY SWEEP
    if price <= low or price >= high:
        score += 3

    # STRONG TREND CONTEXT
    if df["close"].iloc[-1] > df["close"].iloc[-5]:
        score += 1

    # NY SESSION BONUS
    score += 2

    grade = "C"
    if score >= 7:
        grade = "A+"
    elif score >= 5:
        grade = "A"
    elif score >= 3:
        grade = "B"

    return score, grade

if div_signal:
    score += 3



if "DIVERGENCE" in div_signals:
    score += 3

if "HIDDEN" in div_signals:
    score += 2

if len(div_signals) >= 2:
    score += 2  # double divergence = sniper    