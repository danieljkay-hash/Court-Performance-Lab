"""Command-line entry point.

  python -m trading_bot.cli backtest --symbol AAPL --start 2022-01-01 --end 2024-01-01
  python -m trading_bot.cli run --symbols AAPL,MSFT          # paper (default)
  python -m trading_bot.cli run --symbols AAPL --live        # real money (gated)
"""
from __future__ import annotations

import argparse
import logging
import sys

from .backtest import run_backtest
from .config import load_config
from .data import get_historical_bars
from .strategies.ma_crossover import MACrossover


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def cmd_backtest(args: argparse.Namespace) -> int:
    cfg = load_config()
    strategy = MACrossover(fast=cfg.fast_ma, slow=cfg.slow_ma)
    bars = get_historical_bars(
        args.symbol, cfg.timeframe, args.start, args.end,
        api_key=cfg.api_key, secret_key=cfg.secret_key,
    )
    result = run_backtest(
        bars, strategy, symbol=args.symbol,
        starting_cash=args.cash, commission=args.commission,
        slippage_bps=args.slippage_bps, timeframe=cfg.timeframe,
    )
    print(result.summary())
    if result.total_return < result.buy_hold_return:
        print(
            "NOTE: the strategy underperformed buy-and-hold over this window. "
            "That is common for naive crossovers. Don't deploy this expecting profit."
        )
    return 0


def _confirm_live() -> bool:
    print(
        "\n*** LIVE TRADING WITH REAL MONEY ***\n"
        "You can lose real capital. Have you validated this strategy in backtest "
        "and paper trading?\n"
        "Type exactly 'I ACCEPT THE RISK' to continue: ",
        end="",
    )
    return input().strip() == "I ACCEPT THE RISK"


def cmd_run(args: argparse.Namespace) -> int:
    cfg = load_config(force_live=args.live)
    if cfg.is_live and not _confirm_live():
        print("Live confirmation not given. Aborting.")
        return 1

    from .bot import TradingBot  # deferred so backtests don't need the SDK loaded

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    if not symbols:
        print("No symbols provided.", file=sys.stderr)
        return 2
    strategy = MACrossover(fast=cfg.fast_ma, slow=cfg.slow_ma)
    TradingBot(cfg, strategy, symbols).run()
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="trading_bot", description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    bt = sub.add_parser("backtest", help="Backtest the strategy on historical data")
    bt.add_argument("--symbol", required=True)
    bt.add_argument("--start", required=True, help="YYYY-MM-DD")
    bt.add_argument("--end", required=True, help="YYYY-MM-DD")
    bt.add_argument("--cash", type=float, default=10_000.0)
    bt.add_argument("--commission", type=float, default=0.0)
    bt.add_argument("--slippage-bps", type=float, default=5.0)
    bt.set_defaults(func=cmd_backtest)

    run = sub.add_parser("run", help="Run live/paper trading loop")
    run.add_argument("--symbols", required=True, help="Comma-separated, e.g. AAPL,MSFT")
    run.add_argument(
        "--live", action="store_true",
        help="Trade real money. Also requires TRADING_MODE=live in .env.",
    )
    run.set_defaults(func=cmd_run)
    return p


def main(argv: list[str] | None = None) -> int:
    _setup_logging()
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (ValueError, KeyboardInterrupt) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
