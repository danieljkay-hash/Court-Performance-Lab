"""Strategy interface.

A strategy turns a price history into a target position signal. Keep strategies
pure (no I/O, no order placement) so they can be backtested and unit-tested.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from enum import IntEnum

import pandas as pd


class Signal(IntEnum):
    FLAT = 0   # hold no position / exit
    LONG = 1   # hold a long position


class Strategy(ABC):
    name: str = "base"

    @abstractmethod
    def signals(self, bars: pd.DataFrame) -> pd.Series:
        """Return a Signal per row of `bars`.

        `bars` is indexed by timestamp with at least a 'close' column. The
        returned Series is aligned to `bars.index` and holds Signal values
        representing the *desired* position at the close of each bar.
        """

    @property
    @abstractmethod
    def warmup(self) -> int:
        """Number of leading bars with no reliable signal (indicator warmup)."""
