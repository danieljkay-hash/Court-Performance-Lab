"""Environment-driven configuration with a hard paper/live gate."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

PAPER_BASE_URL = "https://paper-api.alpaca.markets"
LIVE_BASE_URL = "https://api.alpaca.markets"


def _get_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return float(raw)


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return int(raw)


@dataclass(frozen=True)
class Config:
    api_key: str
    secret_key: str
    mode: str  # "paper" or "live"

    # Risk
    max_position_pct: float
    stop_loss_pct: float
    max_open_positions: int
    max_daily_loss_pct: float

    # Strategy
    fast_ma: int
    slow_ma: int
    timeframe: str
    poll_seconds: int

    @property
    def is_live(self) -> bool:
        return self.mode == "live"

    @property
    def paper(self) -> bool:
        """alpaca-py TradingClient expects paper=True for the paper endpoint."""
        return not self.is_live

    def validate(self) -> None:
        if not self.api_key or not self.secret_key:
            raise ValueError(
                "Missing ALPACA_API_KEY / ALPACA_SECRET_KEY. Copy .env.example "
                "to .env and fill them in (paper keys are free)."
            )
        if self.mode not in ("paper", "live"):
            raise ValueError(f"TRADING_MODE must be 'paper' or 'live', got {self.mode!r}")
        if self.fast_ma >= self.slow_ma:
            raise ValueError(
                f"FAST_MA ({self.fast_ma}) must be < SLOW_MA ({self.slow_ma})."
            )
        for name, val in (
            ("MAX_POSITION_PCT", self.max_position_pct),
            ("STOP_LOSS_PCT", self.stop_loss_pct),
            ("MAX_DAILY_LOSS_PCT", self.max_daily_loss_pct),
        ):
            if not 0 < val <= 1:
                raise ValueError(f"{name} must be in (0, 1], got {val}")


def load_config(force_live: bool = False) -> Config:
    """Build Config from the environment.

    `force_live` (from the CLI --live flag) only takes effect when the
    environment also opts into live mode. The CLI must additionally obtain a
    typed confirmation before any live order — see cli.py.
    """
    mode = os.getenv("TRADING_MODE", "paper").strip().lower()
    if force_live and mode != "live":
        raise ValueError(
            "--live was passed but TRADING_MODE is not 'live' in .env. Both are "
            "required to trade real money. This is intentional friction."
        )

    cfg = Config(
        api_key=os.getenv("ALPACA_API_KEY", ""),
        secret_key=os.getenv("ALPACA_SECRET_KEY", ""),
        mode=mode,
        max_position_pct=_get_float("MAX_POSITION_PCT", 0.10),
        stop_loss_pct=_get_float("STOP_LOSS_PCT", 0.05),
        max_open_positions=_get_int("MAX_OPEN_POSITIONS", 5),
        max_daily_loss_pct=_get_float("MAX_DAILY_LOSS_PCT", 0.03),
        fast_ma=_get_int("FAST_MA", 20),
        slow_ma=_get_int("SLOW_MA", 50),
        timeframe=os.getenv("TIMEFRAME", "1Day"),
        poll_seconds=_get_int("POLL_SECONDS", 60),
    )
    cfg.validate()
    return cfg
