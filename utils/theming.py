import streamlit as st

def set_page_config_and_theme():
    st.set_page_config(
        page_title="Money Flow Dashboard",
        layout="wide",
    )


# One consistent color language for "is money flowing in or out", reused by
# every verdict badge, card, and score number in the app. Status colors per
# the dataviz skill's validated palette (fixed hex across light/dark, always
# paired with an icon + label so color is never the only channel):
#   inflow (good)    #0ca30c
#   outflow (critical) #d03b3b
#   neutral (muted)  #898781
# The sector-rotation heatmap uses the *diverging* blue<->red pair instead
# (see tabs/overview.py) - that's a continuous numeric encoding where color
# is closer to the only channel, and blue<->red is the validated safer
# choice for red-green color blindness, the most common form of CVD.
VERDICT_STYLE = {
    "Inflow": {"icon": "🟢", "color": "#0ca30c", "wash": "rgba(12,163,12,0.12)"},
    "Outflow": {"icon": "🔴", "color": "#d03b3b", "wash": "rgba(208,59,59,0.12)"},
    "Neutral": {"icon": "⚪", "color": "#898781", "wash": "rgba(137,135,129,0.12)"},
    "Unavailable": {"icon": "◽", "color": "#898781", "wash": "rgba(137,135,129,0.08)"},
}


def inject_custom_css():
    st.markdown(
        """
        <style>
        .flow-card {
            border: 1px solid rgba(128,128,128,0.25);
            border-radius: 10px;
            padding: 14px 16px;
            height: 100%;
        }
        .flow-card-label {
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            opacity: 0.65;
            margin-bottom: 6px;
        }
        .flow-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-weight: 700;
            font-size: 1.05rem;
            padding: 3px 0;
        }
        .flow-score {
            font-size: 0.78rem;
            font-variant-numeric: tabular-nums;
            opacity: 0.7;
            margin: 2px 0 8px 0;
        }
        .flow-meter-track {
            height: 6px;
            border-radius: 3px;
            background: rgba(128,128,128,0.18);
            margin-bottom: 10px;
            position: relative;
            overflow: hidden;
        }
        .flow-meter-fill {
            position: absolute;
            top: 0;
            bottom: 0;
            border-radius: 3px;
        }
        .flow-reason {
            font-size: 0.85rem;
            opacity: 0.85;
            line-height: 1.4;
        }
        .flow-trend-row {
            font-size: 0.75rem;
            font-variant-numeric: tabular-nums;
            opacity: 0.7;
            margin: 6px 0 8px 0;
            padding-top: 6px;
            border-top: 1px dashed rgba(128,128,128,0.25);
        }
        .flow-trend-reversing {
            color: #fab219;
            opacity: 1;
            font-weight: 600;
        }
        .liquidity-strip {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        .liquidity-item {
            flex: 1;
            min-width: 150px;
            border: 1px solid rgba(128,128,128,0.2);
            border-radius: 8px;
            padding: 10px 12px;
        }
        .liquidity-label {
            font-size: 0.75rem;
            opacity: 0.65;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }
        .liquidity-value {
            font-size: 1.15rem;
            font-weight: 600;
            margin-top: 2px;
        }
        .liquidity-delta {
            font-size: 0.8rem;
            margin-top: 2px;
            font-weight: 600;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def verdict_badge_html(verdict: str) -> str:
    style = VERDICT_STYLE.get(verdict, VERDICT_STYLE["Unavailable"])
    return f'<span class="flow-badge" style="color:{style["color"]}">{style["icon"]} {verdict}</span>'


def flow_card_html(
    label: str, verdict: str, score, reason: str, meter_min=-0.6, meter_max=0.6,
    flow_ratio_5d=None, window_5d=None, flow_ratio_20d=None, window_20d=None, trend=None,
) -> str:
    """A self-contained HTML card for one asset class's money-flow verdict.
    score may be NaN (unavailable data) - rendered as a flat, empty meter.
    The 5D/20D row always shows its exact date range - a score is never
    displayed without saying what window it covers - and is highlighted
    when the two windows disagree (trend == "reversing"), since a 20D
    read can lag several days behind an already-reversed short-term trend."""
    style = VERDICT_STYLE.get(verdict, VERDICT_STYLE["Unavailable"])
    score_text = "—" if score is None or score != score else f"{score:+.2f}"

    if score is None or score != score:
        fill_pct, fill_left = 0, 50
    else:
        clipped = max(meter_min, min(meter_max, score))
        span = meter_max - meter_min
        pos_pct = (clipped - meter_min) / span * 100
        mid_pct = (0 - meter_min) / span * 100
        fill_left = min(pos_pct, mid_pct)
        fill_pct = abs(pos_pct - mid_pct)

    trend_html = ""
    if flow_ratio_5d is not None and flow_ratio_5d == flow_ratio_5d:
        is_reversing = trend == "reversing"
        css_class = "flow-trend-row flow-trend-reversing" if is_reversing else "flow-trend-row"
        flag = "⚠ " if is_reversing else ""
        d5 = f"{flow_ratio_5d:+.2f}" + (f" ({window_5d})" if window_5d else "")
        d20 = f"{flow_ratio_20d:+.2f}" + (f" ({window_20d})" if window_20d else "") if flow_ratio_20d == flow_ratio_20d else "—"
        trend_html = f'<div class="{css_class}">{flag}5D flow {d5} · 20D flow {d20}</div>'

    return f"""
    <div class="flow-card">
        <div class="flow-card-label">{label}</div>
        <div class="flow-badge" style="color:{style['color']}">{style['icon']} {verdict}</div>
        <div class="flow-score">score {score_text}</div>
        <div class="flow-meter-track">
            <div class="flow-meter-fill" style="left:{fill_left}%; width:{fill_pct}%; background:{style['color']}"></div>
        </div>
        {trend_html}
        <div class="flow-reason">{reason}</div>
    </div>
    """
