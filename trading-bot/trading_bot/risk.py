"""Risk management: position sizing and pre-trade limits.

Every entry order must pass through RiskManager. The point is to make the bot
fail safe: when in doubt, trade smaller or not at all.
"""
from __future__ import annotations

from dataclasses import dataclass

from .config import Config


@dataclass
class RiskDecision:
    allowed: bool
    qty: int
    reason: str


class RiskManager:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._day_start_equity: float | None = None
        self._halted_for_day = False

    def start_day(self, equity: float) -> None:
        """Record the equity at the start of the trading day for the kill-switch."""
        self._day_start_equity = equity
        self._halted_for_day = False

    def update_equity(self, equity: float) -> None:
        """Trip the daily-loss kill-switch if equity has fallen too far."""
        if self._day_start_equity is None:
            self._day_start_equity = equity
            return
        drawdown = (self._day_start_equity - equity) / self._day_start_equity
        if drawdown >= self.cfg.max_daily_loss_pct:
            self._halted_for_day = True

    @property
    def halted(self) -> bool:
        return self._halted_for_day

    def size_position(
        self, equity: float, price: float, open_positions: int
    ) -> RiskDecision:
        """Decide how many shares to buy for a new long entry."""
        if self._halted_for_day:
            return RiskDecision(False, 0, "daily loss limit hit; no new entries today")
        if open_positions >= self.cfg.max_open_positions:
            return RiskDecision(
                False, 0, f"max open positions ({self.cfg.max_open_positions}) reached"
            )
        if price <= 0:
            return RiskDecision(False, 0, f"invalid price {price}")

        budget = equity * self.cfg.max_position_pct
        qty = int(budget // price)
        if qty < 1:
            return RiskDecision(
                False, 0, f"position budget ${budget:.2f} < 1 share at ${price:.2f}"
            )
        return RiskDecision(True, qty, "ok")

    def stop_loss_price(self, entry_price: float) -> float:
        """Stop-loss trigger price for a long entered at `entry_price`."""
        return round(entry_price * (1 - self.cfg.stop_loss_pct), 2)
