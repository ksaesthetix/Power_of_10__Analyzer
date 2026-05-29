import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from po10_scraper import build_dataframe, infer_event_kind, parse_perf_numeric

st.set_page_config(
    page_title="Power of 10 Analyzer",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Power of 10 Analyzer")
st.markdown(
    "Use this app to scrape Power of 10 athlete performance histories, "
    "then explore event-by-event career progression charts and tables."
)

with st.sidebar:
    st.header("Filters")
    DEFAULT_COACH_ID = "04129636-6880-4268-9266-de639957a483"
    coach_id = DEFAULT_COACH_ID
    athlete_ids_text = ""
    scope = "career"

    if False:
        st.markdown(f"**Coach ID:** {coach_id}")
        athlete_ids_text = st.text_area(
            "Athlete IDs (one per line)",
            value="",
            help="Optional: paste athlete IDs here to scrape specific athletes instead of a coach roster.",
        )
        scope = st.selectbox("Performance scope", ["career", "current"], help="Career parses full history; current only parses the current year.")

    max_events = st.slider("Top events to show", min_value=1, max_value=50, value=40)

    athlete_options = []
    year_options = []
    indoor_options = []
    default_years: list[str] = []
    if "df" in st.session_state and st.session_state["df"] is not None and not st.session_state["df"].empty:
        athlete_options = sorted(st.session_state["df"]["athlete_name"].dropna().unique().tolist())
        year_options = sorted(st.session_state["df"]["year"].dropna().astype(int).astype(str).unique().tolist())
        indoor_options = sorted(st.session_state["df"]["indoor"].dropna().unique().tolist())
        default_years = year_options[-3:]

    selected_athlete = st.multiselect(
        "Filter athlete",
        options=athlete_options,
        default=[],
        help="Select one or more athletes to filter the data.",
    )
    selected_year = st.multiselect(
        "Filter year",
        options=year_options,
        default=default_years,
        help="Select one or more years to filter the data.",
    )
    selected_indoor_options = ["All"] + indoor_options
    selected_indoor = st.selectbox(
        "Filter indoor/outdoor",
        options=selected_indoor_options,
        index=0,
        help="Choose indoor, outdoor, or All performances.",
    )
    scrape_button = st.button("Refresh")

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

# Apply athlete filter if selected
if selected_athlete:
    df = df[df["athlete_name"].isin(selected_athlete)]

# Apply year filter if selected
if selected_year:
    df = df[df["year"].astype(str).isin(selected_year)]

# Apply indoor/outdoor filter if selected
if selected_indoor != "All":
    df = df[df["indoor"] == selected_indoor]

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
            plot_subset = subset[subset["perf_numeric"].notna()]
            fig = px.line(
                plot_subset,
                x="year",
                y="perf_numeric",
                color="athlete_name",
                markers=True,
                title=f"{event} progression",
                hover_data=["performance", "venue", "meeting", "date"],
                template="plotly_dark",
            )
            fig.update_traces(
                mode="lines+markers",
                marker=dict(size=8, line=dict(width=1, color="rgba(255,255,255,0.7)")),
                line=dict(width=2),
            )
            fig.update_layout(
                hovermode="closest",
                hoverlabel=dict(bgcolor="rgba(0, 0, 0, 0.8)", font_color="white"),
                legend_title_text="Athlete",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                    title_font_size=11,
                    bgcolor="rgba(0,0,0,0.5)",
                    bordercolor="rgba(255,255,255,0.2)",
                    borderwidth=1,
                ),
                margin=dict(l=40, r=30, t=60, b=40),
                font=dict(size=12),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            fig.update_xaxes(
                title_text="Year",
                showgrid=False,
                showline=True,
                linecolor="rgba(255,255,255,0.2)",
                tickmode="linear",
                tickfont_color="rgba(255,255,255,0.8)",
                title_font_color="rgba(255,255,255,0.9)",
                showspikes=False,
            )
            if subset["event_kind"].iloc[0] == "time":
                fig.update_yaxes(
                    title_text="Seconds",
                    autorange="reversed",
                    showgrid=False,
                    showline=True,
                    linecolor="rgba(255,255,255,0.2)",
                    tickfont_color="rgba(255,255,255,0.8)",
                    title_font_color="rgba(255,255,255,0.9)",
                    showspikes=False,
                )
            else:
                fig.update_yaxes(
                    title_text="Meters",
                    showgrid=False,
                    showline=True,
                    linecolor="rgba(255,255,255,0.2)",
                    tickfont_color="rgba(255,255,255,0.8)",
                    title_font_color="rgba(255,255,255,0.9)",
                    showspikes=False,
                )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No numeric plot available for this event.")
