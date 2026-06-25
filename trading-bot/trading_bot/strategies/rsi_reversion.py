"""RSI mean-reversion strategy (long-only baseline).

Buys oversold dips and exits once the bounce reaches a neutral/overbought
level. Mean-reversion is the opposite temperament to trend-following: it tends
to do well in choppy, range-bound markets and get steamrolled in strong trends
(it sells winners early and keeps buying into downtrends). Another baseline for
learning, not a proven edge.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .base import Signal, Strategy


def rsi(close: pd.Series, period: int) -> pd.Series:
    """Wilder's RSI."""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    # Wilder smoothing == EWM with alpha = 1/period.
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    out = 100 - 100 / (1 + rs)
    # avg_loss == 0 means no down moves -> RSI 100.
    out[avg_loss == 0] = 100.0
    return out


class RSIReversion(Strategy):
    name = "rsi_reversion"

    def __init__(self, period: int = 14, oversold: float = 30.0, exit_level: float = 55.0):
        if not 0 < oversold < exit_level < 100:
            raise ValueError("require 0 < oversold < exit_level < 100")
        self.period = period
        self.oversold = oversold
        self.exit_level = exit_level

    @property
    def warmup(self) -> int:
        return self.period + 1

    def signals(self, bars: pd.DataFrame) -> pd.Series:
        r = rsi(bars["close"], self.period)
        # Stateful: enter long when RSI dips below oversold, hold until it
        # recovers above exit_level. Vectorized as a forward-filled state.
        enter = r < self.oversold
        exit_ = r > self.exit_level
        state = pd.Series(np.nan, index=bars.index)
        state[enter] = 1.0
        state[exit_] = 0.0
        state = state.ffill().fillna(0.0)
        state[r.isna()] = 0.0  # warmup
        return state.map(lambda v: Signal.LONG if v == 1.0 else Signal.FLAT)
