"""Parameter sweep: grid-search MA-crossover params over historical data.

Ranks (fast, slow) combinations by a chosen metric so you can see how
sensitive results are to parameters. A combo that only looks good at one exact
setting and is bad everywhere around it is almost certainly overfit noise —
prefer robust plateaus over lonely peaks.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .backtest import run_backtest
from .strategies.ma_crossover import MACrossover


@dataclass
class SweepRow:
    fast: int
    slow: int
    total_return: float
    buy_hold_return: float
    sharpe: float
    max_drawdown: float
    num_trades: int


def sweep_ma_crossover(
    bars: pd.DataFrame,
    fasts: list[int],
    slows: list[int],
    symbol: str = "?",
    starting_cash: float = 10_000.0,
    commission: float = 0.0,
    slippage_bps: float = 5.0,
    timeframe: str = "1Day",
    metric: str = "sharpe",
) -> pd.DataFrame:
    """Return a DataFrame of results sorted by `metric` (descending)."""
    valid_metrics = {"sharpe", "total_return", "max_drawdown"}
    if metric not in valid_metrics:
        raise ValueError(f"metric must be one of {valid_metrics}")

    rows: list[SweepRow] = []
    for fast in fasts:
        for slow in slows:
            if fast >= slow:
                continue
            if len(bars) <= slow + 1:
                continue
            res = run_backtest(
                bars, MACrossover(fast=fast, slow=slow), symbol=symbol,
                starting_cash=starting_cash, commission=commission,
                slippage_bps=slippage_bps, timeframe=timeframe,
            )
            rows.append(SweepRow(
                fast=fast, slow=slow,
                total_return=res.total_return,
                buy_hold_return=res.buy_hold_return,
                sharpe=res.sharpe,
                max_drawdown=res.max_drawdown,
                num_trades=res.num_trades,
            ))

    if not rows:
        raise ValueError("No valid (fast, slow) combinations for this data length.")

    df = pd.DataFrame(r.__dict__ for r in rows)
    ascending = metric == "max_drawdown"  # less-negative drawdown is better
    return df.sort_values(metric, ascending=ascending).reset_index(drop=True)
