# coast_fire_dashboard.py
import math
import streamlit as st

st.set_page_config(page_title="Coast FIRE Dashboard", layout="wide")

st.title("Coast FIRE Dashboard")
st.caption("Coast FIRE = you have enough invested today that you can stop contributing and still hit your FIRE number by retirement (given assumptions).")

def fv_lump_sum(pv: float, r: float, n: int) -> float:
    """Future value of a lump sum."""
    return pv * ((1 + r) ** n)

def pmt_to_reach_fv(pv: float, r: float, n: int, fv_target: float) -> float:
    """
    Payment per period (end of period) needed to reach fv_target given pv, rate r, and n periods.
    Uses standard annuity future value formula.
    """
    if n <= 0:
        return float("inf") if fv_target > pv else 0.0
    if abs(r) < 1e-12:
        # No growth: just linear saving
        needed = max(0.0, fv_target - pv)
        return needed / n

    growth_pv = pv * ((1 + r) ** n)
    remaining = fv_target - growth_pv
    if remaining <= 0:
        return 0.0

    annuity_factor = (((1 + r) ** n) - 1) / r
    return remaining / annuity_factor

def format_money(x: float) -> str:
    return f"${x:,.0f}"

with st.sidebar:
    st.header("Inputs")

    colA, colB = st.columns(2)
    with colA:
        current_age = st.number_input("Current age", min_value=0, max_value=100, value=30, step=1)
        retire_age = st.number_input("Retirement age", min_value=0, max_value=120, value=60, step=1)
        coast_age = st.number_input("Coast age (optional)", min_value=0, max_value=120, value=40, step=1)
    with colB:
        current_portfolio = st.number_input("Current invested portfolio ($)", min_value=0.0, value=150000.0, step=1000.0, format="%.0f")
        annual_spending = st.number_input("Expected annual spending in retirement ($)", min_value=0.0, value=60000.0, step=1000.0, format="%.0f")
        swr = st.number_input("Safe withdrawal rate (e.g., 4%)", min_value=0.5, max_value=10.0, value=4.0, step=0.1) / 100.0

    st.divider()
    st.subheader("Return assumptions")

    use_real = st.toggle("Use real return (after inflation)", value=True)

    if use_real:
        real_return = st.number_input("Expected real annual return (%)", min_value=-5.0, max_value=15.0, value=5.0, step=0.1) / 100.0
        r = real_return
        inflation = None
        nominal_return = None
    else:
        nominal_return = st.number_input("Expected nominal annual return (%)", min_value=-5.0, max_value=20.0, value=8.0, step=0.1) / 100.0
        inflation = st.number_input("Inflation (%)", min_value=-1.0, max_value=15.0, value=3.0, step=0.1) / 100.0
        # Convert to real return: (1+nominal)/(1+inflation)-1
        r = (1 + nominal_return) / (1 + inflation) - 1

    st.divider()
    st.subheader("Optional: ongoing contributions")
    annual_contrib = st.number_input("Annual contributions (if you keep investing) ($/yr)", min_value=0.0, value=0.0, step=500.0, format="%.0f")

# Core calculations
years_to_retire = max(0, int(retire_age - current_age))
years_to_coast = max(0, int(coast_age - current_age))

fire_number = annual_spending / swr if swr > 0 else float("inf")
fv_if_coast_now = fv_lump_sum(current_portfolio, r, years_to_retire)

# Minimum portfolio today to be Coast FIRE
required_today_for_coast = fire_number / ((1 + r) ** years_to_retire) if years_to_retire > 0 else fire_number

# If user keeps contributing until retirement, estimate FV with contributions (annual end-of-year)
def fv_with_contrib(pv: float, r: float, n: int, annual: float) -> float:
    if n <= 0:
        return pv
    if abs(r) < 1e-12:
        return pv + annual * n
    return pv * ((1 + r) ** n) + annual * ((((1 + r) ** n) - 1) / r)

fv_with_contributions = fv_with_contrib(current_portfolio, r, years_to_retire, annual_contrib)

# Contributions needed to hit Coast FIRE by coast_age (reach required_today_for_coast by coast_age)
# i.e. you want portfolio at coast_age to equal required portfolio at that time:
# required_at_coast_age = fire_number / (1+r)^(retire_age - coast_age)
years_from_coast_to_retire = max(0, int(retire_age - coast_age))
required_at_coast_age = fire_number / ((1 + r) ** years_from_coast_to_retire) if years_from_coast_to_retire > 0 else fire_number

annual_needed_to_hit_coast_by_coast_age = pmt_to_reach_fv(
    pv=current_portfolio,
    r=r,
    n=years_to_coast,
    fv_target=required_at_coast_age
)
monthly_needed_to_hit_coast_by_coast_age = annual_needed_to_hit_coast_by_coast_age / 12.0

# Layout
top_left, top_right = st.columns([1.2, 1])

with top_left:
    st.subheader("Results")

    coast_status = fv_if_coast_now >= fire_number

    if coast_status:
        st.success("✅ You are Coast FIRE (based on your assumptions).")
    else:
        st.warning("⚠️ Not Coast FIRE yet (based on your assumptions).")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("FIRE number", format_money(fire_number))
    k2.metric("FV if you stop contributing now", format_money(fv_if_coast_now))
    k3.metric("Needed invested TODAY to coast", format_money(required_today_for_coast))
    k4.metric("Years to retirement", f"{years_to_retire}")

    st.write("**Real return used:**", f"{r*100:.2f}%/yr")

    gap = fire_number - fv_if_coast_now
    if gap > 0:
        st.write(f"You're short by **{format_money(gap)}** at retirement *if you contribute $0 going forward* (under these assumptions).")
    else:
        st.write(f"You have an estimated **surplus of {format_money(-gap)}** at retirement *even with $0 contributions* (under these assumptions).")

with top_right:
    st.subheader("Coast-by-age goal (optional)")
    st.write(f"Target: be Coast FIRE by age **{coast_age}** (so you can stop contributions then).")

    st.write("**Required portfolio at coast age** (to coast from then until retirement):", format_money(required_at_coast_age))

    if years_to_coast <= 0:
        st.info("Coast age is not in the future, so contribution-to-coast calculation is not applicable.")
    else:
        if annual_needed_to_hit_coast_by_coast_age <= 0:
            st.success("✅ You can already hit your coast target by that age without additional contributions (based on assumptions).")
        else:
            st.write("Estimated contributions needed to hit Coast FIRE by your coast age:")
            c1, c2 = st.columns(2)
            c1.metric("Annual needed", format_money(annual_needed_to_hit_coast_by_coast_age))
            c2.metric("Monthly needed", format_money(monthly_needed_to_hit_coast_by_coast_age))

st.divider()
st.subheader("Projection table")

# Build a simple projection table year by year (no contributions + with contributions)
rows = []
for i in range(0, years_to_retire + 1):
    age = current_age + i
    fv0 = fv_lump_sum(current_portfolio, r, i)
    fvC = fv_with_contrib(current_portfolio, r, i, annual_contrib)
    rows.append({
        "Age": age,
        "Year": i,
        "Portfolio (no contrib)": fv0,
        "Portfolio (with contrib)": fvC,
        "FIRE number": fire_number
    })

st.dataframe(
    rows,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Portfolio (no contrib)": st.column_config.NumberColumn(format="$%,.0f"),
        "Portfolio (with contrib)": st.column_config.NumberColumn(format="$%,.0f"),
        "FIRE number": st.column_config.NumberColumn(format="$%,.0f"),
    }
)

st.caption("This is a deterministic projection. Real markets vary; treat outputs as planning estimates, not guarantees.")
