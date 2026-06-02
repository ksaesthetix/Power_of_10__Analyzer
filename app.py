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
    get_season_bests,
    get_average_performance,
    get_performance_volatility,
    get_relative_improvement,
    get_yoy_changes,
    get_top_ranked_performances,
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

st.markdown(
    """
    <style>
    :root {
        --color-primary: #FDDA0D;
        --color-primary-variant: #221F1F;
        --color-bg-1: #191919;
        --color-bg-2: #2C2C2C;
        --color-bg-3: #333333;
        --color-accent-1: #DD6BCD;
        --color-accent-2: #67DAFA;
        --color-accent-3: #FCE00A;
        --color-grey-1: #E9EBEC;
        --color-grey-2: #706F6F;
        --color-dark-1: #0E0E0E;
        --color-light: #EFEFEF;
        --color-light-variant: #A1B4C4;
    }

    body, .stApp, .main, .block-container, .reportview-container .main {
        background-color: var(--color-bg-1) !important;
        color: var(--color-light) !important;
    }

    section[data-testid="stSidebar"] {
        background-color: var(--color-bg-2) !important;
        color: var(--color-light) !important;
    }

    .stButton>button, button {
        background-color: var(--color-accent-2) !important;
        color: var(--color-dark-1) !important;
        border: 1px solid var(--color-primary) !important;
    }

    .stButton>button:hover {
        background-color: var(--color-accent-3) !important;
    }

    .st-selectbox, .st-multiselect, .st-slider, .st-date_input {
        background-color: var(--color-bg-2) !important;
        color: var(--color-light) !important;
        border-color: var(--color-bg-3) !important;
    }

    .stMarkdown, .stText, .stHeader {
        color: var(--color-light) !important;
    }

    .css-10trblm.egzxvld1 {
        background-color: var(--color-bg-2) !important;
    }

    .css-1k5ctt2.egzxvld3 {
        background-color: var(--color-bg-3) !important;
    }

    .css-14xtw13.e8zbici2 {
        color: var(--color-light) !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# NAVIGATION BAR
# =========================================================

PAGES = [
    "Summary",
    "Performance Trends",
    "Event Summary",
    "Top Athletes by Year",
    "Distribution",
    "Performance vs Age",
    "Trend Momentum",
    "Top Ranked",
    "Relative Improvement",
    "Volatility",
    "YOY",
]

# Athlete names to omit from filter dropdowns across all pages
EXCLUDED_ATHLETES = {
    "Anna Lipman",
    "Keelan Welch",
}

# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    selected_page = option_menu(
        "Navigation",
        PAGES,
        default_index=st.session_state.get("page_idx", 0),
        orientation="vertical",
        styles={
            "container": {
                "padding": "0!important",
                "background-color": "var(--color-bg-2)",
            },
            "nav-link": {
                "font-size": "16px",
                "text-align": "left",
                "color": "var(--color-grey-1)",
                "margin": "0px",
                "padding": "10px 14px",
            },
            "nav-link-selected": {
                "background-color": "var(--color-primary)",
                "color": "var(--color-primary-variant)",
            },
            "icon": {
                "color": "var(--color-accent-1)",
                "font-size": "18px",
            },
        },
    )
    st.session_state["page_idx"] = PAGES.index(selected_page)

    st.markdown("---")
    st.header("Controls")

    DEFAULT_COACH_ID = (
        "04129636-6880-4268-9266-de639957a483"
    )

    coach_id = DEFAULT_COACH_ID

    scrape_button = st.button("Refresh Data")


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

# =========================================================
# FILTERS HELPER
# =========================================================

def get_page_filters(df, page_name=""):
    """Create filter UI and return selected filters."""
    col1, col2, col3, col4 = st.columns(4)
    
    athletes = sorted(
        [athlete for athlete in df["athlete_name"].dropna().unique().tolist()
         if athlete not in EXCLUDED_ATHLETES]
    )
    events = sorted(df["event"].dropna().unique().tolist())
    years = sorted(df["year"].dropna().unique().tolist())
    
    with col1:
        selected_athletes = st.multiselect("Athletes", athletes, key=f"athlete_{page_name}")
    with col2:
        selected_events = st.multiselect("Events", events, key=f"event_{page_name}")
    with col3:
        selected_years = st.multiselect("Years", years, default=years[-3:] if years else [], key=f"year_{page_name}")
    with col4:
        selected_indoor = st.selectbox("Indoor?", ["All", "Indoor", "Outdoor"], key=f"indoor_{page_name}")
    
    return selected_athletes, selected_events, selected_years, selected_indoor


def apply_filters(df, athletes, events, years, indoor="All"):
    """Apply filters to dataframe."""
    filtered = df.copy()
    if athletes:
        filtered = filtered[filtered["athlete_name"].isin(athletes)]
    if events:
        filtered = filtered[filtered["event"].isin(events)]
    if years:
        filtered = filtered[filtered["year"].isin(years)]
    if indoor == "Indoor":
        filtered = filtered[filtered["indoor"] == True]
    elif indoor == "Outdoor":
        filtered = filtered[filtered["indoor"] == False]
    return filtered


# =========================================================
# RENDER FUNCTIONS
# =========================================================


def render_summary(df):
    st.header("📊 Dataset Summary")
    st.markdown("Overview of the current dataset with counts for athletes, events, and performances based on the selected filters.")
    athletes_list, events_list, years_list, indoor_list = get_page_filters(df, "Summary")
    filtered_df = apply_filters(df, athletes_list, events_list, years_list, indoor_list)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Athletes", filtered_df["athlete_name"].nunique())
    c2.metric("Events", filtered_df["event"].nunique())
    c3.metric("Performances", len(filtered_df))


def render_performance_trends(df):
    st.header("📈 Performance Trends")
    st.markdown("Track athlete progression over time and compare all performances or seasonal bests for selected events.")
    athletes_list, events_list, years_list, indoor_list = get_page_filters(df, "Performance Trends")
    filtered_df = apply_filters(df, athletes_list, events_list, years_list, indoor_list)
    
    sb_df = get_season_bests(filtered_df)

    trend_mode = st.radio(
        "View",
        ["All Performances", "Seasonal Bests"],
        horizontal=True,
    )

    display_df = sb_df if trend_mode == "Seasonal Bests" else filtered_df

    top_event_list = display_df["event"].dropna().unique().tolist()

    if not top_event_list:
        st.info("No events to show.")
        return

    tabs = st.tabs(top_event_list)

    for tab, event in zip(tabs, top_event_list):

        with tab:

            subset = (
                display_df[display_df["event"] == event]
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
                    title=f"{event} {trend_mode}",
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


def render_event_summary(df):
    st.header("📋 Event Summary Statistics")
    st.markdown("View aggregated event-level statistics including average performances and variability for the selected dataset.")
    athletes_list, events_list, years_list, indoor_list = get_page_filters(df, "Event Summary")
    filtered_df = apply_filters(df, athletes_list, events_list, years_list, indoor_list)
    
    summary_df = get_event_summary_stats(filtered_df)
    
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


def render_top_athletes_by_year(df):
    st.header("🏅 Top Athletes by Year")
    st.markdown("Find the best athlete performances by year for each event to identify top competitors and trends.")
    events = sorted(df["event"].dropna().unique().tolist())
    selected_event = st.selectbox(
        "Select event",
        ["All"] + events,
        index=0,
        key="top_athletes_by_year_event_choice",
    )
    filtered_df = df if selected_event == "All" else df[df["event"] == selected_event]
    
    available_years = sorted(
        filtered_df["year"]
        .dropna()
        .unique()
        .tolist()
    )
    
    if not available_years:
        st.info("No year data available.")
        return
    
    selected_year = st.selectbox(
        "Select year",
        available_years,
        index=len(available_years) - 1,
    )
    
    top_year_df = get_top_athletes_by_year(
        filtered_df,
        selected_year,
        top_n=50,
    )
    
    if top_year_df.empty:
        st.info("No results for this year.")
        return

    st.dataframe(
        top_year_df[
            ["athlete_name", "event", "performance", "year", "venue", "meeting"]
        ],
        use_container_width=True,
    )

    #fig = px.bar(
    #    top_year_df,
    #    x="perf_numeric",
    #    y="event",
    #    color="athlete_name",
    #    orientation="h",
    #    title=f"Best Event Performances in {selected_year}",
    #    template="plotly_dark",
    #)
    #if top_year_df["is_track"].iloc[0]:
    #    fig.update_xaxes(autorange="reversed")

    #fig.update_layout(margin=dict(l=20, r=20, t=50, b=20))
    #st.plotly_chart(fig, use_container_width=True)


def render_distribution(df):
    st.header("📊 Performance Distribution by Event")
    st.markdown("Explore how athlete performances are distributed for each event and compare spread across competitors.")
    athletes_list, events_list, years_list, indoor_list = get_page_filters(df, "Distribution")
    filtered_df = apply_filters(df, athletes_list, events_list, years_list, indoor_list)
    
    dist_df = get_performance_distribution(filtered_df)
    
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


def render_performance_vs_age(df):
    st.header("👟 Performance vs Age")
    st.markdown("Analyze how athlete performances evolve with age and identify age-related trends for each event.")
    athletes_list, events_list, years_list, indoor_list = get_page_filters(df, "Performance vs Age")
    filtered_df = apply_filters(df, athletes_list, events_list, years_list, indoor_list)
    
    age_df = get_performance_vs_age(filtered_df)
    
    if age_df.empty:
        st.info("No age-based performance data available.")
        return

    events = sorted(age_df["event"].unique().tolist())
    event_choice = st.selectbox("Select event", events, key="age_event_choice")
    subset = age_df[age_df["event"] == event_choice]
    # Prefer to show an OLS trendline when available (requires statsmodels).
    # If statsmodels is not installed in the environment, fall back to a
    # scatter without the trendline and inform the user.
    try:
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
    except ModuleNotFoundError:
        fig = px.scatter(
            subset,
            x="age",
            y="perf_numeric",
            color="athlete_name",
            hover_data=["performance", "year", "age_group"],
            template="plotly_dark",
            title=f"{event_choice} Performance vs Age (trendline unavailable)",
        )
        st.info("Trendline unavailable: install 'statsmodels' to enable OLS trendlines.")

    if subset["is_track"].iloc[0]:
        fig.update_yaxes(autorange="reversed")

    fig.update_layout(margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig, use_container_width=True)


def render_trend_momentum(df):
    st.header("📈 Trend Slope / Momentum Metrics")
    st.markdown("Compare momentum across athletes and events using slope-based trend metrics for recent performance changes.")
    athletes_list, events_list, years_list, indoor_list = get_page_filters(df, "Trend Momentum")
    filtered_df = apply_filters(df, athletes_list, events_list, years_list, indoor_list)
    
    trend_df = get_trend_slopes(filtered_df)
    
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


def render_top_ranked(df):
    st.header("⭐ Top Ranked Performances")
    st.markdown("Highlight the highest ranked performances across athletes and events, focusing on the top results.")
    athletes_list, events_list, years_list, indoor_list = get_page_filters(df, "Top Ranked")
    filtered_df = apply_filters(df, athletes_list, events_list, years_list, indoor_list)
    
    top_ranked_df = get_top_ranked_performances(filtered_df, top_n=10)
    
    st.dataframe(
        top_ranked_df[["event", "athlete_name", "performance", "date", "venue"]],
        use_container_width=True,
    )


def render_relative_improvement(df):
    st.header("📈 Relative Improvement")
    st.markdown("Measure performance gains over time to highlight athletes improving fastest in each event.")
    athletes_list, events_list, years_list, indoor_list = get_page_filters(df, "Relative Improvement")
    filtered_df = apply_filters(df, athletes_list, events_list, years_list, indoor_list)
    
    improvement_df = get_relative_improvement(filtered_df)
    
    st.dataframe(improvement_df.sort_values("improvement_pct", ascending=False), use_container_width=True)


def render_volatility(df):
    st.header("📊 Performance Volatility")
    st.markdown("Show how consistent or variable athlete performances are across competitions and seasons.")
    athletes_list, events_list, years_list, indoor_list = get_page_filters(df, "Volatility")
    filtered_df = apply_filters(df, athletes_list, events_list, years_list, indoor_list)
    
    volatility_df = get_performance_volatility(filtered_df)
    
    st.dataframe(volatility_df.sort_values("volatility"), use_container_width=True)


def render_yoy_changes(df):
    st.header("📅 Year-over-Year Change")
    st.markdown("Compare seasonal bests between years to reveal performance improvements or declines.")
    athletes_list, events_list, years_list, indoor_list = get_page_filters(df, "YOY")
    filtered_df = apply_filters(df, athletes_list, events_list, years_list, indoor_list)
    
    sb_df = get_season_bests(filtered_df)
    yoy_df = get_yoy_changes(sb_df)
    
    st.dataframe(
        yoy_df[["athlete_name", "event", "year", "performance", "change"]], use_container_width=True
    )


# =========================================================
# PAGE DISPATCH
# =========================================================

if selected_page == "Summary":
    render_summary(analytics_df)
elif selected_page == "Performance Trends":
    render_performance_trends(analytics_df)
elif selected_page == "Event Summary":
    render_event_summary(analytics_df)
elif selected_page == "Top Athletes by Year":
    render_top_athletes_by_year(analytics_df)
elif selected_page == "Distribution":
    render_distribution(analytics_df)
elif selected_page == "Performance vs Age":
    render_performance_vs_age(analytics_df)
elif selected_page == "Trend Momentum":
    render_trend_momentum(analytics_df)
elif selected_page == "Top Ranked":
    render_top_ranked(analytics_df)
elif selected_page == "Relative Improvement":
    render_relative_improvement(analytics_df)
elif selected_page == "Volatility":
    render_volatility(analytics_df)
elif selected_page == "YOY":
    render_yoy_changes(analytics_df)
