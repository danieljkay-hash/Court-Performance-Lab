"""Offline tests for the additional strategies, registry, and sweep."""
import numpy as np
import pandas as pd

from trading_bot.backtest import run_backtest
from trading_bot.strategies import available, build_strategy
from trading_bot.strategies.base import Signal
from trading_bot.strategies.momentum import Momentum
from trading_bot.strategies.rsi_reversion import RSIReversion, rsi
from trading_bot.sweep import sweep_ma_crossover


def _bars(n=400, seed=3):
    rng = np.random.default_rng(seed)
    # Mean-reverting-ish series so RSI actually triggers.
    close = 100 + np.cumsum(rng.normal(0, 1.0, n))
    close = np.clip(close, 5, None)
    idx = pd.date_range("2022-01-01", periods=n, freq="D")
    return pd.DataFrame(
        {"open": close, "high": close + 1, "low": close - 1,
         "close": close, "volume": 1000},
        index=idx,
    )


def test_rsi_bounded_0_100():
    r = rsi(_bars()["close"], 14).dropna()
    assert (r >= 0).all() and (r <= 100).all()


def test_strategies_emit_valid_signals():
    bars = _bars()
    for strat in (RSIReversion(), Momentum(lookback=60)):
        sig = strat.signals(bars)
        assert len(sig) == len(bars)
        assert set(sig.unique()) <= {Signal.FLAT, Signal.LONG}
        # flat during warmup
        assert (sig.iloc[: strat.warmup - 1] == Signal.FLAT).all()


def test_registry_builds_all():
    class FakeCfg:
        fast_ma, slow_ma = 20, 50

    names = available()
    assert {"ma_crossover", "rsi_reversion", "momentum"} <= set(names)
    for name in names:
        strat = build_strategy(name, FakeCfg())
        run_backtest(_bars(), strat, symbol="T")  # should not raise


def test_sweep_returns_sorted_table():
    bars = _bars()
    table = sweep_ma_crossover(bars, [5, 10], [40, 50], symbol="T", metric="sharpe")
    assert len(table) == 4  # 2x2, all valid (fast<slow)
    # sorted descending by sharpe
    assert list(table["sharpe"]) == sorted(table["sharpe"], reverse=True)
