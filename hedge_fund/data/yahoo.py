"""Daily Yahoo Finance prices for price-only study mandates."""

from contextlib import contextmanager
from datetime import date, timedelta
from typing import TYPE_CHECKING

from hedge_fund.data.client import CallMeter, FDClientError
from hedge_fund.data.models import Price

if TYPE_CHECKING:
    from hedge_fund.fund.spec import FundSpec


def uses_yahoo(spec: "FundSpec") -> bool:
    return (
        not spec.is_intraday
        and not spec.risk.has_factor_limits
        and all(model.name == "momentum" for strategy in spec.strategies for model in strategy.models)
    )


@contextmanager
def study_data(spec: "FundSpec", financial_datasets, **options):
    """Use Yahoo for daily momentum mandates and Financial Datasets otherwise."""
    if uses_yahoo(spec):
        yield YahooPriceClient(**options)
    else:
        with financial_datasets(**options) as raw:
            yield raw


class YahooPriceClient:
    cache_namespace = "yahoo"

    def __init__(self, meter: CallMeter | None = None):
        try:
            from yfinance import Ticker
        except ImportError as exc:
            raise FDClientError("Yahoo study funds require yfinance. Install with uv tool install --with yfinance .") from exc
        self._ticker = Ticker
        self._meter = meter

    def get_prices(self, ticker, start_date, end_date, interval="day", interval_multiplier=1):
        if interval != "day" or interval_multiplier != 1:
            raise FDClientError("Yahoo study funds support daily prices only")
        if start_date > end_date:
            return []
        # Include earlier sessions so weekend and holiday windows can be
        # filtered locally while Yahoo fetch errors still propagate.
        padded_start = (date.fromisoformat(start_date) - timedelta(days=7)).isoformat()
        end_exclusive = (date.fromisoformat(end_date) + timedelta(days=1)).isoformat()
        if self._meter is not None:
            self._meter.record("/yahoo/daily")
        try:
            frame = self._ticker(ticker).history(
                start=padded_start, end=end_exclusive, interval="1d",
                auto_adjust=False, actions=False, raise_errors=True,
            )
        except Exception as exc:
            raise FDClientError(f"Yahoo prices for {ticker}: {exc}") from exc

        return [
            Price(time=day.date().isoformat(), open=row.Open, high=row.High,
                  low=row.Low, close=row.Close, volume=int(row.Volume))
            for day, row in zip(frame.index, frame.itertuples(index=False))
            if start_date <= day.date().isoformat() <= end_date
        ]
