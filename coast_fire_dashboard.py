# coast_fire_dashboard.py
import math
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Coast FIRE Dashboard", page_icon="🏝️", layout="wide")

# --- CSS to prevent metrics from truncating (the "$1,00..." issue) ---
st.markdown(
    """
    <style>
    [data-testid="stMetricValue"] {
        white-space: nowrap !important;
        overflow: visible !important;
        text-overflow: clip !important;
        font-size: 2.2rem !important;
        line-height: 1.2 !important;
    }
    [data-testid="stMetricLabel"] {
        white-space: nowrap !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🏝️ Coast FIRE Dashboard")
st.caption(
    "Coast FIRE = you have enough invested today that you can stop contributing and still hit your FIRE number by retirement (given assumptions)."
)

# ---------- Helpers ----------
def money(x: float) -> str:
    if x is None or math.isinf(x) or math.isnan(x):
        return "—"
    return f"${x:,.0f}"

def fv_lump_sum(pv: float, r: float, n: int) -> float:
    return pv * ((1 + r) ** n)

def fv_with_contrib_annual(pv: float, r: float, n: int, annual_contrib: float) -> float:
    """Future value assuming contributions are made at end of each year."""
    if n <= 0:
        return pv
    if abs(r) < 1e-12:
        return pv + annual_contrib * n
    annuity_factor = (((1 + r) ** n) - 1) / r
    return pv * ((1 + r) ** n) + annual_contrib * annuity_factor

def pmt_to_reach_fv(pv: float, r: float, n: int, fv_target: float) -> float:
    """Annual contribution needed (end of year) to reach fv_target in n years."""
    if n <= 0:
        return 0.0 if pv >= fv_target else float("inf")
    if abs(r) < 1e-12:
        needed = max(0.0, fv_target - pv)
        return needed / n

    growth_pv = pv * ((1 + r) ** n)
    remaining = fv_target - growth_pv
    if remaining <= 0:
        return 0.0

    annuity_factor = (((1 + r) ** n) - 1) / r
    return remaining / annuity_factor

# ---------- Sidebar Inputs ----------
with st.sidebar:
    st.header("Inputs")

    st.subheader("Ages")
    current_age = st.number_input("Current age", min_value=0, max_value=100, value=28, step=1)
    retire_age = st.number_input("Retirement age", min_value=0, max_value=120, value=60, step=1)
    coast_age = st.number_input("Coast age (optional)", min_value=0, max_value=120, value=40, step=1)

    st.divider()
    st.subheader("Money")
    current_portfolio = st.number_input(
        "Current invested portfolio ($)",
        min_value=0.0,
        value=50000.0,
        step=1000.0,
        format="%.0f",
    )
    annual_spending = st.number_input(
        "Expected annual spending in retirement ($)",
        min_value=0.0,
        value=40000.0,
        step=1000.0,
        format="%.0f",
    )
    swr_pct = st.number_input(
        "Safe withdrawal rate (%)",
        min_value=0.5,
        max_value=10.0,
        value=4.0,  # ✅ default to 4%
        step=0.1,
    )

    st.divider()
    st.subheader("Return assumptions")
    use_real = st.toggle("Use real return (after inflation)", value=True)

    if use_real:
        r_pct = st.number_input(
            "Expected real annual return (%)",
            min_value=-5.0,
            max_value=15.0,
            value=7.0,  # ✅ default to 7%
            step=0.1,
        )
        r = r_pct / 100.0
        return_label = f"{r_pct:.2f}% real/yr"
    else:
        nominal_pct = st.number_input("Expected nominal annual return (%)", -5.0, 20.0, 10.0, 0.1)
        inflation_pct = st.number_input("Inflation (%)", -1.0, 15.0, 3.0, 0.1)
        nominal = nominal_pct / 100.0
        inflation = inflation_pct / 100.0
        r = (1 + nominal) / (1 + inflation) - 1
        return_label = f"{r*100:.2f}% real/yr (from nominal/inflation)"

    st.divider()
    st.subheader("Optional contributions")
    annual_contrib = st.number_input(
        "Annual contributions ($/yr)",
        min_value=0.0,
        value=0.0,
        step=500.0,
        format="%.0f",
        help="Used only for the graph comparison (no-contrib vs with-contrib). Coast FIRE assumes $0 contributions.",
    )

# ---------- Guardrails ----------
if retire_age <= current_age:
    st.error("Retirement age must be greater than current age.")
    st.stop()

years_to_retire = int(retire_age - current_age)
swr = swr_pct / 100.0

if swr <= 0:
    st.error("Safe withdrawal rate must be greater than 0.")
    st.stop()

# ---------- Core Calculations ----------
fire_number = annual_spending / swr
fv_if_coast_now = fv_lump_sum(current_portfolio, r, years_to_retire)
required_today_for_coast = fire_number / ((1 + r) ** years_to_retire)

coast_now = fv_if_coast_now >= fire_number
gap = fire_number - fv_if_coast_now

# Coast-by-age target
years_to_coast = int(max(0, coast_age - current_age))
years_from_coast_to_retire = int(max(0, retire_age - coast_age))
required_at_coast_age = (
    fire_number / ((1 + r) ** years_from_coast_to_retire) if years_from_coast_to_retire > 0 else fire_number
)
annual_needed_to_hit_coast_by_coast_age = (
    pmt_to_reach_fv(current_portfolio, r, years_to_coast, required_at_coast_age) if years_to_coast > 0 else None
)

# ---------- Layout ----------
left, right = st.columns([1.25, 1])

with left:
    st.subheader("Results")

    # Metrics row (short labels = more room)
    m1, m2, m3, m4 = st.columns([1, 1, 1, 0.8])
    m1.metric("FIRE #", money(fire_number))
    m2.metric("FV (no contrib)", money(fv_if_coast_now))
    m3.metric("Needed today", money(required_today_for_coast))
    m4.metric("Years", f"{years_to_retire}")

    st.caption(f"Return used: **{return_label}**")

    if coast_now:
        st.success("✅ You are Coast FIRE (based on your assumptions).")
        st.write(
            f"Even with **$0 contributions**, you project to hit **{money(fire_number)}** by age **{retire_age}**."
        )
        st.write(f"Estimated surplus at retirement: **{money(-gap)}**")
    else:
        st.warning("⚠️ Not Coast FIRE yet (based on your assumptions).")
        st.write(
            f"If you contribute **$0**, you’re projected to be short by **{money(gap)}** by age **{retire_age}**."
        )

with right:
    st.subheader("Coast-by-age goal (optional)")
    st.write(f"Target: be Coast FIRE by age **{coast_age}** (so you can stop contributions then).")

    st.write(f"Required portfolio at age **{coast_age}**:", money(required_at_coast_age))

    if years_to_coast <= 0:
        st.info("Coast age is not in the future, so the contribution-to-coast calculation isn’t applicable.")
    else:
        if annual_needed_to_hit_coast_by_coast_age is not None and annual_needed_to_hit_coast_by_coast_age <= 0:
            st.success(f"✅ You can reach Coast FIRE by age {coast_age} with $0 added (based on assumptions).")
        else:
            st.write("Estimated contributions needed to hit Coast FIRE by your coast age:")
            c1, c2 = st.columns(2)
            c1.metric("Annual needed", money(annual_needed_to_hit_coast_by_coast_age))
            c2.metric("Monthly needed", money(annual_needed_to_hit_coast_by_coast_age / 12.0))

# ---------- Compound Growth Line Graph ----------
st.divider()
st.subheader("📈 Compound growth (portfolio over time)")

years = list(range(0, years_to_retire + 1))
ages = [current_age + y for y in years]

no_contrib_series = [fv_lump_sum(current_portfolio, r, y) for y in years]
with_contrib_series = [fv_with_contrib_annual(current_portfolio, r, y, annual_contrib) for y in years]
fire_line = [fire_number for _ in years]

chart_df = pd.DataFrame(
    {
        "Age": ages,
        "Portfolio (no contrib)": [round(x, 0) for x in no_contrib_series],
        "Portfolio (with contrib)": [round(x, 0) for x in with_contrib_series],
        "FIRE number": [round(x, 0) for x in fire_line],
    }
).set_index("Age")

st.line_chart(chart_df, use_container_width=True)

st.caption(
    "This chart is deterministic and based on your inputs (real return assumption). Markets vary — use this as a planning estimate, not a guarantee."
)

