"""Strategy registry: name -> factory that builds a Strategy from Config.

Keeps the CLI decoupled from individual strategy constructors. To add a
strategy, implement it and register it here.
"""
from __future__ import annotations

from typing import Callable

from .base import Strategy
from .ma_crossover import MACrossover
from .momentum import Momentum
from .rsi_reversion import RSIReversion

# Each factory takes the loaded Config and returns a Strategy instance.
_REGISTRY: dict[str, Callable[["object"], Strategy]] = {
    MACrossover.name: lambda cfg: MACrossover(fast=cfg.fast_ma, slow=cfg.slow_ma),
    RSIReversion.name: lambda cfg: RSIReversion(),
    Momentum.name: lambda cfg: Momentum(),
}


def available() -> list[str]:
    return sorted(_REGISTRY)


def build_strategy(name: str, cfg) -> Strategy:
    if name not in _REGISTRY:
        raise ValueError(
            f"Unknown strategy {name!r}. Available: {', '.join(available())}"
        )
    return _REGISTRY[name](cfg)
