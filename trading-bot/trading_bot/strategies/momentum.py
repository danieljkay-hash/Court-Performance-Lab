"""Time-series momentum strategy (long-only baseline).

Holds the asset when its trailing return over a lookback window is positive,
goes flat when it's negative. The classic "trend persists" bet. Closely related
to MA-crossover but expressed directly as a return threshold. Strong in
trending regimes, whipsawed in flat ones. A learning baseline, not an edge.
"""
from __future__ import annotations

import pandas as pd

from .base import Signal, Strategy


class Momentum(Strategy):
    name = "momentum"

    def __init__(self, lookback: int = 90, threshold: float = 0.0):
        if lookback < 2:
            raise ValueError("lookback must be >= 2")
        self.lookback = lookback
        self.threshold = threshold

    @property
    def warmup(self) -> int:
        return self.lookback

    def signals(self, bars: pd.DataFrame) -> pd.Series:
        close = bars["close"]
        trailing_return = close / close.shift(self.lookback) - 1
        sig = (trailing_return > self.threshold).astype(int)
        sig[trailing_return.isna()] = 0  # warmup
        return sig.map(lambda v: Signal.LONG if v == 1 else Signal.FLAT)
