import pandas as pd
import numpy as np

def compute_rsi(series: pd.Series, window: int = 14) -> pd.Series:
    delta = series.diff()
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)

    gain_ema = pd.Series(gain, index=series.index).ewm(alpha=1/window, min_periods=window).mean()
    loss_ema = pd.Series(loss, index=series.index).ewm(alpha=1/window, min_periods=window).mean()

    rs = gain_ema / loss_ema.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi

def dollar_volume(close: pd.Series, volume: pd.Series) -> pd.Series:
    """Price x volume - the correct unit for comparing flow across assets
    with very different share prices and share counts (e.g. BTC-USD vs GLD vs ^GSPC).

    NOTE: this assumes `volume` is share/coin-denominated, which is true for
    stocks, ETFs, and commodities - but NOT for Yahoo Finance crypto pairs
    (BTC-USD, ETH-USD, ...), whose "Volume" field is already reported in USD.
    Multiplying it by price again inflates the result by ~the price itself
    (verified live: BTC-USD's raw daily Volume is ~$12B, already a plausible
    real dollar figure - not ~189,000 BTC coins). Ratio-based uses of this
    function (net_flow_ratio, the composite score) are unaffected since that
    same scaling error cancels out in a ratio - it only matters when the
    result is shown as an absolute number. Use display_dollar_volume() below
    for that case."""
    return close * volume


def display_dollar_volume(ticker: str, close: pd.Series, volume: pd.Series) -> pd.Series:
    """dollar_volume(), but safe to show as an absolute $ figure for any
    ticker - routes around the crypto-pair quirk documented above."""
    if ticker.endswith("-USD"):
        return volume
    return dollar_volume(close, volume)


def money_flow_index(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, window: int = 14) -> pd.Series:
    """Classic Money Flow Index: RSI, but weighted by dollar volume instead of price alone.
    >80 = overbought / distribution risk, <20 = oversold / accumulation zone."""
    typical_price = (high + low + close) / 3
    raw_flow = typical_price * volume

    direction = typical_price.diff()
    positive_flow = raw_flow.where(direction > 0, 0.0)
    negative_flow = raw_flow.where(direction < 0, 0.0)

    positive_sum = positive_flow.rolling(window).sum()
    negative_sum = negative_flow.rolling(window).sum()

    money_ratio = positive_sum / negative_sum.replace(0, np.nan)
    mfi = 100 - (100 / (1 + money_ratio))
    return mfi


def chaikin_money_flow(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, window: int = 20) -> pd.Series:
    """Chaikin Money Flow: where price closes within the high-low range, weighted by volume.
    >0 = buying pressure, <0 = selling pressure."""
    range_ = (high - low).replace(0, np.nan)
    money_flow_multiplier = ((close - low) - (high - close)) / range_
    money_flow_volume = money_flow_multiplier * volume

    cmf = money_flow_volume.rolling(window).sum() / volume.rolling(window).sum()
    return cmf


def on_balance_volume(close: pd.Series, volume: pd.Series) -> pd.Series:
    """Cumulative volume, added on up days and subtracted on down days."""
    direction = np.sign(close.diff().fillna(0))
    return (direction * volume).cumsum()


def net_flow_ratio(close: pd.Series, volume: pd.Series, window: int) -> tuple:
    """Net signed dollar volume over the trailing window (each day's dollar
    volume added if price closed up, subtracted if down), plus that net flow
    as a fraction of total dollar volume traded - bounded [-1, 1], so it's
    comparable across assets regardless of price/size. Returns
    (net_dollar_flow, ratio)."""
    dv = dollar_volume(close, volume)
    direction = np.sign(close.diff().fillna(0))
    signed = (direction * dv).tail(window)
    total = dv.tail(window).sum()

    net_flow = signed.sum()
    ratio = net_flow / total if total else np.nan
    return net_flow, ratio
