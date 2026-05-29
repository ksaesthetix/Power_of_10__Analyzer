# analytics.py

import pandas as pd
from po10_scraper import infer_event_kind, parse_perf_numeric


# =========================================================
# PREPARE ANALYTICS DATAFRAME
# =========================================================

def prepare_analytics_df(df: pd.DataFrame) -> pd.DataFrame:

    analytics_df = df.copy()

    analytics_df["event_kind"] = analytics_df["event"].apply(
        infer_event_kind
    )

    analytics_df["perf_numeric"] = analytics_df.apply(
        lambda row: parse_perf_numeric(
            row["performance"],
            row["event_kind"]
        ),
        axis=1
    )

    analytics_df = analytics_df.dropna(
        subset=["perf_numeric"]
    )

    analytics_df["is_track"] = (
        analytics_df["event_kind"] == "time"
    )

    analytics_df["year"] = pd.to_numeric(
        analytics_df["year"],
        errors="coerce"
    )

    analytics_df = analytics_df.dropna(subset=["year"])

    analytics_df["year"] = analytics_df["year"].astype(int)

    return analytics_df


# =========================================================
# PERSONAL BESTS
# =========================================================

def get_personal_bests(df: pd.DataFrame) -> pd.DataFrame:

    pb_rows = []

    for (athlete, event), group in df.groupby(
        ["athlete_name", "event"]
    ):

        is_track = group["is_track"].iloc[0]

        if is_track:
            best_idx = group["perf_numeric"].idxmin()
        else:
            best_idx = group["perf_numeric"].idxmax()

        pb_rows.append(group.loc[best_idx])

    return pd.DataFrame(pb_rows)


# =========================================================
# SEASONAL BESTS
# =========================================================

def get_season_bests(df: pd.DataFrame) -> pd.DataFrame:

    sb_rows = []

    for (athlete, event, year), group in df.groupby(
        ["athlete_name", "event", "year"]
    ):

        is_track = group["is_track"].iloc[0]

        if is_track:
            best_idx = group["perf_numeric"].idxmin()
        else:
            best_idx = group["perf_numeric"].idxmax()

        sb_rows.append(group.loc[best_idx])

    return pd.DataFrame(sb_rows)


# =========================================================
# AVERAGE PERFORMANCE
# =========================================================

def get_average_performance(df: pd.DataFrame) -> pd.DataFrame:

    return (
        df.groupby(
            ["athlete_name", "event"]
        )["perf_numeric"]
        .mean()
        .reset_index(name="average_perf")
    )


# =========================================================
# PERFORMANCE VOLATILITY
# =========================================================

def get_performance_volatility(df: pd.DataFrame) -> pd.DataFrame:

    return (
        df.groupby(
            ["athlete_name", "event"]
        )["perf_numeric"]
        .std()
        .reset_index(name="volatility")
    )


# =========================================================
# RELATIVE IMPROVEMENT
# =========================================================

def get_relative_improvement(df: pd.DataFrame) -> pd.DataFrame:

    rows = []

    for (athlete, event), group in df.groupby(
        ["athlete_name", "event"]
    ):

        group = group.sort_values("year")

        first = group.iloc[0]["perf_numeric"]

        is_track = group["is_track"].iloc[0]

        if is_track:
            best = group["perf_numeric"].min()
            improvement_pct = (
                (first - best) / first
            ) * 100
        else:
            best = group["perf_numeric"].max()
            improvement_pct = (
                (best - first) / first
            ) * 100

        rows.append({
            "athlete_name": athlete,
            "event": event,
            "first_perf": first,
            "best_perf": best,
            "improvement_pct": round(
                improvement_pct,
                2
            )
        })

    return pd.DataFrame(rows)


# =========================================================
# YEAR OVER YEAR CHANGES
# =========================================================

def get_yoy_changes(sb_df: pd.DataFrame) -> pd.DataFrame:

    yoy_rows = []

    for (athlete, event), group in sb_df.groupby(
        ["athlete_name", "event"]
    ):

        group = group.sort_values("year")

        group["prev"] = (
            group["perf_numeric"]
            .shift(1)
        )

        is_track = group["is_track"].iloc[0]

        if is_track:
            group["change"] = (
                group["prev"]
                - group["perf_numeric"]
            )
        else:
            group["change"] = (
                group["perf_numeric"]
                - group["prev"]
            )

        yoy_rows.append(group)

    return pd.concat(yoy_rows)


# =========================================================
# TOP RANKED PERFORMANCES
# =========================================================

def get_top_ranked_performances(
    df: pd.DataFrame,
    top_n: int = 10
) -> pd.DataFrame:

    ranked_rows = []

    for event, group in df.groupby("event"):

        is_track = group["is_track"].iloc[0]

        if is_track:
            ranked = group.sort_values(
                "perf_numeric"
            )
        else:
            ranked = group.sort_values(
                "perf_numeric",
                ascending=False
            )

        ranked_rows.append(ranked.head(top_n))

    return pd.concat(ranked_rows)


# =========================================================
# ROLLING AVERAGES
# =========================================================

def add_rolling_average(
    df: pd.DataFrame,
    window: int = 3
) -> pd.DataFrame:

    rolling_df = df.copy()

    rolling_df = rolling_df.sort_values(
        ["athlete_name", "year"]
    )

    rolling_df["rolling_avg"] = (
        rolling_df.groupby(
            ["athlete_name", "event"]
        )["perf_numeric"]
        .transform(
            lambda x: x.rolling(
                window,
                min_periods=1
            ).mean()
        )
    )

    return rolling_df