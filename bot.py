import ccxt
import pandas as pd
import requests
import json
import os
from datetime import datetime, timezone

# ===============================
# 🔐 TELEGRAM CONFIG
# ===============================
BOT_TOKEN = "8364584748:AAFeym3et4zJwmdKRxYtP3ieIKV8FuPWdQ8"
CHAT_ID = "@Tradecocom"

# ===============================
# ⚙️ SETTINGS
# ===============================
PAIRS = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT"]
TIMEFRAMES = ["5m", "15m", "30m", "1h", "4h", "1d"]
LOOKBACK = 15
STATE_FILE = "state.json"

# ===============================
# 🔁 EXCHANGE
# ===============================
exchange = ccxt.mexc({"enableRateLimit": True})

# ===============================
# 📦 STATE HANDLING
# ===============================
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

# ===============================
# 📨 TELEGRAM ALERT
# ===============================
def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    requests.post(url, json=payload, timeout=10)

# ===============================
# 📊 FETCH DATA
# ===============================
def fetch_data(symbol, timeframe):
    candles = exchange.fetch_ohlcv(
        symbol,
        timeframe=timeframe,
        limit=LOOKBACK + 5
    )
    return pd.DataFrame(
        candles,
        columns=["time", "open", "high", "low", "close", "volume"]
    )

# ===============================
# 🚀 CHECK SIGNAL
# ===============================
def check_signal(symbol, timeframe, state):
    df = fetch_data(symbol, timeframe)

    prev = df.iloc[-3]
    curr = df.iloc[-2]  # last CLOSED candle

    swing_high = df["high"].iloc[-(LOOKBACK + 2):-2].max()
    swing_low = df["low"].iloc[-(LOOKBACK + 2):-2].min()

    candle_time = str(int(curr.time))
    key = f"{symbol}_{timeframe}"

    if state.get(key) == candle_time:
        return

    utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    if prev.close <= swing_high and curr.close > swing_high:
        send_telegram(
            f"🚀 <b>BULLISH BREAKOUT</b>\n\n"
            f"📊 Pair: {symbol}\n"
            f"⏱ Timeframe: {timeframe}\n"
            f"📈 Level: {swing_high:.4f}\n"
            f"💰 Close: {curr.close:.4f}\n"
            f"🕒 UTC: {utc}"
        )
        state[key] = candle_time

    elif prev.close >= swing_low and curr.close < swing_low:
        send_telegram(
            f"🩸 <b>BEARISH BREAKDOWN</b>\n\n"
            f"📊 Pair: {symbol}\n"
            f"⏱ Timeframe: {timeframe}\n"
            f"📉 Level: {swing_low:.4f}\n"
            f"💰 Close: {curr.close:.4f}\n"
            f"🕒 UTC: {utc}"
        )
        state[key] = candle_time

# ===============================
# ▶️ MAIN
# ===============================
def main():
    # 🔔 Send message ONLY on manual run
    if os.getenv("GITHUB_EVENT_NAME") == "workflow_dispatch":
        utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        send_telegram(
            "🤖 <b>Bot Started Successfully</b>\n\n"
            "▶️ Trigger: Manual Run\n"
            "⏱ Auto Scan: Every 15 Minutes\n"
            f"🕒 UTC: {utc}\n\n"
            "📡 Monitoring markets..."
        )

    state = load_state()

    for pair in PAIRS:
        for tf in TIMEFRAMES:
            try:
                check_signal(pair, tf, state)
            except Exception as e:
                print(f"Error {pair} {tf}: {e}")

    save_state(state)

if __name__ == "__main__":
    main()
