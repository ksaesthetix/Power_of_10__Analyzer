import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from po10_scraper import build_dataframe, infer_event_kind, parse_perf_numeric

st.set_page_config(
    page_title="Power of 10 Career Analyzer",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Power of 10 Career Analyzer")
st.markdown(
    "Use this app to scrape Power of 10 athlete performance histories, "
    "then explore event-by-event career progression charts and tables."
)

with st.sidebar:
    st.header("Scrape settings")
    DEFAULT_COACH_ID = "04129636-6880-4268-9266-de639957a483"
    coach_id = DEFAULT_COACH_ID
    st.markdown(f"**Coach ID:** {coach_id}")
    athlete_ids_text = st.text_area(
        "Athlete IDs (one per line)",
        value="",
        help="Optional: paste athlete IDs here to scrape specific athletes instead of a coach roster.",
    )
    scope = st.selectbox("Performance scope", ["career", "current"], help="Career parses full history; current only parses the current year.")
    max_events = st.slider("Top events to show", min_value=1, max_value=12, value=12)
    st.markdown("---")
    st.write("Scraping may take time when the roster is large.")
    scrape_button = st.button("Scrape / Refresh")

athlete_ids = [line.strip() for line in athlete_ids_text.splitlines() if line.strip()]

@st.cache_data(show_spinner=False)
def load_data(coach_id: str, athlete_ids: tuple[str, ...], scope: str) -> "pd.DataFrame":
    return build_dataframe(coach_id=coach_id, athlete_ids=list(athlete_ids), scope=scope)

if scrape_button:
    st.session_state["df"] = None

if "df" not in st.session_state or scrape_button:
    with st.spinner("Scraping Power of 10 data..."):
        st.session_state["df"] = load_data(coach_id, tuple(athlete_ids), scope)

df = st.session_state.get("df")

if df is None or df.empty:
    st.warning("No data is loaded yet. Enter a coach ID or athlete IDs, then click Scrape / Refresh.")
    st.stop()

#st.success(f"Loaded {len(df)} performance rows from {df['athlete_name'].nunique()} athletes.")

st.sidebar.markdown("---")

# Athlete filter: show a dropdown of athlete names (All = no filter)
with st.sidebar:
    if df is not None and not df.empty:
        athlete_options = ["All"] + sorted(df["athlete_name"].dropna().unique().tolist())
        selected_athlete = st.selectbox("Filter athlete", athlete_options, index=0)
    else:
        selected_athlete = "All"

# Apply athlete filter if selected
if selected_athlete != "All":
    df = df[df["athlete_name"] == selected_athlete]

st.header("Dataset summary")
col1, col2, col3 = st.columns(3)
col1.metric("Athletes", f"{df['athlete_name'].nunique()}")
col2.metric("Events", f"{df['event'].nunique()}")
col3.metric("Performances", f"{len(df)}")

st.subheader("Top events")
# Build a small, well-named DataFrame for the top events to avoid duplicate column names
top_events = (
    df["event"].value_counts()
    .rename_axis("event")
    .reset_index(name="count")
    .head(12)
)
st.dataframe(top_events, width=900)

show_columns = ["athlete_name", "year", "performance", "indoor", "position", "venue", "meeting", "date"]

st.markdown("---")

st.subheader("Selected events charts")
tabs = st.tabs([f"{event}" for event in df["event"].value_counts().head(max_events).index.tolist()])
for tab, event in zip(tabs, df["event"].value_counts().head(max_events).index.tolist()):
    with tab:
        subset = df[df["event"] == event].copy().sort_values(["athlete_name", "year"])
        if subset.empty:
            st.write("No rows for this event.")
            continue
        subset["event_kind"] = subset["event"].apply(infer_event_kind)
        subset["perf_numeric"] = subset.apply(lambda row: parse_perf_numeric(row["performance"], row["event_kind"]), axis=1)
        st.write(f"{event}: {len(subset)} rows")
        st.dataframe(subset[show_columns].reset_index(drop=True), use_container_width=True)
        if subset["perf_numeric"].notna().any():
            fig = px.line(
                subset[subset["perf_numeric"].notna()],
                x="year",
                y="perf_numeric",
                color="athlete_name",
                markers=True,
                title=f"{event} progression",
                hover_data=["performance", "venue", "meeting", "date"],
            )
            if subset["event_kind"].iloc[0] == "time":
                fig.update_yaxes(title_text="Seconds", autorange="reversed")
            else:
                fig.update_yaxes(title_text="Meters")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No numeric plot available for this event.")
