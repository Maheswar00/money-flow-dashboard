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


def _reason(cmf, ratio_20d, mfi, cot_component) -> str:
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
        return "No strong signal either way right now."
    return parts[0].capitalize() + (("; " + parts[1]) if len(parts) > 1 else "") + "."


def compute_asset_scores(flow_data: dict, cot_df: pd.DataFrame) -> list:
    """One entry per FLOW_PROXIES asset: verdict (Inflow/Outflow/Neutral),
    composite score, the raw component values (for the Evidence tab), and a
    plain-English reason. flow_data is utils.data_loader.load_flow_universe()'s
    output; cot_df is utils.cot_loader.load_cot_positioning()'s raw history."""
    cot_table = latest_positioning_table(cot_df) if cot_df is not None else pd.DataFrame()

    results = []
    for label, frame in (flow_data or {}).items():
        if frame is None or len(frame) < 21:
            continue

        high, low, close, volume = frame["High"], frame["Low"], frame["Close"], frame["Volume"]

        cmf = chaikin_money_flow(high, low, close, volume).iloc[-1]
        mfi = money_flow_index(high, low, close, volume).iloc[-1]
        _, ratio_20d = net_flow_ratio(close, volume, 20)
        cot_component = _cot_component(cot_table, label)

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

        results.append({
            "label": label,
            "score": score,
            "verdict": _verdict(score) if pd.notna(score) else "Unavailable",
            "reason": _reason(cmf, ratio_20d, mfi, cot_component) if pd.notna(score) else "Not enough data.",
            "cmf": cmf,
            "mfi": mfi,
            "flow_ratio_20d": ratio_20d,
            "cot_component": cot_component,
            "has_cot": label in COT_MATCH,
            "last_close": close.iloc[-1],
        })

    return results
