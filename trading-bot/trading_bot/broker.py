"""Thin wrapper over Alpaca's TradingClient.

Centralizes account/position/order calls so the rest of the bot never touches
the SDK directly. Respects the paper/live gate from Config.
"""
from __future__ import annotations

from .config import Config


class Broker:
    def __init__(self, cfg: Config):
        from alpaca.trading.client import TradingClient

        self.cfg = cfg
        self._client = TradingClient(
            cfg.api_key, cfg.secret_key, paper=cfg.paper
        )

    # --- Account ---
    def equity(self) -> float:
        return float(self._client.get_account().equity)

    def cash(self) -> float:
        return float(self._client.get_account().cash)

    def is_market_open(self) -> bool:
        return bool(self._client.get_clock().is_open)

    # --- Positions ---
    def positions(self) -> dict[str, dict]:
        """Map of symbol -> {qty, avg_entry_price, market_value, unrealized_pl}."""
        out: dict[str, dict] = {}
        for p in self._client.get_all_positions():
            out[p.symbol] = {
                "qty": float(p.qty),
                "avg_entry_price": float(p.avg_entry_price),
                "market_value": float(p.market_value),
                "unrealized_pl": float(p.unrealized_pl),
            }
        return out

    def position_qty(self, symbol: str) -> float:
        return self.positions().get(symbol, {}).get("qty", 0.0)

    # --- Orders ---
    def submit_market_buy(self, symbol: str, qty: int):
        from alpaca.trading.enums import OrderSide, TimeInForce
        from alpaca.trading.requests import MarketOrderRequest

        req = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=OrderSide.BUY,
            time_in_force=TimeInForce.DAY,
        )
        return self._client.submit_order(req)

    def submit_market_sell(self, symbol: str, qty: float):
        from alpaca.trading.enums import OrderSide, TimeInForce
        from alpaca.trading.requests import MarketOrderRequest

        req = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=OrderSide.SELL,
            time_in_force=TimeInForce.DAY,
        )
        return self._client.submit_order(req)

    def close_position(self, symbol: str):
        return self._client.close_position(symbol)
