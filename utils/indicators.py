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
