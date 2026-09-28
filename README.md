# crypto-alert-bot

Telegram bot that pings you when a coin hits your price. Prices come from the Binance public API (no API key needed).

## Commands
```
/price BTC               current price
/alert BTC above 90000   alert when BTC goes above 90k
/alert SOL below 120     alert when SOL drops below 120
/alerts                  list your alerts
/delete 1                delete alert #1
```

Checks prices every 30 sec. Each alert fires once and then gets removed. Alerts are saved to `alerts.json` so they survive a restart.

## Run it
1. Create a bot with [@BotFather](https://t.me/BotFather) and copy the token
2. Install deps:
```
pip install -r requirements.txt
```
3. Start:
```
export BOT_TOKEN=your_token_here
python bot.py
```

## Todo
- percent change alerts (e.g. BTC -5% in 1h)
- support for other exchanges
good luck☺️
