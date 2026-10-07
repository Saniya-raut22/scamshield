import streamlit as st

THEMES = {
    "dark": {
        "theme.base": "dark",
        "theme.primaryColor": "#4F8BF9",
        "theme.backgroundColor": "#0E1117",
        "theme.secondaryBackgroundColor": "#1A1F2B",
        "theme.textColor": "#FAFAFA",
    },
    "light": {
        "theme.base": "light",
        "theme.primaryColor": "#2563EB",
        "theme.backgroundColor": "#FFFFFF",
        "theme.secondaryBackgroundColor": "#EEF2F9",
        "theme.textColor": "#1A1F2B",
    },
}

CSS = """
<style>
.block-container {padding-top: 1.5rem; max-width: 1200px;}
.hero {padding: 1.6rem 1.8rem; border-radius: 18px; margin-bottom: 1.2rem; color: white;
       background: linear-gradient(135deg, #1e3a8a 0%, #4F8BF9 100%);
       box-shadow: 0 8px 24px rgba(79,139,249,.25);}
.hero h1 {margin: 0; font-size: 2.1rem; color: white;}
.hero p {margin: .4rem 0 .8rem; opacity: .92; font-size: 1.05rem; color: white;}
.chip {display: inline-block; padding: .2rem .7rem; margin: 0 .4rem .3rem 0; border-radius: 999px;
       background: rgba(255,255,255,.18); font-size: .85rem; color: white;}
.risk {padding: 1.1rem 1.3rem; border-radius: 16px; margin: .4rem 0 .8rem; color: white;}
.risk h2 {margin: 0; font-size: 1.5rem; color: white;}
.risk p {margin: .4rem 0 0; opacity: .95; color: white;}
.high {background: linear-gradient(135deg, #7f1d1d, #ef4444);}
.med {background: linear-gradient(135deg, #78350f, #f59e0b);}
.low {background: linear-gradient(135deg, #14532d, #22c55e);}
.gauge {position: relative; height: 12px; border-radius: 999px; margin: .6rem 0 .3rem;
        background: linear-gradient(90deg, #22c55e, #f59e0b, #ef4444);}
.marker {position: absolute; top: -5px; width: 5px; height: 22px; border-radius: 3px;
         background: white; transform: translateX(-50%);
         box-shadow: 0 0 0 1px rgba(0,0,0,.5), 0 0 6px rgba(0,0,0,.4);}
.gauge-labels {display: flex; justify-content: space-between; font-size: .75rem;
               opacity: .7; margin-bottom: .8rem;}
[data-testid="stMetric"] {background: rgba(128,128,128,.12); border: 1px solid rgba(128,128,128,.28);
                          border-radius: 14px; padding: .8rem 1rem;}
.stButton > button {border-radius: 10px;}
[data-testid="stSidebar"] {border-right: 1px solid rgba(128,128,128,.25);}
</style>
"""

LEVELS = {
    "High": ("high", "🚨", "HIGH RISK"),
    "Medium": ("med", "⚠️", "MEDIUM RISK"),
    "Low": ("low", "✅", "LOW RISK"),
}


def theme_toggle():
    if "dark_mode" not in st.session_state:
        st.session_state["dark_mode"] = True
    st.sidebar.toggle("🌙 Dark mode", key="dark_mode")

    want = "dark" if st.session_state["dark_mode"] else "light"
    if st.session_state.get("applied_theme") == want:
        return

    ok = False
    try:
        for key, value in THEMES[want].items():
            st._config.set_option(key, value)
        ok = True
    except Exception:
        pass  # if this Streamlit version blocks it, use the Settings menu instead
    st.session_state["applied_theme"] = want
    if ok:
        st.rerun()


def apply(title, subtitle, chips=None):
    theme_toggle()
    st.markdown(CSS, unsafe_allow_html=True)
    chip_html = "".join(f'<span class="chip">{c}</span>' for c in (chips or []))
    st.markdown(
        f'<div class="hero"><h1>{title}</h1><p>{subtitle}</p>{chip_html}</div>',
        unsafe_allow_html=True,
    )


def risk_card(level, score, text=""):
    cls, icon, label = LEVELS[level]
    st.markdown(
        f'<div class="risk {cls}"><h2>{icon} {label} · {score}/100</h2><p>{text}</p></div>',
        unsafe_allow_html=True,
    )


def gauge(score):
    score = max(0, min(100, int(score)))
    st.markdown(
        f'<div class="gauge"><div class="marker" style="left:{score}%"></div></div>'
        '<div class="gauge-labels"><span>Safe</span><span>Suspicious</span><span>Scam</span></div>',
        unsafe_allow_html=True,
    )


def level_from_prob(p):
    if p >= 0.75:
        return "High"
    if p >= 0.5:
        return "Medium"
    return "Low"