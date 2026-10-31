import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Sandwich Radar", page_icon="🥪", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Rajdhani:wght@400;500;600;700&display=swap');

html, body, [class*="css"], .stApp { font-family: 'Rajdhani', sans-serif; }
.stApp {
  background:
    repeating-linear-gradient(135deg, rgba(255,0,41,0.035) 0 2px, transparent 2px 22px),
    #0a0a0c;
}
footer { visibility: hidden; }
.block-container { padding-top: 1.5rem; max-width: 1300px; }

.hero {
  position: relative;
  padding: 34px 40px 30px 40px;
  margin-bottom: 26px;
  background: linear-gradient(120deg, #2a0009 0%, #12060a 45%, #0a0a0c 100%);
  border-left: 5px solid #ff0029;
  clip-path: polygon(0 0, 100% 0, 100% calc(100% - 26px), calc(100% - 26px) 100%, 0 100%);
  box-shadow: 0 0 40px rgba(255,0,41,0.15);
}
.hero .tag {
  display: inline-block; font-family: 'Orbitron', sans-serif; font-size: 0.7rem;
  letter-spacing: 0.3em; color: #ff0029; border: 1px solid #ff0029;
  padding: 4px 10px; margin-bottom: 14px;
}
.hero h1 {
  font-family: 'Orbitron', sans-serif; font-weight: 900; font-size: 3rem;
  letter-spacing: 0.08em; line-height: 1; margin: 0; color: #fff; text-transform: uppercase;
}
.hero h1 span { color: #ff0029; margin-left: 14px; }
.hero p { color: #9a9aa5; font-size: 1.1rem; margin: 12px 0 0 0; letter-spacing: 0.04em; }

[data-testid="stMetric"] {
  background: #111117; border-left: 3px solid #ff0029; padding: 16px 20px;
  clip-path: polygon(0 0, calc(100% - 16px) 0, 100% 16px, 100% 100%, 0 100%);
}
[data-testid="stMetricLabel"] p {
  color: #ff0029 !important; text-transform: uppercase; letter-spacing: 0.15em;
  font-size: 0.8rem !important; font-weight: 600;
}
[data-testid="stMetricValue"] { font-family: 'Orbitron', sans-serif; color: #fff; font-weight: 700; }

h2, h3 {
  font-family: 'Orbitron', sans-serif !important; text-transform: uppercase;
  letter-spacing: 0.12em; color: #fff !important;
  border-left: 4px solid #ff0029; padding-left: 12px; margin-top: 1.6rem;
}
[data-testid="stSidebar"] { background: #0e0e12; border-right: 1px solid #2a0009; }
[data-testid="stSidebar"] * { font-family: 'Rajdhani', sans-serif; }
[data-testid="stDataFrame"] { border: 1px solid #2a2a33; }
.small-note { color: #70707c; font-size: 0.9rem; letter-spacing: 0.05em; margin-top: 24px; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <div class="tag">LIVE · ETHEREUM MAINNET</div>
  <h1>Sandwich<span>Radar</span></h1>
  <p>Detecting front-run / back-run attacks on Uniswap V2 pools from on-chain swap events</p>
</div>
""", unsafe_allow_html=True)


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
st.sidebar.markdown("### Filters")
lo, hi = st.sidebar.slider("Gross profit (% of input)", 0.0, 100.0, (0.05, 5.0))
df = raw[(raw["profit_pct_of_input"] >= lo) & (raw["profit_pct_of_input"] <= hi)].copy()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Sandwiches", len(df))
c2.metric("Unique attackers", df["attacker"].nunique())
c3.metric("Avg gross profit", f"{df['profit_pct_of_input'].mean():.2f}%" if len(df) else "n/a")
c4.metric("Filtered as noise", len(raw) - len(df))

top = (df.groupby("attacker")
         .agg(sandwiches=("front_tx", "count"),
              avg_profit_pct=("profit_pct_of_input", "mean"))
         .sort_values("sandwiches", ascending=False)
         .reset_index())

st.subheader("Top attackers")
left, right = st.columns([3, 2])
with left:
    st.dataframe(top, use_container_width=True, hide_index=True)
with right:
    if len(top):
        chart = top.copy()
        chart["attacker"] = chart["attacker"].str[:6] + "…" + chart["attacker"].str[-4:]
        st.bar_chart(chart.set_index("attacker")["sandwiches"], color="#ff0029")

df["front"] = "https://etherscan.io/tx/" + df["front_tx"]
st.subheader("Detections")
st.dataframe(
    df[["block", "attacker", "profit_pct_of_input", "front"]],
    column_config={"front": st.column_config.LinkColumn("Front tx")},
    use_container_width=True, hide_index=True,
)
st.markdown(
    '<div class="small-note">LIMITS: UNISWAP V2 ONLY · PATTERN-BASED, FALSE POSITIVES POSSIBLE · '
    'PROFIT IS GROSS, BEFORE GAS · ROWS OUTSIDE THE SIDEBAR RANGE ARE HIDDEN</div>',
    unsafe_allow_html=True,
)
