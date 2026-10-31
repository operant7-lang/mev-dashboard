import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="MEV Sandwich Detector", page_icon="🥪", layout="wide")
st.title("🥪 Sandwich attacks on Uniswap V2")
st.caption("Heuristic detection from on-chain Swap events. Profit is a gross estimate before gas.")


@st.cache_data(ttl=300)
def load():
    url = st.secrets["SUPABASE_URL"].rstrip("/") + "/rest/v1/sandwiches"
    r = requests.get(
        url,
        headers={"apikey": st.secrets["SUPABASE_KEY"]},
        params={"select": "block,pool,attacker,front_tx,back_tx,profit_pct_of_input",
                "order": "block.desc", "limit": "5000"},
        timeout=30,
    )
    r.raise_for_status()
    return pd.DataFrame(r.json())


raw = load()
if raw.empty:
    st.info("No detections saved yet.")
    st.stop()

raw["profit_pct_of_input"] = pd.to_numeric(raw["profit_pct_of_input"])
lo, hi = st.sidebar.slider("Gross profit (% of input)", 0.0, 100.0, (0.05, 5.0))
df = raw[(raw["profit_pct_of_input"] >= lo) & (raw["profit_pct_of_input"] <= hi)].copy()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Sandwiches detected", len(df))
c2.metric("Unique attackers", df["attacker"].nunique())
c3.metric("Avg gross profit", f"{df['profit_pct_of_input'].mean():.2f}%" if len(df) else "n/a")
c4.metric("Filtered out as noise", len(raw) - len(df))

top = (df.groupby("attacker")
         .agg(sandwiches=("front_tx", "count"),
              avg_profit_pct=("profit_pct_of_input", "mean"))
         .sort_values("sandwiches", ascending=False)
         .reset_index())
st.subheader("Top attackers")
st.dataframe(top, use_container_width=True)
if len(top):
    st.bar_chart(top.set_index("attacker")["sandwiches"])

df["front"] = "https://etherscan.io/tx/" + df["front_tx"]
st.subheader("Detections")
st.dataframe(
    df[["block", "attacker", "profit_pct_of_input", "front"]],
    column_config={"front": st.column_config.LinkColumn("Front tx")},
    use_container_width=True,
)
st.caption("Limits: Uniswap V2 pools only, pattern-based so false positives are possible, "
           "and rows outside the profit range in the sidebar are hidden.")