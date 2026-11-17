# Fidelity Signal Bot

Two entry points, same strategy engine:

- **`main.py`** — advisory only. Reads your Fidelity holdings via Plaid
  (read-only) and texts you when a signal changes. **Never places a trade.**
  You decide whether to act on it in Fidelity yourself.
- **`auto_trade.py`** — fully automated. Trades a **separate, Alpaca**
  brokerage account directly (Fidelity has no public trading API, so full
  automation requires moving funds to a broker that supports one). Still
  texts you a confirmation after every order it places.

Nothing here is financial advice, and no strategy is a "best" algorithm —
moving-average/MACD/RSI confirmation is a well-known, conservative approach,
not a guarantee of profit. Past performance of any strategy does not predict
future results.

## How the strategy works

- **Trend filter:** SMA(fast) vs SMA(slow), default 20 vs 50 days.
- **Momentum confirmation:** a fresh MACD line/signal-line crossover.
- **Guard rail:** RSI must not already be overbought (for a BUY) or oversold
  (for a SELL).

A BUY or SELL only fires when the trend and the MACD crossover agree in the
same run. Everything else is HOLD. You're only texted when a symbol's signal
*changes* from the last run, so you won't get the same text every day.

Tune thresholds via environment variables (see `.env.example`).

## One-time setup

### 1. Plaid (holdings, read-only)
1. Create a free account at https://dashboard.plaid.com and grab your
   `client_id` and `secret` for the **Sandbox** environment first.
2. Put those in `.env` as `PLAID_CLIENT_ID` / `PLAID_SECRET`, `PLAID_ENV=sandbox`.
3. Run `python scripts/plaid_link.py`, open http://localhost:5000, click
   "Link Fidelity account". **You log into Fidelity inside Plaid's own secure
   widget** — this app never sees your Fidelity username or password.
4. Copy the access token it prints into `.env` as `PLAID_ACCESS_TOKEN`.
5. Once that works end-to-end in Sandbox, apply for Plaid **Production**
   access (required to link your real account — Plaid reviews this), switch
   `PLAID_ENV=production`, and repeat the link step for real.

### 2. Alpha Vantage (price history)
Get a free API key at https://www.alphavantage.co/support/#api-key and set
`ALPHAVANTAGE_API_KEY`. The free tier is rate-limited (25 requests/day) —
`main.py` already spaces requests out, but if you hold more than ~20-25
symbols you'll want a paid Alpha Vantage tier.

### 2b. Alpaca (only if you want `auto_trade.py` to trade for you)
Fidelity has no API for placing orders, so full automation means funding a
*different* account at a broker that supports it.

1. Create an account at https://alpaca.markets. You get a **paper trading**
   account automatically (simulated money, real market data) — start there.
2. Grab the paper account's API key/secret, set `ALPACA_API_KEY` /
   `ALPACA_SECRET_KEY`, and leave `ALPACA_PAPER=true`.
3. Set `WATCHLIST_SYMBOLS` to the tickers you want it allowed to open new
   positions in.
4. Run `python auto_trade.py` on a schedule (or manually) for at least a
   few weeks. Watch the printed log and the texted confirmations. Check
   Alpaca's dashboard to see what it actually did.
5. **Only once you're comfortable with its behavior:** fund a *live* Alpaca
   account with real money (a transfer you initiate yourself in Alpaca's
   UI), switch to the live API key/secret, and set `ALPACA_PAPER=false`.

Built-in safety limits (tune in `.env`):
- `POSITION_SIZE_PCT` — max fraction of account equity per new BUY (default 5%).
- `MAX_DAILY_LOSS_PCT` — daily loss kill switch (default 3%). Once tripped,
  it places zero new orders for the rest of that run and just texts you.

These are basic guardrails, not a substitute for watching the account. There
is no limit on how many *different* symbols in `WATCHLIST_SYMBOLS` can signal
BUY in the same run, so a volatile watchlist can still deploy more capital in
one day than you might expect — keep the watchlist short while you're
building confidence.

### 2c. Optional: let it pick new stocks beyond your watchlist (screener)
By default `auto_trade.py` only ever trades `WATCHLIST_SYMBOLS` plus whatever
it's currently holding — it never looks for anything else. Setting
`SCREENER_ENABLED=true` turns on an additional scan of the S&P 500
(`app/sp500_tickers.txt`, a static snapshot — refresh it periodically) for
fresh BUY signals using the exact same strategy, and can open up to
`MAX_NEW_SCREENER_POSITIONS` brand-new positions per run in companies you
never explicitly chose.

This is a meaningfully bigger risk surface than the fixed watchlist: more
unfamiliar names, more capital in play, no "I recognize this company" check
from you. It's off by default — only turn it on after you've watched the
watchlist-only behavior for a while and trust it, and start with a low
`MAX_NEW_SCREENER_POSITIONS` (default 3).

### 3. Twilio (SMS)
Create an account at https://www.twilio.com, buy a phone number (~$1/mo),
and set `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`
(your Twilio number), and `TWILIO_TO_NUMBER` (your cell, e.g. `+15551234567`).

### 4. Run it locally first
```bash
pip install -r requirements.txt
python main.py          # advisory: Fidelity holdings, texts only
python auto_trade.py    # automated: trades your (paper) Alpaca account
```
Confirm you see sensible BUY/HOLD/SELL output before deploying either one.

## Deploying to Railway

1. Push this repo to GitHub, then create a new Railway project from it.
2. Add all the `.env` variables as Railway environment variables/secrets
   (never commit your real `.env`). Set `STATE_FILE=/data/state.json` to
   match the volume below.
3. Add a **Volume** mounted at `/data` so `state.json` persists between cron
   runs — otherwise every run looks like a fresh signal and you'll get
   duplicate texts/orders.
4. Set the service's cron schedule (weekdays ~4:05pm ET, i.e. shortly after
   market close — adjust for daylight saving). The Dockerfile defaults to
   running `auto_trade.py`; override the start command to `python main.py`
   if you want the advisory-only script instead.

## Limitations, read before relying on this

- Plaid's Investments product can lag real-time Fidelity data by hours.
- Alpha Vantage free tier is end-of-day data only, not intraday.
- This strategy is a conservative, well-documented combination of classic
  indicators — it is **not** a "best" algorithm and has no guarantee of
  future performance. Backtest it against historical data before trusting
  it with real decisions.
- `auto_trade.py` runs unattended and spends real money once `ALPACA_PAPER`
  is false. The kill switch and position-size cap reduce how much a bad
  day or a bug can cost you, but they don't eliminate the risk. Treat
  `ALPACA_PAPER=true` as the default, not a formality — give it real time
  in paper mode before trusting it with a live account, and only fund the
  live account with money you can afford to lose.
