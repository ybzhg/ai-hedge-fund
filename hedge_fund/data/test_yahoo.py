from types import SimpleNamespace
import sys

import pandas as pd
import pytest

from hedge_fund.data.client import FDClientError
from hedge_fund.data.yahoo import YahooPriceClient


def test_daily_prices_include_end_date_and_exclude_padding(monkeypatch):
    def history(**kwargs):
        assert kwargs["start"] == "2025-01-06"
        assert kwargs["end"] == "2025-01-15"
        assert kwargs["raise_errors"] is True
        return pd.DataFrame(
            {"Open": 100, "High": 102, "Low": 99, "Close": 101, "Volume": 500},
            index=pd.DatetimeIndex(["2025-01-10", "2025-01-13", "2025-01-14"], tz="America/New_York"),
        )

    monkeypatch.setitem(sys.modules, "yfinance", SimpleNamespace(Ticker=lambda _: SimpleNamespace(history=history)))
    prices = YahooPriceClient().get_prices("AAPL", "2025-01-13", "2025-01-14")

    assert [(bar.time, bar.close) for bar in prices] == [("2025-01-13", 101), ("2025-01-14", 101)]


def test_provider_failure_is_not_treated_as_no_data(monkeypatch):
    def history(**kwargs):
        raise ConnectionError("Yahoo unavailable")

    monkeypatch.setitem(sys.modules, "yfinance", SimpleNamespace(Ticker=lambda _: SimpleNamespace(history=history)))
    with pytest.raises(FDClientError, match="Yahoo prices for AAPL"):
        YahooPriceClient().get_prices("AAPL", "2025-01-13", "2025-01-14")
