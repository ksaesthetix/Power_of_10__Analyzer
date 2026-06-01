# app.py

import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_option_menu import option_menu

from po10_scraper import (
    build_dataframe
)

from analytics import (
    prepare_analytics_df,
    get_personal_bests,
    get_season_bests,
    get_average_performance,
    get_performance_volatility,
    get_relative_improvement,
    get_yoy_changes,
    get_top_ranked_performances,
    add_rolling_average
)

# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Power of 10 Analyzer",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================================================
# NAVIGATION BAR
# =========================================================

PAGES = [
    "Summary",
    "Event Progression",
    "Personal Bests",
    "Seasonal Bests",
    "Top Ranked",
    "Relative Improvement",
    "Volatility",
    "YOY",
    "Seasonal Trend",
    "Rolling Average",
    "Average Performance",
]

if "page_idx" not in st.session_state:
    st.session_state["page_idx"] = 0

selected_page = option_menu(
    menu_title=None,
    options=PAGES,
    #icons=["speedometer2"] + ["bar-chart"] * 10,
    menu_icon="cast",
    default_index=st.session_state["page_idx"],
    orientation="horizontal",
)
st.session_state["page_idx"] = PAGES.index(selected_page)

st.title("Power of 10 Analyzer")

st.markdown(
    """
    Analyze athlete progression,
    seasonal bests,
    personal bests,
    rankings,
    and performance trends.
    """
)

# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.header("Filters")

    DEFAULT_COACH_ID = (
        "04129636-6880-4268-9266-de639957a483"
    )

    coach_id = DEFAULT_COACH_ID

    max_events = st.slider(
        "Top events to show",
        min_value=1,
        max_value=50,
        value=20
    )

    scrape_button = st.button("Refresh")


# =========================================================
# LOAD DATA
# =========================================================

@st.cache_data(show_spinner=False)
def load_data(coach_id: str):

    return build_dataframe(
        coach_id=coach_id,
        athlete_ids=[],
        scope="career"
    )


if scrape_button:
    st.session_state["df"] = None


if "df" not in st.session_state or scrape_button:

    with st.spinner(
        "Scraping Power of 10..."
    ):

        st.session_state["df"] = load_data(
            coach_id
        )


df = st.session_state.get("df")

if df is None or df.empty:

    st.warning("No data found.")
    st.stop()


# =========================================================
# ANALYTICS DF
# =========================================================

analytics_df = prepare_analytics_df(df)

# pb_df = get_personal_bests(
#     analytics_df
# )

# sb_df = get_season_bests(
#     analytics_df
# )

# avg_df = get_average_performance(
#     analytics_df
# )

# volatility_df = get_performance_volatility(
#     analytics_df
# )

# improvement_df = get_relative_improvement(
#     analytics_df
# )

# yoy_df = get_yoy_changes(
#     sb_df
# )

# top_ranked_df = get_top_ranked_performances(
#     analytics_df,
#     top_n=10
# )

# rolling_df = add_rolling_average(
#     analytics_df,
#     window=3
# )

# =========================================================
# FILTERS
# =========================================================

st.sidebar.markdown("---")

athletes = sorted(
    analytics_df["athlete_name"]
    .dropna()
    .unique()
    .tolist()
)

events = sorted(
    analytics_df["event"]
    .dropna()
    .unique()
    .tolist()
)

years = sorted(
    analytics_df["year"]
    .dropna()
    .unique()
    .tolist()
)

selected_athletes = st.sidebar.multiselect(
    "Athletes",
    athletes
)

selected_events = st.sidebar.multiselect(
    "Events",
    events
)

selected_years = st.sidebar.multiselect(
    "Years",
    years,
    default=years[-3:]
)

filtered_df = analytics_df.copy()

if selected_athletes:
    filtered_df = filtered_df[
        filtered_df["athlete_name"]
        .isin(selected_athletes)
    ]

if selected_events:
    filtered_df = filtered_df[
        filtered_df["event"]
        .isin(selected_events)
    ]

if selected_years:
    filtered_df = filtered_df[
        filtered_df["year"]
        .isin(selected_years)
    ]

# =========================================================
# FILTERED ANALYTICS TABLES
# =========================================================

pb_df = get_personal_bests(
    filtered_df
)

sb_df = get_season_bests(
    filtered_df
)

avg_df = get_average_performance(
    filtered_df
)

volatility_df = get_performance_volatility(
    filtered_df
)

improvement_df = get_relative_improvement(
    filtered_df
)

yoy_df = get_yoy_changes(
    sb_df
)

top_ranked_df = get_top_ranked_performances(
    filtered_df,
    top_n=10
)

rolling_df = add_rolling_average(
    filtered_df,
    window=3
)

# =========================================================
# RENDER FUNCTIONS
# =========================================================


def render_summary(df):
    st.header("📊 Dataset Summary")
    c1, c2, c3 = st.columns(3)
    c1.metric("Athletes", df["athlete_name"].nunique())
    c2.metric("Events", df["event"].nunique())
    c3.metric("Performances", len(df))


def render_event_progression(df, max_events=20):
    st.header("📈 Event Progression Charts")

    top_event_list = (
        df["event"]
        .value_counts()
        .head(max_events)
        .index
        .tolist()
    )

    if not top_event_list:
        st.info("No events to show.")
        return

    tabs = st.tabs(top_event_list)

    for tab, event in zip(tabs, top_event_list):

        with tab:

            subset = (
                df[df["event"] == event]
                .copy()
                .sort_values(["athlete_name", "year"])
            )

            if subset.empty:
                st.info("No performances found.")
                continue

            st.subheader(f"{event}")

            st.dataframe(
                subset[
                    [
                        "athlete_name",
                        "year",
                        "performance",
                        "venue",
                        "meeting",
                        "date",
                    ]
                ],
                use_container_width=True,
            )

            if subset["perf_numeric"].notna().any():

                plot_subset = subset[subset["perf_numeric"].notna()]

                fig = px.line(
                    plot_subset,
                    x="year",
                    y="perf_numeric",
                    color="athlete_name",
                    markers=True,
                    hover_data=["performance", "venue", "meeting", "date"],
                    template="plotly_dark",
                    title=f"{event} Career Progression",
                )

                fig.update_traces(mode="lines+markers", marker=dict(size=8), line=dict(width=2))

                fig.update_layout(
                    hovermode="closest",
                    legend_title_text="Athlete",
                    margin=dict(l=20, r=20, t=50, b=20),
                )

                if subset["is_track"].iloc[0]:
                    fig.update_yaxes(title="Seconds", autorange="reversed")
                else:
                    fig.update_yaxes(title="Meters")

                fig.update_xaxes(title="Year", tickmode="linear")

                st.plotly_chart(fig, use_container_width=True)

            else:
                st.warning("No numeric performances available.")


def render_personal_bests(pb_df):
    st.header("🥇 Personal Bests")
    st.dataframe(
        pb_df[["athlete_name", "event", "performance", "date", "venue"]]
        .sort_values(["event", "athlete_name"]),
        use_container_width=True,
    )


def render_seasonal_bests(sb_df):
    st.header("🎯 Seasonal Bests")
    st.dataframe(
        sb_df[["athlete_name", "event", "year", "performance", "date"]]
        .sort_values(["event", "year"]),
        use_container_width=True,
    )


def render_top_ranked(top_ranked_df):
    st.header("⭐ Top Ranked Performances")
    st.dataframe(
        top_ranked_df[["event", "athlete_name", "performance", "date", "venue"]],
        use_container_width=True,
    )


def render_relative_improvement(improvement_df):
    st.header("📈 Relative Improvement")
    st.dataframe(improvement_df.sort_values("improvement_pct", ascending=False), use_container_width=True)


def render_volatility(volatility_df):
    st.header("📊 Performance Volatility")
    st.dataframe(volatility_df.sort_values("volatility"), use_container_width=True)


def render_yoy_changes(yoy_df):
    st.header("📅 Year-over-Year Change")
    st.dataframe(
        yoy_df[["athlete_name", "event", "year", "performance", "change"]], use_container_width=True
    )


def render_seasonal_trend(sb_df):
    st.header("📊 Seasonal Best Progression")

    events = sorted(sb_df["event"].unique().tolist())
    if not events:
        st.info("No seasonal bests available.")
        return

    event_choice = st.selectbox("Select event", events)

    trend_df = sb_df[sb_df["event"] == event_choice]

    fig = px.line(
        trend_df,
        x="year",
        y="perf_numeric",
        color="athlete_name",
        markers=True,
        hover_data=["performance", "venue", "date"],
        template="plotly_dark",
        title=f"{event_choice} Seasonal Bests",
    )

    if not trend_df.empty and trend_df["is_track"].iloc[0]:
        fig.update_yaxes(autorange="reversed")

    st.plotly_chart(fig, use_container_width=True)


def render_rolling_average(rolling_df):
    st.header("📉 Rolling Average Trends")

    events = sorted(rolling_df["event"].unique().tolist())
    if not events:
        st.info("No rolling averages available.")
        return

    event_choice = st.selectbox("Select event for rolling average", events, key="rolling_event_choice")

    rolling_event_df = rolling_df[rolling_df["event"] == event_choice]

    fig2 = px.line(
        rolling_event_df,
        x="year",
        y="rolling_avg",
        color="athlete_name",
        markers=True,
        template="plotly_dark",
        title=f"{event_choice} Rolling Average",
    )

    if not rolling_event_df.empty and rolling_event_df["is_track"].iloc[0]:
        fig2.update_yaxes(autorange="reversed")

    st.plotly_chart(fig2, use_container_width=True)


def render_average_performance(avg_df):
    st.header("📊 Average Performance")
    st.dataframe(avg_df.sort_values(["event", "average_perf"]), use_container_width=True)


# call the renderer for the selected page
if selected_page == "Summary":
    render_summary(filtered_df)
elif selected_page == "Event Progression":
    render_event_progression(filtered_df, max_events=max_events)
elif selected_page == "Personal Bests":
    render_personal_bests(pb_df)
elif selected_page == "Seasonal Bests":
    render_seasonal_bests(sb_df)
elif selected_page == "Top Ranked":
    render_top_ranked(top_ranked_df)
elif selected_page == "Relative Improvement":
    render_relative_improvement(improvement_df)
elif selected_page == "Volatility":
    render_volatility(volatility_df)
elif selected_page == "YOY":
    render_yoy_changes(yoy_df)
elif selected_page == "Seasonal Trend":
    render_seasonal_trend(sb_df)
elif selected_page == "Rolling Average":
    render_rolling_average(rolling_df)
elif selected_page == "Average Performance":
    render_average_performance(avg_df)