# app.py

import os

import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_option_menu import option_menu

from po10_scraper import (
    build_dataframe,
    Po10AuthError,
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
    # new analyses
    add_relative_to_best,
    get_consistency,
    get_pb_timeline,
    get_pb_progression,
    get_season_shape,
    classify_meeting,
    get_championship_comparison,
    get_results_record,
    get_legal_vs_all_pbs,
    LEGAL_WIND_LIMIT,
    add_days_since_previous,
    get_competition_load,
    fit_age_curve,
    get_age_curve_residuals,
    project_next_season,
    format_numeric_perf,
    get_event_ratios,
    EVENT_RATIO_BENCHMARKS,
    load_standards,
    compare_to_standards,
    STANDARDS_COLUMNS,
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

    body,
    .stApp,
    .stApp .main,
    .stApp .main .block-container,
    .reportview-container .main {
        background-color: var(--color-bg-1) !important;
        color: var(--color-light) !important;
    }

    section[data-testid="stSidebar"],
    .css-1d391kg .css-1d391kg {
        background-color: var(--color-bg-2) !important;
        color: var(--color-light) !important;
    }

    .stButton>button,
    button {
        background-color: var(--color-primary) !important;
        color: var(--color-dark-1) !important;
        border: 1px solid var(--color-primary) !important;
        border-radius: 14px !important;
    }

    .stButton>button:hover,
    button:hover {
        background-color: var(--color-accent-3) !important;
    }

    div[data-baseweb="select"],
    div[data-baseweb="select"] > div,
    .stSelectbox,
    .stSelectbox>div,
    .stMultiSelect,
    .stMultiSelect>div,
    .stDateInput,
    .stTextInput,
    .stNumberInput,
    .stSlider,
    .stTextInput>div {
        
        color: var(--color-light) !important;
        
        border-radius: 14px !important;
    }

    .stSlider .css-1n76uvr {
        border-radius: 14px !important;
    }

    div[data-testid="stForm"] *,
    div[data-testid="stMetric"] *,
    .stMarkdown,
    .stText,
    .stHeader,
    .css-14xtw13.e8zbici2,
    .css-10trblm.egzxvld1,
    .css-1k5ctt2.egzxvld3 {
        color: var(--color-light) !important;
    }

    .st-bf {
        background-color: var(--color-bg-2) !important;
    }

    .st-bs,
    .st-bu,
    .st-bv {
        background-color: var(--color-bg-3) !important;
    }

    .css-1r6slb0,
    .css-1p5g3er,
    .css-ya1uwj {
        background-color: var(--color-bg-2) !important;
        color: var(--color-light) !important;
    }

    .css-18e3th9 {
        background-color: var(--color-bg-1) !important;
    }

    .css-1vq4p4l {
        color: var(--color-light) !important;
    }

    div[role="tablist"] > button {
        color: var(--color-light) !important;
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        border-radius: 14px !important;
        border-bottom: 2px solid transparent !important;
    }

    div[role="tablist"] > button:hover {
        background-color: rgba(253, 218, 13, 0.08) !important;
    }

    div[role="tablist"] > button[aria-selected="true"] {
        color: var(--color-light) !important;
        background-color: transparent !important;
        border: none !important;
    }

    div[data-baseweb="tag"] {
        background-color: var(--color-bg-3) !important;
        color: var(--color-light) !important;
        border: none !important;
        border-radius: 14px !important;
    }

    div[data-baseweb="tag"] .tagText,
    div[data-baseweb="tag"] .value {
        color: var(--color-light) !important;
    }

    div[data-baseweb="tag"][data-state="selected"],
    div[data-baseweb="tag"][data-selected="true"],
    div[data-baseweb="tag"] [data-state="selected"] {
        background-color: var(--color-primary) !important;
        color: var(--color-primary-variant) !important;
        border: none !important;
    }

    div[data-baseweb="tag"][data-state="selected"] .tagText,
    div[data-baseweb="tag"][data-selected="true"] .tagText,
    div[data-baseweb="tag"] [data-state="selected"] .tagText {
        color: var(--color-primary-variant) !important;
    }

    div[data-baseweb="tag"] [data-state="selected"] svg,
    div[data-baseweb="tag"][data-state="selected"] svg,
    div[data-baseweb="tag"][data-selected="true"] svg {
        color: var(--color-primary-variant) !important;
    }

    .st-bx {
        background-color: var(--color-bg-3) !important;
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
    "PB Timeline",
    "Performance Trends",
    "Season Shape",
    "Consistency",
    "Championships",
    "Wind",
    "Competition Load",
    "Event Summary",
    "Distribution",
    "Top Athletes by Year",
    "Top Ranked",
    "Relative Improvement",
    "YOY",
    "Trend Momentum",
    "Performance vs Age",
    "Age Curve",
    "Projection",
    "Event Suitability",
    "Standards",
]

STANDARDS_FILE = "standards.csv"   # optional, repo root - see Standards page

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
                "background-color": "var(--color-bg-1)",
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
                "color": "var(--color-light)",
                "font-size": "18px",
            },
        },
    )
    st.session_state["page_idx"] = PAGES.index(selected_page)

    DEFAULT_COACH_ID = (
        "04129636-6880-4268-9266-de639957a483"
    )

    coach_id = DEFAULT_COACH_ID

    # ---- Power of 10 session ----
    # Po10 now requires an account to view athlete data, and its sign-in
    # form is behind reCAPTCHA, so the app can't log in by itself. Instead,
    # sign in once in your browser and paste that session's Cookie header
    # here. Seeded once from .streamlit/secrets.toml ([po10] cookie) or the
    # PO10_COOKIE env var; after that session_state is the source of truth.
    def _po10_secret(key: str) -> str:
        try:
            return str(st.secrets["po10"][key])
        except Exception:
            return ""

    if "po10_cookie" not in st.session_state:
        st.session_state["po10_cookie"] = (
            _po10_secret("cookie") or os.environ.get("PO10_COOKIE", "")
        )

    cookie_missing = not st.session_state["po10_cookie"].strip()

    with st.expander("Power of 10 session", expanded=cookie_missing):
        st.caption(
            "Po10 requires a signed-in account. Sign in at powerof10.uk in "
            "your browser, then paste your session cookie here. It is held in "
            "memory for this session only."
        )
        st.text_input(
            "Session cookie",
            type="password",
            key="po10_cookie",
            placeholder="name=value; name2=value2; ...",
        )
        with st.popover("How do I get this?"):
            st.markdown(
                """
1. Sign in at **powerof10.uk** in your browser (complete the reCAPTCHA).
2. Press **F12** → **Network** tab, then reload any Po10 page.
3. Click the first request to `www.powerof10.uk`.
4. Under **Request Headers**, copy the whole value of the **Cookie** line.
5. Paste it here. Repeat when it expires — the app will tell you.
                """
            )

    scrape_button = st.button("Refresh Data")


# =========================================================
# LOAD DATA
# =========================================================

@st.cache_data(show_spinner=False)
def load_data(coach_id: str, _cookie: str):
    # Leading underscore keeps the cookie out of the cache key, so the
    # session token is never hashed/stored by st.cache_data.
    return build_dataframe(
        coach_id=coach_id,
        athlete_ids=[],
        scope="career",
        cookie_header=_cookie,
    )


if scrape_button:
    # Previously the cached frame was returned even after "Refresh Data";
    # clearing the cache forces a genuine re-scrape (and a fresh sign-in).
    load_data.clear()
    st.session_state["df"] = None


if st.session_state.get("df") is None:

    po10_cookie = st.session_state.get("po10_cookie", "").strip()

    if not po10_cookie:
        st.info(
            "Paste your Power of 10 session cookie in the sidebar "
            "to load athlete data."
        )
        st.stop()

    with st.spinner(
        "Scraping Power of 10..."
    ):
        try:
            st.session_state["df"] = load_data(
                coach_id,
                po10_cookie,
            )
        except Po10AuthError as exc:
            st.error(f"Power of 10 session problem: {exc}")
            st.stop()


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

def get_page_filters(df, page_name="", include_years=True):
    """Create filter UI and return (athletes, events, years, indoor, wind)."""
    col1, col2, col3, col4, col5 = st.columns(5)

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
        if include_years:
            selected_years = st.multiselect("Years", years, default=years[-3:] if years else [], key=f"year_{page_name}")
        else:
            selected_years = []
            st.caption("All seasons (career view)")
    with col4:
        selected_indoor = st.selectbox("Indoor?", ["All", "Indoor", "Outdoor"], key=f"indoor_{page_name}")
    with col5:
        selected_wind = st.selectbox(
            "Wind",
            ["Legal only", "All marks"],
            key=f"wind_{page_name}",
            help=f"Legal only drops marks with a tailwind over +{LEGAL_WIND_LIMIT:.1f} m/s. "
                 "Marks with no wind reading are kept.",
        )

    return selected_athletes, selected_events, selected_years, selected_indoor, selected_wind


def apply_filters(df, athletes, events, years, indoor="All", wind="Legal only"):
    """Apply filters to dataframe."""
    filtered = df.copy()
    if athletes:
        filtered = filtered[filtered["athlete_name"].isin(athletes)]
    else:
        filtered = filtered[~filtered["athlete_name"].isin(EXCLUDED_ATHLETES)]
    if events:
        filtered = filtered[filtered["event"].isin(events)]
    if years:
        filtered = filtered[filtered["year"].isin(years)]
    if indoor == "Indoor":
        filtered = filtered[filtered["indoor"] == True]
    elif indoor == "Outdoor":
        filtered = filtered[filtered["indoor"] == False]
    if wind == "Legal only" and "wind_assisted" in filtered.columns:
        filtered = filtered[~filtered["wind_assisted"]]
    return filtered


def _set_perf_axis(fig, is_track, axis="y"):
    """Label a performance axis and reverse it for timed events."""
    kwargs = dict(title="Seconds", autorange="reversed") if is_track else dict(title="Metres / points")
    (fig.update_yaxes if axis == "y" else fig.update_xaxes)(**kwargs)


def _month_axis(fig):
    """Turn a day-of-year x axis into month labels."""
    starts = [1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    fig.update_xaxes(title="Time of year", tickmode="array", tickvals=starts, ticktext=names)


# =========================================================
# RENDER FUNCTIONS
# =========================================================


def render_summary(df):
    st.header("📊 Dataset Summary")
    st.markdown("Overview of the current dataset with counts for athletes, events, and performances based on the selected filters.")
    athletes_list, events_list, years_list, indoor_list, wind_list = get_page_filters(df, "Summary")
    filtered_df = apply_filters(df, athletes_list, events_list, years_list, indoor_list, wind_list)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Athletes", filtered_df["athlete_name"].nunique())
    c2.metric("Events", filtered_df["event"].nunique())
    c3.metric("Performances", len(filtered_df))


def render_performance_trends(df):
    st.header("📈 Performance Trends")
    st.markdown("Track athlete progression over time and compare all performances or seasonal bests for selected events.")
    athletes_list, events_list, years_list, indoor_list, wind_list = get_page_filters(df, "Performance Trends")
    filtered_df = apply_filters(df, athletes_list, events_list, years_list, indoor_list, wind_list)
    
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
                width="stretch",
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

                st.plotly_chart(fig, width="stretch")

            else:
                st.warning("No numeric performances available.")


def render_event_summary(df):
    st.header("📋 Event Summary Statistics")
    st.markdown("View aggregated event-level statistics including average performances and variability for the selected dataset.")
    athletes_list, events_list, years_list, indoor_list, wind_list = get_page_filters(df, "Event Summary")
    filtered_df = apply_filters(df, athletes_list, events_list, years_list, indoor_list, wind_list)
    
    summary_df = get_event_summary_stats(filtered_df)
    
    if summary_df.empty:
        st.info("No event summary data available.")
        return

    st.dataframe(
        summary_df.sort_values("event"),
        width="stretch",
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
    st.plotly_chart(fig, width="stretch")


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
        width="stretch",
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
    #st.plotly_chart(fig, width="stretch")


def render_distribution(df):
    st.header("📊 Performance Distribution by Event")
    st.markdown("Explore how athlete performances are distributed for each event and compare spread across competitors.")
    athletes_list, events_list, years_list, indoor_list, wind_list = get_page_filters(df, "Distribution")
    filtered_df = apply_filters(df, athletes_list, events_list, years_list, indoor_list, wind_list)
    
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
    st.plotly_chart(fig, width="stretch")


def render_performance_vs_age(df):
    st.header("👟 Performance vs Age")
    st.markdown("Analyze how athlete performances evolve with age and identify age-related trends for each event.")
    athletes_list, events_list, years_list, indoor_list, wind_list = get_page_filters(df, "Performance vs Age")
    filtered_df = apply_filters(df, athletes_list, events_list, years_list, indoor_list, wind_list)
    
    age_df = get_performance_vs_age(filtered_df)
    
    if age_df.empty:
        st.info(
            "No age data available — Po10 didn't show a date of birth or a "
            "current age for these athletes. Try Refresh Data to re-scrape."
        )
        return

    events = sorted(age_df["event"].unique().tolist())
    event_choice = st.selectbox("Select event", events, key="age_event_choice")
    subset = age_df[age_df["event"] == event_choice]

    n_estimated = int((subset["age_source"] == "estimated").sum())
    if n_estimated:
        st.caption(
            f"Ages for {n_estimated} of {len(subset)} performances are estimated from "
            "the athlete's current age on Po10 (accurate to ±6 months); the rest use "
            "a published date of birth."
        )

    hover = {
        "age_decimal": ":.1f",
        "age": True,
        "age_group": True,
        "performance": True,
        "date": True,
        "year": True,
        "athlete_name": False,
    }

    # Prefer to show an OLS trendline when available (requires statsmodels).
    # If statsmodels is not installed in the environment, fall back to a
    # scatter without the trendline and inform the user.
    try:
        fig = px.scatter(
            subset,
            x="age_decimal",
            y="perf_numeric",
            color="athlete_name",
            trendline="ols",
            hover_data=hover,
            template="plotly_dark",
            title=f"{event_choice} Performance vs Age",
        )
    except ModuleNotFoundError:
        fig = px.scatter(
            subset,
            x="age_decimal",
            y="perf_numeric",
            color="athlete_name",
            hover_data=hover,
            template="plotly_dark",
            title=f"{event_choice} Performance vs Age (trendline unavailable)",
        )
        st.info("Trendline unavailable: install 'statsmodels' to enable OLS trendlines.")

    fig.update_xaxes(title="Age at performance (years)")
    if subset["is_track"].iloc[0]:
        fig.update_yaxes(title="Seconds", autorange="reversed")
    else:
        fig.update_yaxes(title="Metres")

    fig.update_layout(margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig, width="stretch")


def render_trend_momentum(df):
    st.header("📈 Trend Slope / Momentum Metrics")
    st.markdown("Compare momentum across athletes and events using slope-based trend metrics for recent performance changes.")
    athletes_list, events_list, years_list, indoor_list, wind_list = get_page_filters(df, "Trend Momentum")
    filtered_df = apply_filters(df, athletes_list, events_list, years_list, indoor_list, wind_list)
    
    trend_df = get_trend_slopes(filtered_df)
    
    if trend_df.empty:
        st.info("No trend momentum data available.")
        return

    st.dataframe(
        trend_df.sort_values("momentum", ascending=False),
        width="stretch",
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
    st.plotly_chart(fig, width="stretch")


def render_top_ranked(df):
    st.header("⭐ Top Ranked Performances")
    st.markdown("Highlight the highest ranked performances across athletes and events, focusing on the top results.")
    athletes_list, events_list, years_list, indoor_list, wind_list = get_page_filters(df, "Top Ranked")
    filtered_df = apply_filters(df, athletes_list, events_list, years_list, indoor_list, wind_list)
    
    if filtered_df.empty:
        st.info("No performances in the selection.")
        return

    top_ranked_df = get_top_ranked_performances(filtered_df, top_n=10)
    
    st.dataframe(
        top_ranked_df[["event", "athlete_name", "performance", "date", "venue"]],
        width="stretch",
    )


def render_relative_improvement(df):
    st.header("📈 Relative Improvement")
    st.markdown("Measure performance gains over time to highlight athletes improving fastest in each event.")
    athletes_list, events_list, years_list, indoor_list, wind_list = get_page_filters(df, "Relative Improvement")
    filtered_df = apply_filters(df, athletes_list, events_list, years_list, indoor_list, wind_list)
    
    if filtered_df.empty:
        st.info("No performances in the selection.")
        return

    improvement_df = get_relative_improvement(filtered_df)
    
    st.dataframe(improvement_df.sort_values("improvement_pct", ascending=False), width="stretch")


def render_consistency(df):
    st.header("🎯 Consistency")
    st.markdown(
        "How close each athlete gets to their own best, race after race. Everything is expressed "
        "as a percentage of their best mark in the selection (100 = equal to it), so a 100 m "
        "sprinter and a 1500 m runner can be compared on the same scale."
    )
    athletes_list, events_list, years_list, indoor_list, wind_list = get_page_filters(df, "Consistency")
    filtered_df = apply_filters(df, athletes_list, events_list, years_list, indoor_list, wind_list)
    if filtered_df.empty:
        st.info("No performances in the selection.")
        return

    within = st.slider("Count a mark as a 'hit' when it is within this % of the athlete's best", 0.5, 5.0, 2.0, 0.5)
    cons_df = get_consistency(filtered_df, within_pct=within)
    hit_col = f"hit_rate_within_{within:g}pct"

    st.dataframe(
        cons_df.sort_values(hit_col, ascending=False).rename(columns={hit_col: f"hit rate within {within:g}% (%)"}),
        width="stretch",
    )

    fig = px.bar(
        cons_df.sort_values(hit_col),
        x=hit_col,
        y="athlete_name",
        color="event",
        orientation="h",
        barmode="group",
        template="plotly_dark",
        title=f"Share of marks within {within:g}% of best",
        labels={hit_col: "Hit rate (%)", "athlete_name": "Athlete"},
    )
    fig.update_layout(margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig, width="stretch")

    events = sorted(filtered_df["event"].unique().tolist())
    event_choice = st.selectbox("Spread of marks for event", events, key="consistency_event_choice")
    rel = add_relative_to_best(filtered_df[filtered_df["event"] == event_choice])
    fig2 = px.box(
        rel,
        x="athlete_name",
        y="pct_of_pb",
        points="all",
        hover_data=["performance", "date", "meeting"],
        template="plotly_dark",
        title=f"{event_choice}: every mark as % of best",
        labels={"pct_of_pb": "% of best", "athlete_name": "Athlete"},
    )
    fig2.update_layout(margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig2, width="stretch")

    with st.expander("Raw volatility (standard deviation in event units)"):
        st.dataframe(get_performance_volatility(filtered_df).sort_values("volatility"), width="stretch")


def render_yoy_changes(df):
    st.header("📅 Year-over-Year Change")
    st.markdown("Compare seasonal bests between years to reveal performance improvements or declines.")
    athletes_list, events_list, years_list, indoor_list, wind_list = get_page_filters(df, "YOY")
    filtered_df = apply_filters(df, athletes_list, events_list, years_list, indoor_list, wind_list)
    
    if filtered_df.empty:
        st.info("No performances in the selection.")
        return

    sb_df = get_season_bests(filtered_df)
    yoy_df = get_yoy_changes(sb_df)
    
    st.dataframe(
        yoy_df[["athlete_name", "event", "year", "performance", "change"]], width="stretch"
    )


def render_pb_timeline(df):
    st.header("🏆 PB Timeline")
    st.markdown(
        "Career PB for every athlete/event, how long ago it was set, and how this season's best "
        "compares. 'Off by >3%' for a long time is usually worth a conversation."
    )
    athletes_list, events_list, _, indoor_list, wind_list = get_page_filters(df, "PB Timeline", include_years=False)
    filtered_df = apply_filters(df, athletes_list, events_list, [], indoor_list, wind_list)
    if filtered_df.empty:
        st.info("No performances in the selection.")
        return

    timeline = get_pb_timeline(filtered_df)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Athlete/event pairs", len(timeline))
    c2.metric("PB this season", int((timeline["status"] == "PB this season").sum()))
    c3.metric("Within 1%", int((timeline["status"] == "Within 1%").sum()))
    c4.metric("Off by >3%", int((timeline["status"] == "Off by >3%").sum()))

    show = timeline[[
        "athlete_name", "event", "pb", "pb_date", "pb_meeting", "days_since_pb",
        "latest_season", "latest_sb", "latest_sb_pct_of_pb", "status", "marks",
    ]]
    st.dataframe(show, width="stretch", hide_index=True)

    events = sorted(filtered_df["event"].unique().tolist())
    event_choice = st.selectbox("PB progression for event", events, key="pb_timeline_event_choice")
    prog = get_pb_progression(filtered_df[filtered_df["event"] == event_choice])
    if prog.empty:
        return
    fig = px.line(
        prog.sort_values("perf_date_parsed"),
        x="perf_date_parsed",
        y="perf_numeric",
        color="athlete_name",
        line_shape="hv",
        markers=True,
        hover_data=["performance", "date", "meeting", "venue"],
        template="plotly_dark",
        title=f"{event_choice}: every PB, when it was set",
        labels={"perf_date_parsed": "Date", "athlete_name": "Athlete"},
    )
    _set_perf_axis(fig, bool(prog["is_track"].iloc[0]))
    fig.update_layout(margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig, width="stretch")


def render_season_shape(df):
    st.header("🌤️ Season Shape")
    st.markdown(
        "Performance against the time of year, one line per season. Does the best mark land "
        "when it needs to (championship window) or in May with a fade after?"
    )
    athletes_list, events_list, years_list, indoor_list, wind_list = get_page_filters(df, "Season Shape")
    filtered_df = apply_filters(df, athletes_list, events_list, years_list, indoor_list, wind_list)
    if filtered_df.empty:
        st.info("No performances in the selection.")
        return

    c1, c2 = st.columns(2)
    with c1:
        athlete_choice = st.selectbox(
            "Athlete", sorted(filtered_df["athlete_name"].unique().tolist()), key="season_shape_athlete"
        )
    athlete_df = filtered_df[filtered_df["athlete_name"] == athlete_choice]
    with c2:
        event_choice = st.selectbox(
            "Event", sorted(athlete_df["event"].unique().tolist()), key="season_shape_event"
        )
    subset = add_relative_to_best(athlete_df[athlete_df["event"] == event_choice]).sort_values("perf_date_parsed")
    subset = subset.assign(season=subset["year"].astype(str))
    is_track = bool(subset["is_track"].iloc[0])

    fig = px.line(
        subset,
        x="day_of_year",
        y="perf_numeric",
        color="season",
        markers=True,
        hover_data=["performance", "date", "meeting", "pct_of_sb"],
        template="plotly_dark",
        title=f"{athlete_choice} - {event_choice} by time of year",
        labels={"season": "Season"},
    )
    sb_points = subset[subset["perf_numeric"] == subset["sb_numeric"]]
    fig.add_scatter(
        x=sb_points["day_of_year"], y=sb_points["perf_numeric"], mode="markers",
        marker=dict(size=14, symbol="star", color="#FDDA0D", line=dict(width=1, color="#191919")),
        name="Season's best", hovertext=sb_points["performance"],
    )
    _set_perf_axis(fig, is_track)
    _month_axis(fig)
    fig.update_layout(margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig, width="stretch")

    shape = get_season_shape(filtered_df)
    st.subheader("Where in the season the best mark fell")
    st.caption("sb_race_number = which outing of the season produced the SB; first/last mark % show the start and end of season relative to the SB.")
    st.dataframe(
        shape.sort_values(["athlete_name", "event", "year"]),
        width="stretch",
        hide_index=True,
    )


def render_championships(df):
    st.header("🏟️ Championships vs Ordinary Meets")
    st.markdown(
        "Do athletes rise to the big occasion? Each mark is expressed as % of the athlete's best, "
        "then averaged separately for championship meets and everything else. A positive delta "
        "means they perform relatively better at championships."
    )
    athletes_list, events_list, years_list, indoor_list, wind_list = get_page_filters(df, "Championships")
    filtered_df = apply_filters(df, athletes_list, events_list, years_list, indoor_list, wind_list)
    if filtered_df.empty:
        st.info("No performances in the selection.")
        return

    comp = get_championship_comparison(filtered_df)
    if comp.empty:
        st.info("No meetings in the selection were recognised as championships.")
    else:
        st.dataframe(comp, width="stretch", hide_index=True)
        plot_df = comp.dropna(subset=["delta_pct_points"])
        if not plot_df.empty:
            fig = px.bar(
                plot_df.sort_values("delta_pct_points"),
                x="delta_pct_points",
                y="athlete_name",
                color="event",
                orientation="h",
                barmode="group",
                template="plotly_dark",
                title="Championship performance vs other meets (percentage points of best)",
                labels={"delta_pct_points": "Championship minus other (pp)", "athlete_name": "Athlete"},
            )
            fig.add_vline(x=0, line_dash="dash", line_color="#A1B4C4")
            fig.update_layout(margin=dict(l=20, r=20, t=50, b=20))
            st.plotly_chart(fig, width="stretch")

    st.subheader("Results record")
    st.dataframe(get_results_record(filtered_df).sort_values("wins", ascending=False), width="stretch", hide_index=True)

    with st.expander("How meetings were classified"):
        st.caption(
            "Classification is a keyword match on the meeting name (see CHAMPIONSHIP_PATTERN / "
            "LEAGUE_PATTERN in analytics.py). Adjust the patterns if something is miscategorised."
        )
        meets = (
            filtered_df.groupby("meeting").size().reset_index(name="marks")
            .assign(type=lambda d: d["meeting"].apply(classify_meeting))
            .sort_values(["type", "marks"], ascending=[True, False])
        )
        st.dataframe(meets, width="stretch", hide_index=True)


def render_wind(df):
    st.header("💨 Wind")
    st.markdown(
        f"Sprints and horizontal jumps only count for records when the tailwind is at most "
        f"+{LEGAL_WIND_LIMIT:.1f} m/s. This page shows every mark regardless of wind, so you can see "
        "which PBs are wind-assisted and how much the wind is flattering a season."
    )
    athletes_list, events_list, years_list, indoor_list, _ = get_page_filters(df, "Wind")
    filtered_df = apply_filters(df, athletes_list, events_list, years_list, indoor_list, wind="All marks")
    wind_df = filtered_df[filtered_df["wind_numeric"].notna()]
    if wind_df.empty:
        st.info("No wind readings in the selection (Po10 only records wind for sprints and horizontal jumps).")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Marks with wind reading", len(wind_df))
    c2.metric("Wind-assisted (> +2.0)", int(wind_df["wind_assisted"].sum()))
    pbs = get_legal_vs_all_pbs(filtered_df)
    c3.metric("PBs that are windy", int(pbs["pb_is_windy"].sum()) if not pbs.empty else 0)

    st.subheader("Legal PB vs all-conditions PB")
    st.dataframe(pbs, width="stretch", hide_index=True)

    events = sorted(wind_df["event"].unique().tolist())
    event_choice = st.selectbox("Wind vs performance for event", events, key="wind_event_choice")
    subset = wind_df[wind_df["event"] == event_choice]
    fig = px.scatter(
        subset,
        x="wind_numeric",
        y="perf_numeric",
        color="athlete_name",
        symbol="wind_assisted",
        hover_data=["performance", "date", "meeting", "wind"],
        template="plotly_dark",
        title=f"{event_choice}: performance against wind",
        labels={"wind_numeric": "Wind (m/s, + is tailwind)", "athlete_name": "Athlete", "wind_assisted": "Over limit"},
    )
    fig.add_vline(x=LEGAL_WIND_LIMIT, line_dash="dash", line_color="#DD6BCD", annotation_text="legal limit")
    _set_perf_axis(fig, bool(subset["is_track"].iloc[0]))
    fig.update_layout(margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig, width="stretch")


def render_competition_load(df):
    st.header("📆 Competition Load")
    st.markdown(
        "How often each athlete competes, how tightly the outings are packed, and whether short "
        "gaps between competitions cost performance."
    )
    athletes_list, events_list, years_list, indoor_list, wind_list = get_page_filters(df, "Competition Load")
    filtered_df = apply_filters(df, athletes_list, events_list, years_list, indoor_list, wind_list)
    if filtered_df.empty:
        st.info("No performances in the selection.")
        return

    load = get_competition_load(filtered_df)
    st.dataframe(load.sort_values(["athlete_name", "year"]), width="stretch", hide_index=True)

    fig = px.bar(
        load.assign(season=load["year"].astype(str)),
        x="athlete_name",
        y="competition_days",
        color="season",
        barmode="group",
        template="plotly_dark",
        title="Competition days per season",
        labels={"competition_days": "Competition days", "athlete_name": "Athlete", "season": "Season"},
    )
    fig.update_layout(margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig, width="stretch")

    st.subheader("Does a short gap hurt?")
    events = sorted(filtered_df["event"].unique().tolist())
    event_choice = st.selectbox("Event", events, key="load_event_choice")
    gap_df = add_days_since_previous(add_relative_to_best(filtered_df))
    subset = gap_df[(gap_df["event"] == event_choice) & gap_df["days_since_prev"].notna()]
    if subset.empty:
        st.info("Not enough consecutive competitions to show gaps.")
        return
    fig2 = px.scatter(
        subset,
        x="days_since_prev",
        y="pct_of_sb",
        color="athlete_name",
        hover_data=["performance", "date", "meeting"],
        template="plotly_dark",
        title=f"{event_choice}: mark (% of season's best) against days since previous competition",
        labels={"days_since_prev": "Days since previous competition (any event)", "pct_of_sb": "% of season's best", "athlete_name": "Athlete"},
    )
    fig2.update_layout(margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig2, width="stretch")


def render_age_curve(df):
    st.header("📐 Squad Age Curve")
    st.markdown(
        "A quadratic fit of performance against age across everyone in the group for one event. "
        "Shows roughly where peak age sits and which athletes are ahead of or behind the group's "
        "curve for their age. It is the squad's own curve, not a national one, so treat it as a "
        "comparison between training partners."
    )
    athletes_list, events_list, years_list, indoor_list, wind_list = get_page_filters(df, "Age Curve")
    filtered_df = apply_filters(df, athletes_list, events_list, years_list, indoor_list, wind_list)
    age_df = get_performance_vs_age(filtered_df)
    if age_df.empty:
        st.info("No age data in the selection.")
        return

    events = sorted(age_df["event"].unique().tolist())
    event_choice = st.selectbox("Event", events, key="age_curve_event_choice")
    subset = age_df[age_df["event"] == event_choice]
    fit = fit_age_curve(subset)
    if fit is None:
        st.info("Not enough marks across different ages to fit a curve for this event (need 8+ marks over 4+ distinct ages).")
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Marks", fit["n"])
    c2.metric("Athletes", fit["athletes"])
    c3.metric("Age range", f"{fit['age_min']}-{fit['age_max']}")
    c4.metric("Estimated peak age", fit["peak_age"] if fit["peak_age"] is not None else "outside data")
    st.caption(f"R² of fit: {fit['r_squared']}. A peak age is only reported when the curve turns within (or just beyond) the ages observed.")

    is_track = bool(subset["is_track"].iloc[0])
    fig = px.scatter(
        subset,
        x="age_decimal",
        y="perf_numeric",
        color="athlete_name",
        hover_data={"performance": True, "date": True, "age_decimal": ":.1f", "athlete_name": False},
        template="plotly_dark",
        title=f"{event_choice}: squad age curve",
        labels={"age_decimal": "Age at performance (years)", "athlete_name": "Athlete"},
    )
    fig.add_scatter(x=fit["curve_x"], y=fit["curve_y"], mode="lines", name="Squad curve",
                    line=dict(color="#FDDA0D", width=3))
    if fit["peak_age"] is not None:
        fig.add_vline(x=fit["peak_age"], line_dash="dash", line_color="#A1B4C4", annotation_text=f"peak ~{fit['peak_age']}")
    _set_perf_axis(fig, is_track)
    fig.update_layout(margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig, width="stretch")

    st.subheader("Athletes against the curve")
    st.caption("Positive % = better than the squad curve predicts for that age; 'latest' is their most recent mark.")
    st.dataframe(get_age_curve_residuals(subset, fit), width="stretch", hide_index=True)


def render_projection(df):
    st.header("🔮 Projection")
    st.warning(
        "Naive by design: a straight line through recent seasonal bests, extended one year. "
        "It knows nothing about injuries, age, training changes or regression to the mean. "
        "Use it as a conversation starter, not a target.",
        icon="⚠️",
    )
    athletes_list, events_list, _, indoor_list, wind_list = get_page_filters(df, "Projection", include_years=False)
    filtered_df = apply_filters(df, athletes_list, events_list, [], indoor_list, wind_list)
    if filtered_df.empty:
        st.info("No performances in the selection.")
        return

    recent = st.slider("Seasons to fit on", 3, 8, 4)
    sb_df = get_season_bests(filtered_df)
    proj = project_next_season(sb_df, recent_seasons=recent)
    if proj.empty:
        st.info(f"Need at least 3 seasons of marks for an athlete/event to project.")
        return

    show = proj.assign(
        projected=[format_numeric_perf(v, t) for v, t in zip(proj["projected_numeric"], proj["is_track"])],
        band=[f"{format_numeric_perf(lo, t)} - {format_numeric_perf(hi, t)}" for lo, hi, t in zip(proj["band_low"], proj["band_high"], proj["is_track"])],
    )[["athlete_name", "event", "seasons_used", "from_year", "to_year", "latest_sb", "slope_per_year", "projected_year", "projected", "band", "would_be_pb"]]
    st.dataframe(show, width="stretch", hide_index=True)

    events = sorted(proj["event"].unique().tolist())
    event_choice = st.selectbox("Chart for event", events, key="projection_event_choice")
    hist = sb_df[sb_df["event"] == event_choice].assign(kind="Seasonal best")
    p = proj[proj["event"] == event_choice]
    is_track = bool(p["is_track"].iloc[0])

    fig = px.line(
        hist.sort_values("year"),
        x="year", y="perf_numeric", color="athlete_name", markers=True,
        hover_data=["performance"], template="plotly_dark",
        title=f"{event_choice}: seasonal bests with next-season projection",
        labels={"athlete_name": "Athlete", "year": "Season"},
    )
    for _, row in p.iterrows():
        fig.add_scatter(
            x=[row["projected_year"]], y=[row["projected_numeric"]], mode="markers",
            marker=dict(symbol="diamond-open", size=14, line=dict(width=2)),
            error_y=dict(type="data", symmetric=False,
                         array=[row["band_high"] - row["projected_numeric"]],
                         arrayminus=[row["projected_numeric"] - row["band_low"]]),
            name=f"{row['athlete_name']} (projected)",
            hovertext=f"{format_numeric_perf(row['projected_numeric'], is_track)}",
        )
    _set_perf_axis(fig, is_track)
    fig.update_xaxes(tickmode="linear", dtick=1)
    fig.update_layout(margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig, width="stretch")


def render_event_suitability(df):
    st.header("🧭 Event Suitability")
    st.markdown(
        "Ratios between an athlete's PBs in paired events (200/100, 800/400, 110H/100 ...) "
        "compared with the range seen in well-trained athletes. A ratio outside the band hints "
        "at where the athlete's strengths lie and which event may suit them better."
    )
    athletes_list, events_list, _, indoor_list, wind_list = get_page_filters(df, "Event Suitability", include_years=False)
    filtered_df = apply_filters(df, athletes_list, events_list, [], indoor_list, wind_list)
    ratios = get_event_ratios(filtered_df)
    if ratios.empty:
        st.info("No athlete has PBs in both events of any benchmark pair in the selection.")
    else:
        st.dataframe(ratios, width="stretch", hide_index=True)
        fig = px.scatter(
            ratios, x="ratio", y="pair", color="athlete_name", symbol="verdict",
            hover_data=["pb_longer", "pb_shorter", "reading"], template="plotly_dark",
            title="Ratios by pair (bands shown in table)", labels={"athlete_name": "Athlete"},
        )
        fig.update_layout(margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig, width="stretch")

    with st.expander("Benchmark bands (indicative, editable in analytics.py)"):
        bench = pd.DataFrame(
            EVENT_RATIO_BENCHMARKS,
            columns=["longer / harder", "shorter / easier", "typical low", "typical high", "below band means", "above band means"],
        )
        st.dataframe(bench, width="stretch", hide_index=True)


def render_standards(df):
    st.header("🇬🇧 Standards")
    st.markdown(
        "Where each athlete's best for an age group sits against published standards. "
        "The bundled `standards.csv` holds the 2026 English Schools (National / Entry / County / "
        "District / School) and England Athletics championship entry standards; upload your own "
        "CSV to use something else. The comparison uses the best mark the athlete set *while in "
        "that age group*, so U17 marks are judged against U17 standards even if the athlete is "
        "now a senior."
    )
    with st.expander("CSV format"):
        st.code(
            "event,sex,age_group,level,standard,source\n"
            "100,F,U17,ESAA entry,12.6,English Schools 2026\n"
            "100,F,U17,ESAA national,12.2,English Schools 2026\n"
            "800,M,U20,EA U20 champs,1:55.0,England Athletics 2026\n"
            "LJ,F,U15,ESAA entry,5.00,English Schools 2026",
            language="text",
        )
        st.caption(
            "sex is M, F or blank for both. age_group must match Po10's labels (U13, U15, U17, U20, U23, SEN, V35 ...); "
            "list several with | (e.g. U17|U16) when one standard should apply to both the old and new age-group labels. "
            "Times as ss.cc or m:ss.cc, distances in metres, combined events as points. Several levels per event/group are fine."
        )

    upload = st.file_uploader("Upload a standards CSV", type=["csv"], key="standards_upload")
    standards = None
    source_note = ""
    try:
        if upload is not None:
            standards = load_standards(upload)
            source_note = f"Using uploaded file ({len(standards)} standards)."
        elif os.path.exists(STANDARDS_FILE):
            standards = load_standards(STANDARDS_FILE)
            source_note = f"Using {STANDARDS_FILE} from the repo ({len(standards)} standards)."
    except Exception as exc:
        st.error(f"Could not read the standards file: {exc}")
        return
    if standards is None or standards.empty:
        st.info("No standards loaded yet.")
        return
    st.caption(source_note)
    if "gender" in df.columns and (df["gender"].astype(str).str.strip() == "").all():
        st.caption("Po10 profiles didn't expose a gender, so sex-specific standards are matched to everyone - add a blank-sex row or check the scrape.")

    athletes_list, events_list, _, indoor_list, wind_list = get_page_filters(df, "Standards", include_years=False)
    filtered_df = apply_filters(df, athletes_list, events_list, [], indoor_list, wind_list)
    cmp = compare_to_standards(filtered_df, standards)
    if cmp.empty:
        st.info("None of the loaded standards match an athlete/event/age-group in the selection. Check the event codes and age-group labels in the CSV.")
        return
    c1, c2 = st.columns(2)
    c1.metric("Athlete/event/age-group rows", len(cmp))
    c2.metric("Rows with at least one standard met", int((cmp["standards_met"] != "-").sum()))
    st.dataframe(cmp, width="stretch", hide_index=True)


# =========================================================
# PAGE DISPATCH
# =========================================================

RENDERERS = {
    "Summary": render_summary,
    "PB Timeline": render_pb_timeline,
    "Performance Trends": render_performance_trends,
    "Season Shape": render_season_shape,
    "Consistency": render_consistency,
    "Championships": render_championships,
    "Wind": render_wind,
    "Competition Load": render_competition_load,
    "Event Summary": render_event_summary,
    "Distribution": render_distribution,
    "Top Athletes by Year": render_top_athletes_by_year,
    "Top Ranked": render_top_ranked,
    "Relative Improvement": render_relative_improvement,
    "YOY": render_yoy_changes,
    "Trend Momentum": render_trend_momentum,
    "Performance vs Age": render_performance_vs_age,
    "Age Curve": render_age_curve,
    "Projection": render_projection,
    "Event Suitability": render_event_suitability,
    "Standards": render_standards,
}

RENDERERS[selected_page](analytics_df)