"""Vectorized backtester with fees and slippage.

Honest accounting matters more than a pretty equity curve. We:
- act on the *next* bar's open (no look-ahead on the signal bar),
- charge slippage on every fill,
- charge a commission per trade,
- compare against buy-and-hold so you can see whether the strategy actually
  beat just holding the asset.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .strategies.base import Signal, Strategy


@dataclass
class BacktestResult:
    symbol: str
    start_equity: float
    end_equity: float
    total_return: float
    buy_hold_return: float
    max_drawdown: float
    sharpe: float
    num_trades: int
    win_rate: float
    equity_curve: pd.Series

    def summary(self) -> str:
        return (
            f"Backtest: {self.symbol}\n"
            f"  Start equity:     ${self.start_equity:,.2f}\n"
            f"  End equity:       ${self.end_equity:,.2f}\n"
            f"  Strategy return:  {self.total_return:+.2%}\n"
            f"  Buy & hold:       {self.buy_hold_return:+.2%}\n"
            f"  Max drawdown:     {self.max_drawdown:.2%}\n"
            f"  Sharpe (ann.):    {self.sharpe:.2f}\n"
            f"  Trades:           {self.num_trades}\n"
            f"  Win rate:         {self.win_rate:.2%}\n"
        )


_PERIODS_PER_YEAR = {
    "1Min": 252 * 390,
    "5Min": 252 * 78,
    "15Min": 252 * 26,
    "1Hour": 252 * 7,
    "1Day": 252,
}


def run_backtest(
    bars: pd.DataFrame,
    strategy: Strategy,
    symbol: str = "?",
    starting_cash: float = 10_000.0,
    commission: float = 0.0,
    slippage_bps: float = 5.0,
    timeframe: str = "1Day",
) -> BacktestResult:
    """Simulate `strategy` over `bars`.

    slippage_bps: basis points of adverse price impact applied to each fill.
    commission: flat $ per trade (entry and exit each count as a trade).
    """
    if len(bars) <= strategy.warmup + 1:
        raise ValueError(
            f"Not enough bars ({len(bars)}) for warmup ({strategy.warmup})."
        )

    close = bars["close"].to_numpy(dtype=float)
    open_ = bars["open"].to_numpy(dtype=float)
    desired = strategy.signals(bars).to_numpy(dtype=int)

    # Execute on the NEXT bar's open to avoid look-ahead: the signal computed at
    # the close of bar i is acted on at the open of bar i+1.
    slip = slippage_bps / 10_000.0
    cash = starting_cash
    shares = 0.0
    position = Signal.FLAT
    equity_curve = np.empty(len(bars))
    trade_returns: list[float] = []
    entry_price = 0.0
    num_trades = 0

    for i in range(len(bars)):
        # Mark-to-market on the current close.
        equity_curve[i] = cash + shares * close[i]

        if i == 0:
            continue
        target = Signal(desired[i - 1])  # signal from previous bar's close
        fill = open_[i]

        if target == Signal.LONG and position == Signal.FLAT:
            buy_price = fill * (1 + slip)
            shares = (cash - commission) / buy_price if buy_price > 0 else 0.0
            cash -= shares * buy_price + commission
            entry_price = buy_price
            position = Signal.LONG
            num_trades += 1
        elif target == Signal.FLAT and position == Signal.LONG:
            sell_price = fill * (1 - slip)
            cash += shares * sell_price - commission
            trade_returns.append((sell_price - entry_price) / entry_price)
            shares = 0.0
            position = Signal.FLAT
            num_trades += 1

    end_equity = cash + shares * close[-1]
    curve = pd.Series(equity_curve, index=bars.index)

    total_return = end_equity / starting_cash - 1
    buy_hold_return = close[-1] / close[0] - 1

    running_max = np.maximum.accumulate(equity_curve)
    drawdowns = (equity_curve - running_max) / running_max
    max_drawdown = float(drawdowns.min())

    rets = pd.Series(equity_curve).pct_change().dropna()
    ppy = _PERIODS_PER_YEAR.get(timeframe, 252)
    if rets.std(ddof=0) > 0:
        sharpe = float(rets.mean() / rets.std(ddof=0) * np.sqrt(ppy))
    else:
        sharpe = 0.0

    wins = sum(1 for r in trade_returns if r > 0)
    win_rate = wins / len(trade_returns) if trade_returns else 0.0

    return BacktestResult(
        symbol=symbol,
        start_equity=starting_cash,
        end_equity=end_equity,
        total_return=total_return,
        buy_hold_return=buy_hold_return,
        max_drawdown=max_drawdown,
        sharpe=sharpe,
        num_trades=num_trades,
        win_rate=win_rate,
        equity_curve=curve,
    )
