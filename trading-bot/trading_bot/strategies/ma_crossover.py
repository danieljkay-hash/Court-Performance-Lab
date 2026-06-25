"""Moving-average crossover strategy (long-only baseline)."""
from __future__ import annotations

import pandas as pd

from .base import Signal, Strategy


class MACrossover(Strategy):
    """Long when fast SMA > slow SMA, flat otherwise.

    This is a trend-following baseline. It tends to do well in persistent
    trends and bleed money in choppy, sideways markets via whipsaws. It is a
    starting point for learning, not a proven edge.
    """

    name = "ma_crossover"

    def __init__(self, fast: int = 20, slow: int = 50):
        if fast >= slow:
            raise ValueError(f"fast ({fast}) must be < slow ({slow})")
        self.fast = fast
        self.slow = slow

    @property
    def warmup(self) -> int:
        return self.slow

    def signals(self, bars: pd.DataFrame) -> pd.Series:
        close = bars["close"]
        fast_ma = close.rolling(self.fast).mean()
        slow_ma = close.rolling(self.slow).mean()
        # Desired position: long while fast is above slow.
        sig = (fast_ma > slow_ma).astype(int)
        # Bars inside the warmup window have an undefined slow MA -> stay flat.
        sig[slow_ma.isna()] = Signal.FLAT
        return sig.map(lambda v: Signal.LONG if v == 1 else Signal.FLAT)
