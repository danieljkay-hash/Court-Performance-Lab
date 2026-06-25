"""Equity-curve plotting for backtest results.

matplotlib is an optional dependency; we import it lazily and give a clear
message if it's missing so the rest of the bot works without it.
"""
from __future__ import annotations

import pandas as pd

from .backtest import BacktestResult


def _require_matplotlib():
    try:
        import matplotlib.pyplot as plt  # noqa: WPS433 (lazy by design)
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise ImportError(
            "Plotting needs matplotlib. Install it with: pip install matplotlib"
        ) from exc
    return plt


def plot_equity_curve(
    result: BacktestResult,
    bars: pd.DataFrame,
    out_path: str | None = None,
):
    """Plot strategy equity vs. a buy-and-hold benchmark on the same capital.

    If `out_path` is given, saves a PNG there; otherwise shows interactively.
    """
    plt = _require_matplotlib()

    # Buy-and-hold benchmark scaled to the same starting capital.
    close = bars["close"]
    benchmark = result.start_equity * (close / close.iloc[0])

    fig, ax = plt.subplots(figsize=(11, 6))
    ax.plot(result.equity_curve.index, result.equity_curve.values,
            label=f"{result.symbol} strategy ({result.total_return:+.1%})", linewidth=1.6)
    ax.plot(benchmark.index, benchmark.values,
            label=f"Buy & hold ({result.buy_hold_return:+.1%})",
            linewidth=1.2, linestyle="--", alpha=0.8)
    ax.set_title(f"Equity curve — {result.symbol}  "
                 f"(Sharpe {result.sharpe:.2f}, max DD {result.max_drawdown:.1%})")
    ax.set_xlabel("Date")
    ax.set_ylabel("Equity ($)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    if out_path:
        fig.savefig(out_path, dpi=120)
        plt.close(fig)
        return out_path
    plt.show()
    return None
