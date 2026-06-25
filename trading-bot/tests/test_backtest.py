"""Offline tests: no API keys, no network. Validates strategy + backtester."""
import numpy as np
import pandas as pd

from trading_bot.backtest import run_backtest
from trading_bot.strategies.base import Signal
from trading_bot.strategies.ma_crossover import MACrossover


def _synthetic_bars(n=400, seed=7):
    # A trending series with noise so the crossover actually trades.
    rng = np.random.default_rng(seed)
    trend = np.linspace(100, 160, n)
    noise = np.cumsum(rng.normal(0, 1.0, n))
    close = trend + noise
    idx = pd.date_range("2022-01-01", periods=n, freq="D")
    return pd.DataFrame(
        {"open": close, "high": close + 1, "low": close - 1,
         "close": close, "volume": 1000},
        index=idx,
    )


def test_signals_are_valid_and_flat_during_warmup():
    bars = _synthetic_bars()
    strat = MACrossover(fast=20, slow=50)
    sig = strat.signals(bars)
    assert len(sig) == len(bars)
    assert set(sig.unique()) <= {Signal.FLAT, Signal.LONG}
    # No reliable signal before the slow MA exists.
    assert (sig.iloc[: strat.warmup - 1] == Signal.FLAT).all()


def test_backtest_runs_and_reports():
    bars = _synthetic_bars()
    strat = MACrossover(fast=20, slow=50)
    res = run_backtest(bars, strat, symbol="TEST", starting_cash=10_000)
    assert res.start_equity == 10_000
    assert res.end_equity > 0
    assert res.num_trades >= 1
    assert -1.0 <= res.max_drawdown <= 0.0
    assert 0.0 <= res.win_rate <= 1.0


def test_no_lookahead_flat_strategy_keeps_cash():
    # A strategy that never goes long must end with exactly the starting cash.
    class AlwaysFlat(MACrossover):
        def signals(self, bars):
            return pd.Series(Signal.FLAT, index=bars.index)

    bars = _synthetic_bars()
    res = run_backtest(bars, AlwaysFlat(20, 50), starting_cash=10_000)
    assert res.num_trades == 0
    assert abs(res.end_equity - 10_000) < 1e-6


def test_fast_must_be_below_slow():
    try:
        MACrossover(fast=50, slow=20)
    except ValueError:
        return
    raise AssertionError("expected ValueError for fast >= slow")
