"""Simple long-only momentum for studying the paper-trading workflow."""

from datetime import date as Date, timedelta

from hedge_fund.data.protocol import DataClient
from hedge_fund.models import Signal
from hedge_fund.signals.base import QuantModel


class MomentumModel(QuantModel):
    name = "momentum"
    investment_approach = "long_only"
    horizon_days = 5
    lookback = 10

    def predict(self, ticker: str, date: str, data_client: DataClient) -> Signal:
        as_of = date[:10]
        start = (Date.fromisoformat(as_of) - timedelta(days=30)).isoformat()
        prices = sorted(
            (bar for bar in data_client.get_prices(ticker, start, as_of)
             if start <= bar.time[:10] <= as_of and bar.close > 0),
            key=lambda bar: bar.time,
        )
        if len(prices) <= self.lookback:
            return Signal(
                model_name=self.name, ticker=ticker, date=date, value=0,
                reasoning="Insufficient daily closes for ten-session momentum.",
                metadata={"abstained": True},
            )
        change = prices[-1].close / prices[-1 - self.lookback].close - 1
        return Signal(
            model_name=self.name, ticker=ticker, date=date,
            value=self._normalize_to_signal(change * 10),
            reasoning=f"Price change over the last ten sessions: {change:+.2%}.",
            components={"ten_session_return": change},
        )
