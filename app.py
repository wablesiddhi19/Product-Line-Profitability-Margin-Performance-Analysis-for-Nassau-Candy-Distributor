"""
Nassau Candy Distributor - Product Line Profitability & Margin Performance
Run with:  streamlit run app.py
"""
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import analysis as a

st.set_page_config(page_title="Nassau Candy | Profitability", page_icon="🍫", layout="wide")

COCOA, CARAMEL, BERRY, MINT, NAVY = "#3E2723", "#E09F3E", "#C8283C", "#2A9D8F", "#264653"
DIV_COL = {"Chocolate": COCOA, "Other": CARAMEL, "Sugar": MINT}
FLAG_COL = {"Critical": BERRY, "High": "#F4A259", "Watch": "#F2CC8F", "Healthy": MINT}

st.markdown(
    f"""
    <style>
      .block-container {{padding-top: 1.2rem;}}
      .hero {{background: linear-gradient(120deg,{COCOA},#6D4C41); color:#fff; padding:1.1rem 1.5rem;
              border-radius:14px; margin-bottom:1rem;}}
      .hero h1 {{margin:0; font-size:1.7rem; color:#fff;}}
      .hero p {{margin:.2rem 0 0 0; opacity:.85; font-size:.92rem;}}
      .kpi {{background:#FFF8E7; border-left:6px solid {CARAMEL}; border-radius:10px; padding:.7rem .9rem;}}
      .kpi .lab {{font-size:.72rem; color:#6D4C41; text-transform:uppercase; letter-spacing:.04em; font-weight:600;}}
      .kpi .val {{font-size:1.55rem; font-weight:700; color:{COCOA}; line-height:1.2;}}
      .kpi .sub {{font-size:.72rem; color:#8D6E63;}}
      .insight {{background:#F5F0EB; border-radius:10px; padding:.7rem 1rem; margin:.4rem 0 .8rem 0; font-size:.92rem;
                 border-left:4px solid {NAVY};}}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def get_data():
    return a.load_clean()


def kpi(col, label, value, sub=""):
    col.markdown(f'<div class="kpi"><div class="lab">{label}</div><div class="val">{value}</div>'
                 f'<div class="sub">{sub}</div></div>', unsafe_allow_html=True)


def insight(text):
    st.markdown(f'<div class="insight">{text}</div>', unsafe_allow_html=True)


raw, audit = get_data()

# ------------------------------------------------------------------ sidebar
st.sidebar.markdown("## 🍫 Filters")
dmin, dmax = raw["Order Date"].min().date(), raw["Order Date"].max().date()
date_sel = st.sidebar.date_input("Order date range", (dmin, dmax), min_value=dmin, max_value=dmax)
if isinstance(date_sel, tuple) and len(date_sel) == 2:
    d0, d1 = date_sel
else:  # user has only picked the first date so far
    d0, d1 = dmin, dmax
divisions = sorted(raw["Division"].unique())
div_sel = st.sidebar.multiselect("Division", divisions, default=divisions)
regions = sorted(raw["Region"].unique())
reg_sel = st.sidebar.multiselect("Region", regions, default=regions)
search = st.sidebar.text_input("Product search", placeholder="e.g. Wonka, gum, taffy")

full_gm = raw["Gross Profit"].sum() / raw["Sales"].sum() * 100
thr = st.sidebar.slider("Margin threshold (%)", 0, 90, int(round(full_gm)),
                        help="Products below this gross margin are treated as margin-risk. "
                             "Default is the overall portfolio margin.")
st.sidebar.caption("Risk flags: Critical < 25%, High < 50%, Watch < threshold.")

mask = (raw["Order Date"].dt.date >= d0) & (raw["Order Date"].dt.date <= d1)
mask &= raw["Division"].isin(div_sel) & raw["Region"].isin(reg_sel)
if search.strip():
    mask &= raw["Product Name"].str.contains(search.strip(), case=False, regex=False)
df = raw[mask]

st.markdown(
    '<div class="hero"><h1>🍫 Nassau Candy Distributor — Product Profitability & Margin Performance</h1>'
    '<p>Which products really drive profit, which divisions dilute margin, and where to reprice, renegotiate or rationalise.</p></div>',
    unsafe_allow_html=True,
)
if df.empty:
    st.warning("No orders match the current filters. Widen the date range or clear the search box.")
    st.stop()

P = a.product_metrics(df, margin_threshold=thr)
D = a.division_metrics(df)
tot_s, tot_gp, tot_u = df["Sales"].sum(), df["Gross Profit"].sum(), df["Units"].sum()
gm = tot_gp / tot_s * 100
at_risk = int(P["Risk Flag"].isin(["Critical", "High"]).sum())

c = st.columns(6)
kpi(c[0], "Sales", f"${tot_s:,.0f}", f"{df['Order ID'].nunique():,} orders")
kpi(c[1], "Gross profit", f"${tot_gp:,.0f}", f"cost ${df['Cost'].sum():,.0f}")
kpi(c[2], "Gross margin", f"{gm:.1f}%", f"threshold {thr}%")
kpi(c[3], "Profit / unit", f"${tot_gp / tot_u:,.2f}", f"{tot_u:,} units")
kpi(c[4], "Products at risk", f"{at_risk} / {len(P)}", "Critical or High flag")
cs = a.concentration_summary(df)
kpi(c[5], "Profit concentration", f"{cs['n80_profit']} of {cs['n_products']}", "products give 80% of profit")
st.write("")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["📊 Product profitability", "🏭 Division performance", "🔍 Cost vs margin diagnostics",
     "📈 Profit concentration", "🗂️ Data & export"])

# ------------------------------------------------------------------ tab 1
with tab1:
    best = P.sort_values("Gross Margin %", ascending=False).iloc[0]
    worst = P.sort_values("Gross Margin %").iloc[0]
    insight(f"Top profit driver: <b>{P.iloc[0]['Product Name']}</b> (${P.iloc[0]['Gross Profit']:,.0f}, "
            f"{P.iloc[0]['Profit Contribution %']:.1f}% of profit). Highest margin: <b>{best['Product Name']}</b> "
            f"({best['Gross Margin %']:.1f}%). Lowest margin: <b>{worst['Product Name']}</b> ({worst['Gross Margin %']:.1f}%).")
    left, right = st.columns([1.15, 1])
    with left:
        st.subheader("Margin leaderboard")
        rank_by = st.radio("Rank by", ["Gross Margin %", "Gross Profit", "Profit per Unit"], horizontal=True)
        lb = P.sort_values(rank_by, ascending=True)
        fig = px.bar(lb, x=rank_by, y="Product Name", orientation="h", color="Risk Flag", color_discrete_map=FLAG_COL,
                     hover_data={"Gross Profit": ":,.0f", "Gross Margin %": ":.1f", "Sales": ":,.0f"},
                     category_orders={"Risk Flag": ["Critical", "High", "Watch", "Healthy"]})
        if rank_by == "Gross Margin %":
            fig.add_vline(x=thr, line_dash="dash", line_color=NAVY, annotation_text=f"threshold {thr}%")
        fig.update_layout(height=480, margin=dict(l=0, r=10, t=10, b=0), yaxis_title=None,
                          legend=dict(orientation="h", y=-0.15))
        st.plotly_chart(fig, use_container_width=True)
    with right:
        st.subheader("Profit contribution")
        top = P.copy()
        top["Label"] = np.where(top["Profit Contribution %"] >= 1, top["Product Name"], "Other products (<1% each)")
        pie = top.groupby("Label", as_index=False)["Gross Profit"].sum()
        fig = px.pie(pie, names="Label", values="Gross Profit", hole=.55,
                     color_discrete_sequence=[COCOA, "#6D4C41", "#8D6E63", "#BCAAA4", CARAMEL, MINT, "#D7CCC8"])
        fig.update_traces(textinfo="percent", textposition="outside")
        fig.update_layout(height=480, margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h", y=-0.1))
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Portfolio map: sales share vs margin")
    fig = px.scatter(P, x="Revenue Contribution %", y="Gross Margin %", size="Gross Profit", color="Segment",
                     hover_name="Product Name", log_x=True, size_max=45,
                     color_discrete_map={"Star": COCOA, "Volume trap": BERRY, "Niche premium": MINT, "Under-performer": CARAMEL})
    fig.add_hline(y=thr, line_dash="dash", line_color=NAVY)
    fig.add_vline(x=100 / len(P), line_dash="dot", line_color="#999")
    fig.update_layout(height=430, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True)
    st.subheader("Product scorecard")
    show = P[["Product Name", "Division", "Factory", "Sales", "Gross Profit", "Gross Margin %", "Profit per Unit",
              "Revenue Contribution %", "Profit Contribution %", "Margin Volatility (pp)", "Segment", "Risk Flag"]]
    st.dataframe(show.style.format({"Sales": "${:,.0f}", "Gross Profit": "${:,.0f}", "Gross Margin %": "{:.1f}%",
                                    "Profit per Unit": "${:.2f}", "Revenue Contribution %": "{:.2f}%",
                                    "Profit Contribution %": "{:.2f}%", "Margin Volatility (pp)": "{:.2f}"}),
                 use_container_width=True, hide_index=True)

# ------------------------------------------------------------------ tab 2
with tab2:
    worst_div = D.sort_values("Gross Margin %").iloc[0]
    insight(f"<b>{worst_div['Division']}</b> has the lowest division margin at {worst_div['Gross Margin %']:.1f}% "
            f"({worst_div['Gross Margin %'] - gm:+.1f} pp vs portfolio). Profit share vs revenue share gap: "
            f"{worst_div['Profit - Revenue Gap (pp)']:+.1f} pp.")
    l, r = st.columns(2)
    with l:
        st.subheader("Revenue vs profit")
        m = D.melt(id_vars="Division", value_vars=["Sales", "Gross Profit"], var_name="Measure", value_name="USD")
        fig = px.bar(m, x="Division", y="USD", color="Measure", barmode="group",
                     color_discrete_map={"Sales": "#BCAAA4", "Gross Profit": COCOA})
        fig.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h", y=1.1, title=None))
        st.plotly_chart(fig, use_container_width=True)
    with r:
        st.subheader("Revenue share vs profit share")
        m = D.melt(id_vars="Division", value_vars=["Revenue Share %", "Profit Share %"], var_name="Measure", value_name="%")
        fig = px.bar(m, x="Division", y="%", color="Measure", barmode="group",
                     color_discrete_map={"Revenue Share %": "#BCAAA4", "Profit Share %": CARAMEL})
        fig.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h", y=1.1, title=None))
        st.plotly_chart(fig, use_container_width=True)
    l, r = st.columns(2)
    with l:
        st.subheader("Margin distribution by division")
        st.caption("Each dot is a product (all order lines of a product share one price and cost, so margin differs by product, not by order).")
        fig = px.strip(P, x="Division", y="Gross Margin %", color="Division", hover_name="Product Name",
                       color_discrete_map=DIV_COL)
        fig.update_traces(marker=dict(size=13, line=dict(width=1, color="white")))
        fig.add_hline(y=gm, line_dash="dash", line_color=NAVY, annotation_text=f"portfolio {gm:.1f}%")
        fig.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    with r:
        st.subheader("Monthly gross margin by division")
        mt = a.monthly_trend(df, "Division")
        fig = px.line(mt, x="Month", y="Gross Margin %", color="Division", markers=True, color_discrete_map=DIV_COL)
        fig.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h", y=1.1, title=None))
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Swings in smaller divisions reflect product mix in months with very few orders, not price or cost changes.")
    st.subheader("Division scorecard")
    st.dataframe(D[["Division", "Products", "Sales", "Gross Profit", "Gross Margin %", "Profit per Unit", "Revenue Share %",
                    "Profit Share %", "Profit - Revenue Gap (pp)", "Margin Volatility (pp)"]]
                 .style.format({"Sales": "${:,.0f}", "Gross Profit": "${:,.0f}", "Gross Margin %": "{:.1f}%",
                                "Profit per Unit": "${:.2f}", "Revenue Share %": "{:.1f}%", "Profit Share %": "{:.1f}%",
                                "Profit - Revenue Gap (pp)": "{:+.1f}", "Margin Volatility (pp)": "{:.2f}"}),
                 use_container_width=True, hide_index=True)
    st.subheader("Factory view")
    Fm = a.factory_metrics(df)
    fig = px.bar(Fm, x="Factory", y="Gross Profit", color="Gross Margin %", color_continuous_scale="RdYlGn",
                 text=Fm["Gross Margin %"].map("{:.1f}%".format))
    fig.update_layout(height=330, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------------ tab 3
with tab3:
    flagged = P[P["Risk Flag"].isin(["Critical", "High", "Watch"])]
    insight(f"{len(flagged)} product(s) fall below the {thr}% threshold; {at_risk} are Critical or High risk. "
            "Points above the dotted margin lines have a lower margin than that line.")
    l, r = st.columns([1.3, 1])
    with l:
        st.subheader("Cost vs sales (log scale)")
        fig = px.scatter(P, x="Sales", y="Cost", color="Risk Flag", color_discrete_map=FLAG_COL, size="Units", size_max=38,
                         hover_name="Product Name", log_x=True, log_y=True,
                         hover_data={"Gross Margin %": ":.1f", "Cost Ratio %": ":.1f"})
        xs = np.logspace(np.log10(max(P["Sales"].min(), 1)), np.log10(P["Sales"].max()), 30)
        for mg, dash in [(0.25, "dot"), (0.50, "dash"), (thr / 100, "solid")]:
            fig.add_trace(go.Scatter(x=xs, y=xs * (1 - mg), mode="lines", line=dict(color="#999", dash=dash, width=1),
                                     name=f"{mg * 100:.0f}% margin", hoverinfo="skip"))
        fig.update_layout(height=470, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, use_container_width=True)
    with r:
        st.subheader("Unit economics")
        ue = P.melt(id_vars="Product Name", value_vars=["Avg Price per Unit", "Cost per Unit"], var_name="Measure", value_name="USD")
        fig = px.bar(ue, y="Product Name", x="USD", color="Measure", barmode="group", orientation="h",
                     color_discrete_map={"Avg Price per Unit": CARAMEL, "Cost per Unit": COCOA})
        fig.update_layout(height=470, margin=dict(l=0, r=0, t=10, b=0), yaxis_title=None, legend=dict(orientation="h", y=-0.12, title=None))
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Margin-risk flags & recommended action")
    tbl = P[["Product Name", "Sales", "Gross Margin %", "Cost Ratio %", "Risk Flag", "Recommended Action"]]
    def _colour(v):
        return f"background-color:{FLAG_COL.get(v, 'white')}; color:{'white' if v in ('Critical',) else 'black'}"
    st.dataframe(tbl.style.map(_colour, subset=["Risk Flag"])
                 .format({"Sales": "${:,.0f}", "Gross Margin %": "{:.1f}%", "Cost Ratio %": "{:.1f}%"}),
                 use_container_width=True, hide_index=True)

    st.subheader("Repricing / cost simulator")
    cand = P[P["Gross Margin %"] < 99]["Product Name"].tolist()
    default_ix = cand.index(P.sort_values("Gross Margin %").iloc[0]["Product Name"])
    s1, s2 = st.columns([1, 2])
    with s1:
        prod = st.selectbox("Product", cand, index=default_ix)
        target = st.slider("Target gross margin (%)", 10, 80, 50)
    row = P[P["Product Name"] == prod].iloc[0]
    new_price = row["Cost per Unit"] / (1 - target / 100)
    max_cost = row["Avg Price per Unit"] * (1 - target / 100)
    uplift = max(new_price - row["Avg Price per Unit"], 0) * row["Units"]
    with s2:
        k = st.columns(4)
        kpi(k[0], "Current price / cost", f"${row['Avg Price per Unit']:.2f} / ${row['Cost per Unit']:.2f}", f"GM {row['Gross Margin %']:.1f}%")
        kpi(k[1], "Price needed", f"${max(new_price, row['Avg Price per Unit']):.2f}",
            f"{max(new_price / row['Avg Price per Unit'] - 1, 0) * 100:+.0f}%")
        kpi(k[2], "Or cost must fall to", f"${min(max_cost, row['Cost per Unit']):.2f}",
            f"{min(max_cost / row['Cost per Unit'] - 1, 0) * 100:.0f}%")
        kpi(k[3], "Profit uplift", f"${uplift:,.0f}", "constant units")
        st.caption("Assumes unchanged volume. A price rise of this size may reduce demand, so treat it as an upper bound.")

# ------------------------------------------------------------------ tab 4
with tab4:
    measure = st.radio("Concentration basis", ["Gross Profit", "Sales"], horizontal=True)
    level = st.radio("Level", ["Product Name", "Factory", "State/Province"], horizontal=True)
    LEVEL_WORD = {"Product Name": "products", "Factory": "factories", "State/Province": "states"}
    par = a.pareto(df, level, measure)
    n80 = a.n_to_reach(par)
    insight(f"<b>{n80} of {len(par)}</b> {LEVEL_WORD[level]} ({n80 / len(par) * 100:.0f}%) generate 80% of {measure.lower()}. "
            f"Top item: <b>{par.iloc[0][level]}</b> ({par.iloc[0]['Share %']:.1f}%).")
    view = par.head(25)
    fig = go.Figure()
    fig.add_bar(x=view[level], y=view["Share %"], name=f"{measure} share %",
                marker_color=[COCOA if i < n80 else "#BCAAA4" for i in range(len(view))])
    fig.add_trace(go.Scatter(x=view[level], y=view["Cumulative %"], name="Cumulative %", yaxis="y2",
                             mode="lines+markers", line=dict(color=BERRY)))
    fig.add_hline(y=80, line_dash="dash", line_color=BERRY, yref="y2")
    fig.update_layout(height=450, yaxis=dict(title="Share %"), yaxis2=dict(title="Cumulative %", overlaying="y", side="right", range=[0, 105]),
                      margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h", y=1.1), xaxis_tickangle=-40)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Dependency indicators")
    k = st.columns(4)
    kpi(k[0], "Top-1 product share", f"{cs['top1_profit_share']:.1f}%", "of gross profit")
    kpi(k[1], "Top-3 product share", f"{cs['top3_profit_share']:.1f}%", "of gross profit")
    kpi(k[2], "Top-5 product share", f"{cs['top5_profit_share']:.1f}%", "of gross profit")
    hhi = cs["hhi_profit"]
    kpi(k[3], "Profit HHI", f"{hhi:,.0f}", "high" if hhi > 2500 else "moderate" if hhi > 1500 else "low")
    fac = a.pareto(df, "Factory", "Gross Profit")
    stt = a.pareto(df, "State/Province", "Gross Profit")
    st.write("")
    risk_rows = [
        ("Product dependency", f"Top 3 products = {cs['top3_profit_share']:.0f}% of profit",
         "High" if cs["top3_profit_share"] > 50 else "Moderate"),
        ("Factory dependency", f"{fac.iloc[0]['Factory']} = {fac.iloc[0]['Share %']:.0f}% of profit; top 2 = {fac['Share %'].head(2).sum():.0f}%",
         "High" if fac["Share %"].head(2).sum() > 80 else "Moderate"),
        ("Geographic dependency", f"{stt.iloc[0]['State/Province']} = {stt.iloc[0]['Share %']:.0f}%; top 3 states = {stt['Share %'].head(3).sum():.0f}%",
         "Moderate" if stt["Share %"].head(3).sum() > 30 else "Low"),
    ]
    st.dataframe(pd.DataFrame(risk_rows, columns=["Dependency", "Evidence (current filters)", "Level"]),
                 use_container_width=True, hide_index=True)

# ------------------------------------------------------------------ tab 5
with tab5:
    st.subheader("Data quality audit")
    st.write(f"Rows in: **{audit['rows_in']:,}** → rows out: **{audit['rows_out']:,}**  "
             f"(invalid removed: {audit['invalid_removed']}, missing units: {audit['missing_units']}, "
             f"profit mismatches fixed: {audit['profit_mismatch']}, duplicates: {audit['exact_duplicates']}).")
    st.caption(f"Ship Date is not used: it falls a median of {audit['ship_lag_days_median']:,} days after Order Date, "
               "which is not plausible and has no bearing on profitability.")
    st.download_button("⬇️ Download product metrics (CSV)", P.to_csv(index=False).encode(), "product_metrics.csv", "text/csv")
    st.download_button("⬇️ Download filtered orders (CSV)", df.drop(columns=["Month"]).to_csv(index=False).encode(),
                       "filtered_orders.csv", "text/csv")
    st.dataframe(df.head(500), use_container_width=True, hide_index=True)
    st.caption("Showing the first 500 filtered rows.")
