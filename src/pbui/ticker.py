"""Headless adapter for a ticker's daily price history."""

from __future__ import annotations

import pandas as pd
import yfinance as yf


def production_history(ticker: yf.Ticker) -> pd.DataFrame:
    """Fetch one month of daily history for the exact supplied ticker."""

    return ticker.history(period="1mo", interval="1d", timeout=15)
