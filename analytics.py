# analytics.py

import re
import pandas as pd
from datetime import datetime
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

    # parse DOB if available and compute age at performance
    if "dob" in analytics_df.columns:
        # try to parse DOB - many pages use formats like '18 November 2000'
        analytics_df["dob_parsed"] = pd.to_datetime(
            analytics_df["dob"], dayfirst=True, errors="coerce"
        )

        # parse performance date where available
        analytics_df["perf_date_parsed"] = pd.to_datetime(
            analytics_df["date"], dayfirst=True, errors="coerce"
        )

        # fallback: where perf_date_parsed is NaT, set to Jan 1 of the performance year
        missing_perf_dates = analytics_df["perf_date_parsed"].isna()
        if missing_perf_dates.any():
            analytics_df.loc[missing_perf_dates, "perf_date_parsed"] = pd.to_datetime(
                analytics_df.loc[missing_perf_dates, "year"].astype(str) + "-01-01"
            )

        # compute age in years (floor)
        def compute_age(row):
            dob = row.get("dob_parsed")
            perf = row.get("perf_date_parsed")
            if pd.isna(dob) or pd.isna(perf):
                return None
            # compute full years difference, adjusting for month/day
            years = perf.year - dob.year
            if (perf.month, perf.day) < (dob.month, dob.day):
                years -= 1
            return int(years)

        analytics_df["age"] = analytics_df.apply(compute_age, axis=1)

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
# EVENT SUMMARY STATS
# =========================================================

def get_event_summary_stats(df: pd.DataFrame) -> pd.DataFrame:

    return (
        df[df["perf_numeric"].notna()]
        .groupby("event")["perf_numeric"]
        .agg(
            event_count="count",
            mean_perf="mean",
            median_perf="median",
            min_perf="min",
            max_perf="max",
            std_perf="std",
        )
        .reset_index()
    )


# =========================================================
# TOP ATHLETES BY YEAR
# =========================================================

def get_top_athletes_by_year(
    df: pd.DataFrame,
    year: int,
    top_n: int = 20,
) -> pd.DataFrame:

    year_df = df[df["year"] == year]
    if year_df.empty:
        return pd.DataFrame()

    rows = []
    for event, group in year_df.groupby("event"):
        is_track = group["is_track"].iloc[0]
        if is_track:
            best_idx = group["perf_numeric"].idxmin()
        else:
            best_idx = group["perf_numeric"].idxmax()
        rows.append(group.loc[best_idx])

    top_df = pd.DataFrame(rows)
    if top_df.empty:
        return top_df

    return top_df.sort_values(["event", "perf_numeric"], ascending=[True, True]).head(top_n)


# =========================================================
# PERFORMANCE DISTRIBUTION
# =========================================================

def get_performance_distribution(df: pd.DataFrame) -> pd.DataFrame:

    return df[df["perf_numeric"].notna()].copy()


# =========================================================
# PERFORMANCE VS AGE
# =========================================================

def _extract_age(age_group: str):
    if not age_group:
        return None
    match = re.search(r"(\d{1,2})", str(age_group))
    if match:
        return int(match.group(1))
    return None


def get_performance_vs_age(df: pd.DataFrame) -> pd.DataFrame:

    df = df.copy()
    # prefer computed age (from DOB) when available; otherwise fall back to age_group
    if "age" not in df.columns or df["age"].isna().all():
        df["age"] = df["age_group"].apply(_extract_age)

    return df[df["age"].notna() & df["perf_numeric"].notna()].copy()


# =========================================================
# TREND SLOPE / MOMENTUM
# =========================================================

def _compute_trend_slope(years: pd.Series, values: pd.Series):
    if len(years) < 2:
        return None
    cov = years.cov(values)
    var = years.var()
    if var == 0 or pd.isna(cov):
        return None
    return cov / var


def get_trend_slopes(df: pd.DataFrame) -> pd.DataFrame:

    rows = []
    for (athlete, event), group in df.groupby(["athlete_name", "event"]):
        valid = group.dropna(subset=["year", "perf_numeric"]).sort_values("year")
        if len(valid) < 2:
            continue
        slope = _compute_trend_slope(valid["year"], valid["perf_numeric"])
        if slope is None:
            continue
        is_track = valid["is_track"].iloc[0]
        momentum = -slope if is_track else slope
        rows.append({
            "athlete_name": athlete,
            "event": event,
            "data_points": len(valid),
            "slope": slope,
            "momentum": momentum,
            "improvement_direction": "improving" if momentum > 0 else "declining",
        })

    return pd.DataFrame(rows)


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