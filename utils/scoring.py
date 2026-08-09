import numpy as np
import pandas as pd

from utils.cot_loader import COT_MARKETS, latest_positioning_table
from utils.indicators import chaikin_money_flow, money_flow_index, net_flow_ratio

# FLOW_PROXIES label -> COT_MARKETS label, where a match exists. Ethereum has
# no CFTC-reported futures market, so it's intentionally absent here - its
# score is built from price/volume signals only, and the UI says so rather
# than pretending coverage it doesn't have.
COT_MATCH = {
    "US Equities (SPY)": "S&P 500 (Equities)",
    "Nasdaq Equities (QQQ)": "Nasdaq 100 (Equities)",
    "Gold (GLD)": "Gold",
    "Oil (USO)": "Crude Oil (WTI)",
    "Bonds (TLT)": "10Y Treasury (Bonds)",
    "Bitcoin": "Bitcoin",
}

# Weights for the composite score. Each component is pre-normalized to
# roughly [-1, 1] before this. Renormalized per-asset when COT has no match
# (Ethereum) so its score isn't diluted by a missing component.
_WEIGHTS = {"cmf": 0.35, "flow_ratio": 0.35, "mfi": 0.15, "cot": 0.15}

INFLOW_THRESHOLD = 0.15
OUTFLOW_THRESHOLD = -0.15


def _cot_component(cot_table: pd.DataFrame, label: str):
    """+1/-1 blend of position direction and this week's change in that
    position. None if there's no COT match or data for this asset - callers
    must renormalize weights rather than treat None as 0."""
    market = COT_MATCH.get(label)
    if market is None or cot_table is None or cot_table.empty:
        return None
    row = cot_table[cot_table["Market"] == market]
    if row.empty:
        return None
    row = row.iloc[0]
    net, wow = row["Net Large-Spec Position"], row["WoW Change"]
    if pd.isna(net):
        return None
    position_sign = float(np.sign(net))
    trend_sign = float(np.sign(wow)) if pd.notna(wow) else 0.0
    return 0.5 * position_sign + 0.5 * trend_sign


def _verdict(score: float) -> str:
    if score >= INFLOW_THRESHOLD:
        return "Inflow"
    if score <= OUTFLOW_THRESHOLD:
        return "Outflow"
    return "Neutral"


def window_label(index, window: int):
    """'Aug 1-7' style label for the trailing N-bar window - so a score is
    never shown without saying exactly what dates it covers. Builds the
    non-zero-padded day manually (rather than %-d/%#d) since that strftime
    flag isn't portable between Windows and Unix."""
    if index is None or len(index) < window:
        return None
    start, end = index[-window], index[-1]
    if start.year == end.year and start.month == end.month:
        return f"{start.strftime('%b')} {start.day}–{end.day}"
    return f"{start.strftime('%b')} {start.day}–{end.strftime('%b')} {end.day}"


def _trend_state(ratio_5d, ratio_20d) -> str:
    """The 20D flow ratio can stay negative for weeks after a heavy-volume
    selloff even once buying has resumed, because the old selloff volume is
    still inside the window. Comparing against the most recent 5 days catches
    that lag instead of silently showing a stale verdict."""
    if pd.isna(ratio_5d) or pd.isna(ratio_20d):
        return "insufficient"
    if (ratio_5d > 0.1 and ratio_20d < -0.1) or (ratio_5d < -0.1 and ratio_20d > 0.1):
        return "reversing"
    return "confirming"


def cmf_label(cmf: float) -> str:
    """Shared plain-English CMF read, used consistently by the Overview/Evidence
    reason text and the Watchlist scanner - one vocabulary everywhere instead
    of two heuristics that could disagree."""
    if pd.isna(cmf):
        return "Not enough data"
    if cmf > 0.05:
        return "Buying pressure"
    if cmf < -0.05:
        return "Selling pressure"
    return "Neutral"


def _reason(cmf, ratio_20d, mfi, cot_component, ratio_5d=None, trend=None) -> str:
    parts = []
    if pd.notna(cmf):
        if cmf > 0.05:
            parts.append("buying pressure within the daily range")
        elif cmf < -0.05:
            parts.append("selling pressure within the daily range")
    if pd.notna(ratio_20d):
        if ratio_20d > 0.1:
            parts.append("most of the past month's volume came on up days")
        elif ratio_20d < -0.1:
            parts.append("most of the past month's volume came on down days")
    if cot_component is not None:
        if cot_component > 0:
            parts.append("large speculators are net long and adding")
        elif cot_component < 0:
            parts.append("large speculators are net short or trimming")
    if pd.notna(mfi) and (mfi >= 80 or mfi <= 20):
        parts.append("MFI is stretched, watch for a reversal")

    if not parts:
        base = "No strong signal either way right now."
    else:
        base = parts[0].capitalize() + (("; " + parts[1]) if len(parts) > 1 else "") + "."

    if trend == "reversing" and pd.notna(ratio_5d):
        direction = "buying" if ratio_5d > 0 else "selling"
        base += f" But the last 5 days have flipped to net {direction} — this read may be lagging."

    return base


def _score_frame(label: str, frame: pd.DataFrame, cot_component, has_cot: bool):
    """Core composite-scoring math for one asset's OHLCV frame. Shared by
    compute_asset_scores() (the curated 7 asset-class proxies, with CFTC
    positioning) and score_ticker() (any user-entered ticker on the
    Watchlist, no CFTC coverage) - one signal vocabulary for the whole app
    instead of two implementations that could drift apart."""
    if frame is None or len(frame) < 21:
        return None

    high, low, close, volume = frame["High"], frame["Low"], frame["Close"], frame["Volume"]

    cmf = chaikin_money_flow(high, low, close, volume).iloc[-1]
    mfi = money_flow_index(high, low, close, volume).iloc[-1]
    _, ratio_20d = net_flow_ratio(close, volume, 20)
    _, ratio_5d = net_flow_ratio(close, volume, 5) if len(frame) >= 6 else (np.nan, np.nan)
    trend = _trend_state(ratio_5d, ratio_20d)

    components = {
        "cmf": (cmf, _WEIGHTS["cmf"]),
        "flow_ratio": (ratio_20d, _WEIGHTS["flow_ratio"]),
        "mfi": ((mfi - 50) / 50 if pd.notna(mfi) else np.nan, _WEIGHTS["mfi"]),
        "cot": (cot_component, _WEIGHTS["cot"]),
    }

    weighted_sum, weight_total = 0.0, 0.0
    for value, weight in components.values():
        if value is None or (isinstance(value, float) and np.isnan(value)):
            continue
        weighted_sum += value * weight
        weight_total += weight

    score = weighted_sum / weight_total if weight_total > 0 else np.nan

    return {
        "label": label,
        "score": score,
        "verdict": _verdict(score) if pd.notna(score) else "Unavailable",
        "reason": _reason(cmf, ratio_20d, mfi, cot_component, ratio_5d, trend) if pd.notna(score) else "Not enough data.",
        "cmf": cmf,
        "mfi": mfi,
        "flow_ratio_20d": ratio_20d,
        "flow_ratio_5d": ratio_5d,
        "trend": trend,
        "window_5d": window_label(close.index, 5),
        "window_20d": window_label(close.index, 20),
        "cot_component": cot_component,
        "has_cot": has_cot,
        "last_close": close.iloc[-1],
    }


def compute_asset_scores(flow_data: dict, cot_df: pd.DataFrame) -> list:
    """One entry per FLOW_PROXIES asset: verdict (Inflow/Outflow/Neutral),
    composite score, the raw component values (for the Evidence tab), and a
    plain-English reason. flow_data is utils.data_loader.load_flow_universe()'s
    output; cot_df is utils.cot_loader.load_cot_positioning()'s raw history."""
    cot_table = latest_positioning_table(cot_df) if cot_df is not None else pd.DataFrame()

    results = []
    for label, frame in (flow_data or {}).items():
        cot_component = _cot_component(cot_table, label)
        entry = _score_frame(label, frame, cot_component, has_cot=label in COT_MATCH)
        if entry is not None:
            results.append(entry)

    return results


def score_ticker(ticker: str, frame: pd.DataFrame):
    """Same composite scoring as compute_asset_scores(), for any single
    user-entered ticker (Watchlist tab). No CFTC futures market exists for
    most tickers, so the CFTC component is always excluded and the other
    weights renormalize - same rule as Ethereum in the curated scorecard.
    Returns None if there's not enough price history (needs 21+ daily bars)."""
    return _score_frame(ticker, frame, cot_component=None, has_cot=False)
