"""Live/paper run loop.

On each iteration, for each symbol:
  1. pull recent bars and compute the strategy's desired position,
  2. enforce stop-losses on open positions,
  3. enter or exit to match the desired position, respecting risk limits.

This is deliberately simple and synchronous. It is not a low-latency engine;
it polls on an interval and trades on bar signals.
"""
from __future__ import annotations

import logging
import time

from .broker import Broker
from .config import Config
from .data import get_latest_bars
from .risk import RiskManager
from .strategies.base import Signal, Strategy

log = logging.getLogger("trading_bot")


class TradingBot:
    def __init__(self, cfg: Config, strategy: Strategy, symbols: list[str]):
        self.cfg = cfg
        self.strategy = strategy
        self.symbols = symbols
        self.broker = Broker(cfg)
        self.risk = RiskManager(cfg)
        # entry prices we track to apply stop-losses locally.
        self._entry_prices: dict[str, float] = {}

    def _desired_signal(self, symbol: str) -> tuple[Signal, float]:
        lookback = self.strategy.warmup + 5
        bars = get_latest_bars(
            symbol, self.cfg.timeframe, lookback,
            self.cfg.api_key, self.cfg.secret_key,
        )
        sig = self.strategy.signals(bars)
        last_price = float(bars["close"].iloc[-1])
        return Signal(int(sig.iloc[-1])), last_price

    def _check_stop_loss(self, symbol: str, last_price: float) -> bool:
        """Force-exit if price has breached the stop. Returns True if exited."""
        entry = self._entry_prices.get(symbol)
        if entry is None:
            return False
        if last_price <= self.risk.stop_loss_price(entry):
            log.warning(
                "STOP-LOSS hit on %s: price %.2f <= stop %.2f (entry %.2f)",
                symbol, last_price, self.risk.stop_loss_price(entry), entry,
            )
            self.broker.close_position(symbol)
            self._entry_prices.pop(symbol, None)
            return True
        return False

    def step(self) -> None:
        if not self.broker.is_market_open():
            log.info("Market closed; skipping iteration.")
            return

        equity = self.broker.equity()
        self.risk.update_equity(equity)
        positions = self.broker.positions()

        for symbol in self.symbols:
            try:
                target, last_price = self._desired_signal(symbol)
            except Exception as exc:  # data hiccups shouldn't kill the loop
                log.error("Signal error for %s: %s", symbol, exc)
                continue

            held = symbol in positions
            if held and self._check_stop_loss(symbol, last_price):
                continue

            if target == Signal.LONG and not held:
                decision = self.risk.size_position(
                    equity, last_price, open_positions=len(positions)
                )
                if not decision.allowed:
                    log.info("Skip BUY %s: %s", symbol, decision.reason)
                    continue
                log.info("BUY %s x%d @ ~%.2f", symbol, decision.qty, last_price)
                self.broker.submit_market_buy(symbol, decision.qty)
                self._entry_prices[symbol] = last_price
            elif target == Signal.FLAT and held:
                log.info("SELL (exit) %s @ ~%.2f", symbol, last_price)
                self.broker.close_position(symbol)
                self._entry_prices.pop(symbol, None)

    def run(self) -> None:
        mode = "LIVE (real money)" if self.cfg.is_live else "paper"
        log.info(
            "Starting bot in %s mode | strategy=%s | symbols=%s | every %ds",
            mode, self.strategy.name, ",".join(self.symbols), self.cfg.poll_seconds,
        )
        self.risk.start_day(self.broker.equity())
        try:
            while True:
                try:
                    self.step()
                except Exception as exc:
                    log.exception("Iteration failed: %s", exc)
                time.sleep(self.cfg.poll_seconds)
        except KeyboardInterrupt:
            log.info("Stopped by user. Open positions left untouched.")
