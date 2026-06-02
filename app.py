# app.py

import streamlit as st
import pandas as pd
import plotly.express as px

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
    add_rolling_average,
    get_event_summary_stats,
    get_top_athletes_by_year,
    get_performance_distribution,
    get_performance_vs_age,
    get_trend_slopes,
)

# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Power of 10 Analyzer",
    layout="wide",
    initial_sidebar_state="expanded",
)

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
# NAVIGATION BAR
# =========================================================

PAGES = [
    "Summary",
    "Event Progression",
    "Event Summary",
    "Top Athletes by Year",
    "Distribution",
    "Performance vs Age",
    "Trend Momentum",
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

# Custom CSS for navigation bar
st.markdown("""
<style>
.nav-container {
    display: flex;
    gap: 8px;
    margin: 20px 0;
    padding: 12px;
    background-color: #f0f2f6;
    border-radius: 8px;
    flex-wrap: wrap;
}
.nav-item {
    padding: 10px 18px;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 500;
    font-size: 14px;
    border: 2px solid transparent;
    transition: all 0.3s ease;
    white-space: nowrap;
}
.nav-item:hover {
    background-color: #e0e5f1;
    border-color: #1f77b4;
}
.nav-item.active {
    background-color: #ff6b6b;
    color: white;
    border-color: #ff6b6b;
}
</style>
""", unsafe_allow_html=True)

# Create navigation bar using columns
cols = st.columns(len(PAGES))
selected_page = None

for idx, (col, page) in enumerate(zip(cols, PAGES)):
    with col:
        if st.button(
            page,
            key=f"nav_{idx}",
            use_container_width=True,
            help=f"Go to {page}"
        ):
            st.session_state["page_idx"] = idx
            selected_page = page

# Get selected page from session state
if selected_page is None:
    selected_page = PAGES[st.session_state["page_idx"]]

st.markdown("---")

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

available_years = sorted(
    filtered_df["year"]
    .dropna()
    .unique()
    .tolist()
)

selected_top_year = None
if available_years:
    selected_top_year = st.sidebar.selectbox(
        "Top athletes year",
        available_years,
        index=len(available_years) - 1,
    )

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

summary_df = get_event_summary_stats(filtered_df)

top_year_df = (
    get_top_athletes_by_year(
        filtered_df,
        selected_top_year,
        top_n=50,
    ) if selected_top_year is not None else pd.DataFrame()
)

dist_df = get_performance_distribution(filtered_df)

age_df = get_performance_vs_age(filtered_df)

trend_df = get_trend_slopes(filtered_df)

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


def render_event_summary(summary_df):
    st.header("📋 Event Summary Statistics")
    if summary_df.empty:
        st.info("No event summary data available.")
        return

    st.dataframe(
        summary_df.sort_values("event"),
        use_container_width=True,
    )

    fig = px.bar(
        summary_df,
        x="event",
        y="mean_perf",
        error_y="std_perf",
        title="Mean Performance by Event",
        template="plotly_dark",
    )
    fig.update_layout(xaxis_tickangle=-45, margin=dict(l=20, r=20, t=50, b=120))
    st.plotly_chart(fig, use_container_width=True)


def render_top_athletes_by_year(top_year_df, year):
    st.header(f"🏅 Top Athletes in {year}")
    if top_year_df.empty:
        st.info("No results for this year.")
        return

    st.dataframe(
        top_year_df[
            ["athlete_name", "event", "performance", "year", "venue", "meeting"]
        ],
        use_container_width=True,
    )

    fig = px.bar(
        top_year_df,
        x="perf_numeric",
        y="event",
        color="athlete_name",
        orientation="h",
        title=f"Best Event Performances in {year}",
        template="plotly_dark",
    )
    if top_year_df["is_track"].iloc[0]:
        fig.update_xaxes(autorange="reversed")

    fig.update_layout(margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig, use_container_width=True)


def render_distribution(dist_df):
    st.header("📊 Performance Distribution by Event")
    if dist_df.empty:
        st.info("No distribution data available.")
        return

    events = sorted(dist_df["event"].unique().tolist())
    event_choice = st.selectbox("Select event", events, key="distribution_event_choice")
    subset = dist_df[dist_df["event"] == event_choice]

    fig = px.histogram(
        subset,
        x="perf_numeric",
        nbins=25,
        color="athlete_name",
        marginal="box",
        template="plotly_dark",
        title=f"{event_choice} Performance Distribution",
    )

    if subset["is_track"].iloc[0]:
        fig.update_xaxes(autorange="reversed")
        fig.update_xaxes(title="Seconds")
    else:
        fig.update_xaxes(title="Meters")

    fig.update_layout(margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig, use_container_width=True)


def render_performance_vs_age(age_df):
    st.header("👟 Performance vs Age")
    if age_df.empty:
        st.info("No age-based performance data available.")
        return

    events = sorted(age_df["event"].unique().tolist())
    event_choice = st.selectbox("Select event", events, key="age_event_choice")
    subset = age_df[age_df["event"] == event_choice]

    fig = px.scatter(
        subset,
        x="age",
        y="perf_numeric",
        color="athlete_name",
        trendline="ols",
        hover_data=["performance", "year", "age_group"],
        template="plotly_dark",
        title=f"{event_choice} Performance vs Age",
    )

    if subset["is_track"].iloc[0]:
        fig.update_yaxes(autorange="reversed")

    fig.update_layout(margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig, use_container_width=True)


def render_trend_momentum(trend_df):
    st.header("📈 Trend Slope / Momentum Metrics")
    if trend_df.empty:
        st.info("No trend momentum data available.")
        return

    st.dataframe(
        trend_df.sort_values("momentum", ascending=False),
        use_container_width=True,
    )

    fig = px.bar(
        trend_df,
        x="momentum",
        y="athlete_name",
        color="event",
        orientation="h",
        title="Trend Momentum by Athlete/Event",
        template="plotly_dark",
    )
    fig.update_layout(margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig, use_container_width=True)


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
elif selected_page == "Event Summary":
    render_event_summary(summary_df)
elif selected_page == "Top Athletes by Year":
    render_top_athletes_by_year(top_year_df, selected_top_year)
elif selected_page == "Distribution":
    render_distribution(dist_df)
elif selected_page == "Performance vs Age":
    render_performance_vs_age(age_df)
elif selected_page == "Trend Momentum":
    render_trend_momentum(trend_df)
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