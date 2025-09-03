import os
import json
import time
import requests
import yfinance as yf
import websocket
from datetime import datetime, timedelta
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, CallbackContext

# ==============================================================
# 🔑 Hardcoded Secrets (your real tokens & IDs)
# ==============================================================

TELEGRAM_BOT_TOKEN = "7599608446:AAEtDw54jnH7GVDl57q-QtmwwD_cTrweVMs"
TELEGRAM_CHAT_ID = "6372242153"

# Price source setup
PRICE_SOURCE = "DERIV"  # Options: DERIV, YAHOO, OANDA

# Deriv API
DERIV_API_TOKEN = "49rcp63A2W1X9EY"
DERIV_APP_ID = "1089"

# OANDA (optional, leave blank if not using)
OANDA_API_KEY = ""
OANDA_ACCOUNT_ID = ""

# ==============================================================

# Telegram bot setup
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Store POIs in memory (can extend to file/db)
POIS = {}

def save_pois():
    with open("pois.json", "w") as f:
        json.dump(POIS, f)

def load_pois():
    global POIS
    try:
        with open("pois.json", "r") as f:
            POIS = json.load(f)
    except:
        POIS = {}

# ==============================================================
# 📌 Telegram Commands
# ==============================================================

def start(update: Update, context: CallbackContext):
    update.message.reply_text("✅ Processunit bot is live!\nUse /help for commands.")

def help_cmd(update: Update, context: CallbackContext):
    update.message.reply_text(
        "/add <PAIR> <PRICE> - Add POI\n"
        "/remove <PAIR> - Remove POI\n"
        "/list - List POIs\n"
        "/summary - Daily summary"
    )

def add_poi(update: Update, context: CallbackContext):
    try:
        pair = context.args[0].upper()
        price = float(context.args[1])
        if pair not in POIS:
            POIS[pair] = []
        POIS[pair].append(price)
        save_pois()
        update.message.reply_text(f"✅ Added POI {price} for {pair}")
    except:
        update.message.reply_text("Usage: /add EURUSD 1.0850")

def remove_poi(update: Update, context: CallbackContext):
    try:
        pair = context.args[0].upper()
        if pair in POIS:
            del POIS[pair]
            save_pois()
            update.message.reply_text(f"❌ Removed POIs for {pair}")
        else:
            update.message.reply_text("No POIs for that pair")
    except:
        update.message.reply_text("Usage: /remove EURUSD")

def list_pois(update: Update, context: CallbackContext):
    if not POIS:
        update.message.reply_text("📭 No POIs set.")
        return
    text = "📌 Current POIs:\n"
    for pair, prices in POIS.items():
        text += f"{pair}: {prices}\n"
    update.message.reply_text(text)

def summary(update: Update, context: CallbackContext):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    update.message.reply_text(f"📊 Daily summary for {today}\nPOIs: {json.dumps(POIS)}")

# ==============================================================
# 📌 Price Checkers (Deriv, Yahoo, OANDA)
# ==============================================================

def check_price_yahoo(pair):
    ticker = yf.Ticker(pair + "=X")
    data = ticker.history(period="1d", interval="15m")
    if not data.empty:
        return data["Close"].iloc[-1]
    return None

def check_price_deriv(pair):
    try:
        url = "wss://ws.derivws.com/websockets/v3?app_id=" + DERIV_APP_ID
        ws = websocket.create_connection(url)
        ws.send(json.dumps({"ticks_history": pair, "count": 1, "end": "latest", "granularity": 900, "style": "candles"}))
        result = json.loads(ws.recv())
        ws.close()
        candle = result["candles"][-1]
        return float(candle["close"])
    except:
        return None

def check_price(pair):
    if PRICE_SOURCE == "DERIV":
        return check_price_deriv(pair)
    elif PRICE_SOURCE == "YAHOO":
        return check_price_yahoo(pair)
    else:
        return None

# ==============================================================
# 📌 Main loop
# ==============================================================

def monitor():
    while True:
        for pair, levels in POIS.items():
            price = check_price(pair)
            if price:
                for level in levels:
                    if abs(price - level) < 0.0005:
                        bot.send_message(
                            chat_id=TELEGRAM_CHAT_ID,
                            text=f"🚨 {pair} reached POI {level} (current {price})"
                        )
        time.sleep(60)

# ==============================================================
# 📌 Run Bot
# ==============================================================

def main():
    load_pois()
    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_cmd))
    dp.add_handler(CommandHandler("add", add_poi))
    dp.add_handler(CommandHandler("remove", remove_poi))
    dp.add_handler(CommandHandler("list", list_pois))
    dp.add_handler(CommandHandler("summary", summary))

    updater.start_polling()
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text="✅ Processunit bot is online")
    monitor()

if __name__ == "__main__":
    main()
