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

def pct_return(series: pd.Series, periods: int) -> float:
    if len(series) < periods + 1:
        return np.nan
    return (series.iloc[-1] / series.iloc[-periods - 1] - 1) * 100

def multi_period_returns(df: pd.DataFrame, periods_map: dict) -> pd.DataFrame:
    out = {}
    for label, periods in periods_map.items():
        out[label] = df.pct_change(periods=periods).iloc[-1] * 100
    return pd.DataFrame(out)

def dollar_volume(close: pd.Series, volume: pd.Series) -> pd.Series:
    """Price x volume - the correct unit for comparing flow across assets
    with very different share prices and share counts (e.g. BTC-USD vs GLD vs ^GSPC)."""
    return close * volume


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


def volume_price_signal(price: pd.Series, volume: pd.Series, window: int = 20) -> str:
    if len(price) < window + 1 or len(volume) < window + 1:
        return "Insufficient data"

    price_change = price.iloc[-1] / price.iloc[-window - 1] - 1
    vol_ma = volume.rolling(window).mean()
    vol_change = volume.iloc[-1] / vol_ma.iloc[-1] - 1 if vol_ma.iloc[-1] != 0 else 0

    if price_change > 0 and vol_change > 0:
        return "Strong Accumulation (Price ↑, Volume ↑)"
    elif price_change > 0 and vol_change <= 0:
        return "Weak Rally (Price ↑, Volume ↓/flat)"
    elif price_change < 0 and vol_change > 0:
        return "Distribution (Price ↓, Volume ↑)"
    elif price_change < 0 and vol_change <= 0:
        return "Weak Selling (Price ↓, Volume ↓/flat)"
    else:
        return "Sideways / No clear signal"
