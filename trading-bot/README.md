# Trading Bot (Stocks/ETFs, Alpaca)

An honest, risk-managed automated trading bot for US equities. It executes a
**moving-average crossover** strategy through [Alpaca](https://alpaca.markets),
and is built around a simple, non-negotiable workflow:

> **Backtest → Paper trade → (only then) Live, with small size.**

## ⚠️ Read this first

- **No bot is guaranteed to make money.** This one isn't either. A bot only
  automates a *strategy*. The strategy is the edge — or the loss. The default
  MA-crossover strategy is a *baseline for learning*, not a money printer. On
  most assets and timeframes a naive crossover loses to buy-and-hold after fees
  and slippage. Treat any profit as unproven until you've backtested and
  paper-traded it yourself.
- **You can lose money, including real money in live mode.** Trade only capital
  you can afford to lose.
- **Live mode is opt-in and gated.** The bot runs against Alpaca's *paper*
  endpoint unless you explicitly set `TRADING_MODE=live` and provide live keys.

## Setup

```bash
cd trading-bot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in your Alpaca keys
```

Get free API keys at <https://app.alpaca.markets/> (paper keys are free and
require no funding).

## Usage

```bash
# 1. Backtest the strategy on historical data (no keys needed for cached CSV;
#    Alpaca keys needed to pull fresh data)
python -m trading_bot.cli backtest --symbol AAPL --start 2022-01-01 --end 2024-01-01

# 2. Paper trade live (simulated money, real prices) — this is the default mode
python -m trading_bot.cli run --symbols AAPL,MSFT

# 3. Live trade (REAL money). Requires TRADING_MODE=live in .env and a typed
#    confirmation. Do not do this until paper results convince you.
python -m trading_bot.cli run --symbols AAPL --live
```

## Strategy

**Moving-average crossover** (`strategies/ma_crossover.py`):
- Go long when the fast SMA crosses **above** the slow SMA.
- Exit (flat) when the fast SMA crosses **below** the slow SMA.
- Long-only by default (no shorting).

Swap in your own logic by subclassing `Strategy` in `strategies/base.py`.

## Risk controls (`risk.py`)

All enforced on every order:
- **Max position size** as a fraction of equity (`MAX_POSITION_PCT`).
- **Per-trade stop loss** (`STOP_LOSS_PCT`).
- **Max concurrent open positions** (`MAX_OPEN_POSITIONS`).
- **Daily loss kill-switch** (`MAX_DAILY_LOSS_PCT`) — halts new entries for the
  day once breached.

## Layout

```
trading_bot/
  config.py        # env-driven settings, paper/live gate
  data.py          # historical + latest bars (Alpaca / CSV cache)
  broker.py        # thin Alpaca trading wrapper
  risk.py          # position sizing + risk limits
  backtest.py      # vectorized backtester with fees/slippage
  strategies/
    base.py        # Strategy interface
    ma_crossover.py
  bot.py           # live/paper run loop
  cli.py           # command-line entry point
```

## Disclaimer

This software is for educational purposes. It is not financial advice. The
authors accept no liability for trading losses. Markets are risky; automated
systems can fail in unexpected ways (bugs, outages, data errors, flash crashes).
Use stop-losses, start in paper mode, and never risk money you can't lose.
