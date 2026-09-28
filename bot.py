import os
import json
import asyncio
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
ALERTS_FILE = "alerts.json"
CHECK_EVERY = 30  # seconds

HELP = (
    "Crypto price alert bot\n\n"
    "/price BTC - current price\n"
    "/alert BTC above 90000 - ping me when BTC goes above 90000\n"
    "/alert SOL below 120 - ping me when SOL drops below 120\n"
    "/alerts - my alerts\n"
    "/delete 1 - delete alert #1"
)


def load_alerts():
    if not os.path.exists(ALERTS_FILE):
        return []
    with open(ALERTS_FILE) as f:
        return json.load(f)


def save_alerts(alerts):
    with open(ALERTS_FILE, "w") as f:
        json.dump(alerts, f, indent=2)


def get_price(coin):
    # binance public api, no key needed
    try:
        r = requests.get(
            "https://api.binance.com/api/v3/ticker/price",
            params={"symbol": coin + "USDT"},
            timeout=10,
        )
    except requests.RequestException:
        return None
    if r.status_code != 200:
        return None
    return float(r.json()["price"])


def fmt(p):
    # big prices with commas, small ones (memecoins) with more digits
    if p >= 1:
        return f"${p:,.2f}"
    return "$" + f"{p:.10f}".rstrip("0").rstrip(".")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP)


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /price BTC")
        return
    coin = context.args[0].upper()
    p = await asyncio.to_thread(get_price, coin)
    if p is None:
        await update.message.reply_text(f"Can't find {coin} on Binance")
    else:
        await update.message.reply_text(f"{coin}: {fmt(p)}")


async def alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) != 3 or args[1].lower() not in ("above", "below"):
        await update.message.reply_text("Usage: /alert BTC above 90000")
        return
    coin = args[0].upper()
    direction = args[1].lower()
    try:
        target = float(args[2].replace(",", "."))
    except ValueError:
        await update.message.reply_text("Price should be a number")
        return

    now = await asyncio.to_thread(get_price, coin)
    if now is None:
        await update.message.reply_text(f"Can't find {coin} on Binance")
        return

    alerts = load_alerts()
    alerts.append({"chat_id": update.effective_chat.id, "coin": coin, "direction": direction, "target": target})
    save_alerts(alerts)
    await update.message.reply_text(f"Done. {coin} {direction} {fmt(target)} (now {fmt(now)})")


async def list_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat.id
    mine = [a for a in load_alerts() if a["chat_id"] == chat]
    if not mine:
        await update.message.reply_text("No alerts yet")
        return
    lines = [f"{i}. {a['coin']} {a['direction']} {fmt(a['target'])}" for i, a in enumerate(mine, 1)]
    await update.message.reply_text("\n".join(lines))


async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat.id
    alerts = load_alerts()
    mine = [a for a in alerts if a["chat_id"] == chat]
    try:
        n = int(context.args[0])
        a = mine[n - 1]
        if n < 1:
            raise IndexError
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /delete 1 (number from /alerts)")
        return
    alerts.remove(a)
    save_alerts(alerts)
    await update.message.reply_text(f"Deleted: {a['coin']} {a['direction']} {fmt(a['target'])}")


async def check_alerts(context: ContextTypes.DEFAULT_TYPE):
    alerts = load_alerts()
    if not alerts:
        return

    # one request per coin, not per alert
    prices = {}
    for coin in {a["coin"] for a in alerts}:
        prices[coin] = await asyncio.to_thread(get_price, coin)

    fired = []
    for a in alerts:
        p = prices.get(a["coin"])
        if p is None:
            continue
        hit = p >= a["target"] if a["direction"] == "above" else p <= a["target"]
        if hit:
            fired.append(a)
            emoji = "🚀" if a["direction"] == "above" else "🔻"
            try:
                await context.bot.send_message(
                    a["chat_id"],
                    f"{emoji} {a['coin']} is {a['direction']} {fmt(a['target'])}\nPrice now: {fmt(p)}",
                )
            except Exception as e:
                print("send failed:", e)

    if fired:
        # reload in case someone added an alert while we were checking
        alerts = load_alerts()
        for a in fired:
            if a in alerts:
                alerts.remove(a)
        save_alerts(alerts)


def main():
    if not TOKEN:
        raise SystemExit("Set BOT_TOKEN first (see README)")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler(["start", "help"], start))
    app.add_handler(CommandHandler("price", price))
    app.add_handler(CommandHandler("alert", alert))
    app.add_handler(CommandHandler("alerts", list_alerts))
    app.add_handler(CommandHandler("delete", delete))
    app.job_queue.run_repeating(check_alerts, interval=CHECK_EVERY, first=5)
    print("bot is running")
    app.run_polling()


if __name__ == "__main__":
    main()
