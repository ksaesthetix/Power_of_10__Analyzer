# analytics.py

import re
import numpy as np
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

    analytics_df = add_age_at_performance(analytics_df)

    return analytics_df


# =========================================================
# AGE AT PERFORMANCE
# =========================================================

DAYS_PER_YEAR = 365.25


def add_age_at_performance(df: pd.DataFrame) -> pd.DataFrame:
    """Add ``age`` (whole years), ``age_decimal`` and ``age_source`` columns.

    Two sources, in order of preference:

    * ``dob`` — a full date of birth, which Po10 only publishes for some
      athletes. Gives the exact age.  ``age_source == "dob"``.
    * ``age_now`` + ``scraped_on`` — the "(N YRS)" shown on every profile,
      read on the scrape date. Someone who is N today was born in the year
      ending N years ago, so we take the midpoint of that window as the DOB;
      ages derived from it are accurate to within six months.
      ``age_source == "estimated"``.

    Rows with neither get NaN ages and ``age_source`` of None.
    """
    df = df.copy()
    n = len(df)

    # performance date; fall back to mid-season when only the year is known
    df["perf_date_parsed"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")
    missing = df["perf_date_parsed"].isna()
    if missing.any():
        df.loc[missing, "perf_date_parsed"] = pd.to_datetime(
            df.loc[missing, "year"].astype(int).astype(str) + "-07-01"
        )

    # exact DOB, when published (e.g. '18 November 2000')
    if "dob" in df.columns:
        dob_parsed = pd.to_datetime(df["dob"], dayfirst=True, errors="coerce")
    else:
        dob_parsed = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")

    # estimated DOB from current age on the day of the scrape
    if {"age_now", "scraped_on"}.issubset(df.columns):
        scraped = pd.to_datetime(df["scraped_on"], errors="coerce")
        age_now = pd.to_numeric(df["age_now"], errors="coerce")
        dob_estimated = scraped - pd.to_timedelta((age_now + 0.5) * DAYS_PER_YEAR, unit="D")
    else:
        dob_estimated = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")

    df["dob_parsed"] = dob_parsed
    df["dob_estimated"] = dob_estimated

    effective_dob = dob_parsed.fillna(dob_estimated)
    df["age_source"] = np.select(
        [dob_parsed.notna(), dob_estimated.notna()],
        ["dob", "estimated"],
        default=None,
    ) if n else pd.Series(dtype="object")

    days_old = (df["perf_date_parsed"] - effective_dob).dt.days
    df["age_decimal"] = (days_old / DAYS_PER_YEAR).round(2)
    df["age"] = np.floor(df["age_decimal"]).astype("Int64")

    return df


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

def get_performance_vs_age(df: pd.DataFrame) -> pd.DataFrame:
    """Rows with a real age at performance (from DOB or the estimated DOB).

    Age-group labels are deliberately NOT used as a fallback: "U20" says only
    that the athlete was 17-19, so plotting it as 20 would be misleading.
    """
    if not {"age_decimal", "perf_numeric"}.issubset(df.columns):
        return df.iloc[0:0].copy()
    return df[df["age_decimal"].notna() & df["perf_numeric"].notna()].copy()


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