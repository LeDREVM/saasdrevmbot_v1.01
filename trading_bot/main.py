# main.py
from data_engine import get_data, PAIRS
from strategy_engine import analyze
from scoring_engine import score_signal
from telegram import send
from divergence_engine import detect_divergence
from smart_money_engine import smart_signal

div_signals = detect_divergences(df)
while True:
    for pair in PAIRS:

        df = get_data(pair)
        analysis = analyze(df)

        score, grade = score_signal(analysis, df)

        if analysis["signal"] != "NONE":

            msg = f"""
📊 {pair}

Price: {analysis['price']}
RSI: {analysis['rsi']:.2f}

Signal: {analysis['signal']}
Setup: {analysis['setup']}

Score: {score}
Grade: {grade}

NY STRATEGY ACTIVE
"""

            if grade == "A+":
                send("🔥 A+ SETUP DETECTED\n\n" + msg)
            elif grade == "A":
                send("⚡ A SETUP\n\n" + msg)

                


bias = get_bias_h4(df_h4)
zone_high, zone_low = get_zone_m15(df_m15)
trigger = entry_m5(df_m5)
wyckoff = detect_wyckoff(df_m5)

signal = None

# LOGIQUE INSTITUTIONNELLE
if bias == "BULLISH" and wyckoff == "SPRING" and trigger == "BUY_TRIGGER":
    signal = "BUY"

elif bias == "BEARISH" and wyckoff == "UTAD" and trigger == "SELL_TRIGGER":
    signal = "SELL"

if signal:
    execute_trade("EURUSD", signal, 0.1, sl, tp)             