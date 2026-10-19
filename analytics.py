# analytics.py

import re
from typing import Optional

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
    analytics_df = add_wind_flags(analytics_df)
    analytics_df = add_season_fields(analytics_df)
    analytics_df["event_code"] = analytics_df["event"].apply(normalise_event_code)

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

    return pd.concat(yoy_rows) if yoy_rows else sb_df.iloc[0:0].copy()


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

    return pd.concat(ranked_rows) if ranked_rows else df.iloc[0:0].copy()


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

# =========================================================
# EVENT CODE NORMALISATION
# =========================================================

_EVENT_ALIASES = {
    "LONGJUMP": "LJ", "TRIPLEJUMP": "TJ", "HIGHJUMP": "HJ", "POLEVAULT": "PV",
    "SHOTPUT": "SP", "SHOT": "SP", "DISCUS": "DT", "HAMMER": "HT", "JAVELIN": "JT",
    "MILE": "MILE", "1M": "MILE", "HALFMARATHON": "HM", "MARATHON": "MAR",
}


def normalise_event_code(event: str) -> str:
    """Collapse Po10 event names to a short comparable code.

    '100m' -> '100', '100HW' -> '100H', '110HU20M' -> '110H', 'SP4K' -> 'SP',
    'Long Jump' -> 'LJ'. Implement weights and sex/age suffixes are dropped so
    that an athlete's marks across age groups line up as one event.
    """
    code = re.sub(r"\\s+", "", str(event or "")).upper()
    if not code:
        return ""
    if code in _EVENT_ALIASES:
        return _EVENT_ALIASES[code]
    m = re.match(r"^(\\d+)M$", code)
    if m:
        return m.group(1)
    m = re.match(r"^(\\d+)(H|SC|W)(U\\d+)?[WM]?$", code)
    if m:
        return m.group(1) + m.group(2)
    m = re.match(r"^(LJ|TJ|HJ|PV)(U\\d+)?[WM]?$", code)
    if m:
        return m.group(1)
    m = re.match(r"^(SP|DT|HT|JT|WT|BT)(\\d+(\\.\\d+)?K?)?(U\\d+)?[WM]?$", code)
    if m:
        return m.group(1)
    return code


# =========================================================
# WIND
# =========================================================

LEGAL_WIND_LIMIT = 2.0


def add_wind_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Add ``wind_numeric`` and ``wind_assisted`` (> +2.0 m/s).

    Rows with no wind reading are treated as legal - Po10 only records wind
    for sprints and horizontal jumps, so a blank means "not a wind event" or
    "not measured", neither of which should exclude a mark.
    """
    df = df.copy()
    wind = df["wind"].astype("string") if "wind" in df.columns else pd.Series("", index=df.index, dtype="string")
    cleaned = wind.fillna("").str.replace(r"[^0-9.+\\-]", "", regex=True).replace("", pd.NA)
    df["wind_numeric"] = pd.to_numeric(cleaned, errors="coerce")
    df["wind_assisted"] = (df["wind_numeric"] > LEGAL_WIND_LIMIT).fillna(False).astype(bool)
    return df


def get_legal_vs_all_pbs(df: pd.DataFrame) -> pd.DataFrame:
    """For wind-measured events: legal PB alongside all-conditions PB."""
    wind_events = df.loc[df["wind_numeric"].notna(), "event"].unique()
    sub = df[df["event"].isin(wind_events)]
    rows = []
    for (athlete, event), g in sub.groupby(["athlete_name", "event"]):
        is_track = bool(g["is_track"].iloc[0])
        best_all = g["perf_numeric"].idxmin() if is_track else g["perf_numeric"].idxmax()
        legal = g[~g["wind_assisted"]]
        if legal.empty:
            best_legal = None
        else:
            best_legal = legal["perf_numeric"].idxmin() if is_track else legal["perf_numeric"].idxmax()
        rows.append({
            "athlete_name": athlete,
            "event": event,
            "legal_pb": g.loc[best_legal, "performance"] if best_legal is not None else None,
            "legal_pb_date": g.loc[best_legal, "date"] if best_legal is not None else None,
            "all_conditions_pb": g.loc[best_all, "performance"],
            "all_conditions_wind": g.loc[best_all, "wind"],
            "all_conditions_date": g.loc[best_all, "date"],
            "windy_marks": int(g["wind_assisted"].sum()),
            "marks": int(len(g)),
            "pb_is_windy": bool(g.loc[best_all, "wind_assisted"]),
        })
    return pd.DataFrame(rows)


# =========================================================
# SEASON FIELDS
# =========================================================

def add_season_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Add ``day_of_year`` / ``month`` from the parsed performance date."""
    df = df.copy()
    df["day_of_year"] = df["perf_date_parsed"].dt.dayofyear
    df["month"] = df["perf_date_parsed"].dt.month
    return df


# =========================================================
# % OF PB / SB, CONSISTENCY
# =========================================================

def add_relative_to_best(df: pd.DataFrame) -> pd.DataFrame:
    """Add ``pb_numeric``, ``sb_numeric``, ``pct_of_pb``, ``pct_of_sb``.

    100 means "equal to best"; lower is further off. Bests are taken within
    the frame given, so apply filters first if you want e.g. legal-only PBs.
    """
    df = df.copy()
    if df.empty:
        for c in ("pb_numeric", "sb_numeric", "pct_of_pb", "pct_of_sb"):
            df[c] = pd.Series(dtype="float")
        return df
    track = df["is_track"].astype(bool)
    g_pb = df.groupby(["athlete_name", "event"])["perf_numeric"]
    g_sb = df.groupby(["athlete_name", "event", "year"])["perf_numeric"]
    df["pb_numeric"] = np.where(track, g_pb.transform("min"), g_pb.transform("max"))
    df["sb_numeric"] = np.where(track, g_sb.transform("min"), g_sb.transform("max"))
    with np.errstate(divide="ignore", invalid="ignore"):
        df["pct_of_pb"] = np.where(track, df["pb_numeric"] / df["perf_numeric"], df["perf_numeric"] / df["pb_numeric"]) * 100
        df["pct_of_sb"] = np.where(track, df["sb_numeric"] / df["perf_numeric"], df["perf_numeric"] / df["sb_numeric"]) * 100
    df["pct_of_pb"] = df["pct_of_pb"].round(2)
    df["pct_of_sb"] = df["pct_of_sb"].round(2)
    return df


def get_consistency(df: pd.DataFrame, within_pct: float = 2.0) -> pd.DataFrame:
    """Per athlete/event consistency expressed relative to their own best."""
    rel = add_relative_to_best(df)
    rows = []
    for (athlete, event), g in rel.groupby(["athlete_name", "event"]):
        n = len(g)
        rows.append({
            "athlete_name": athlete,
            "event": event,
            "marks": n,
            "mean_pct_of_pb": round(g["pct_of_pb"].mean(), 2),
            "median_pct_of_pb": round(g["pct_of_pb"].median(), 2),
            "std_pct_of_pb": round(g["pct_of_pb"].std(ddof=0), 2) if n > 1 else 0.0,
            f"hit_rate_within_{within_pct:g}pct": round((g["pct_of_pb"] >= 100 - within_pct).mean() * 100, 1),
            "cv_pct": round(g["perf_numeric"].std(ddof=0) / g["perf_numeric"].mean() * 100, 2) if n > 1 else 0.0,
            "worst_pct_of_pb": round(g["pct_of_pb"].min(), 2),
        })
    return pd.DataFrame(rows)


# =========================================================
# PB TIMELINE / STALENESS
# =========================================================

def get_pb_timeline(df: pd.DataFrame, as_of: Optional[pd.Timestamp] = None) -> pd.DataFrame:
    """Career PB per athlete/event with staleness and how this season compares."""
    as_of = pd.Timestamp(as_of) if as_of is not None else pd.Timestamp.today().normalize()
    rel = add_relative_to_best(df)
    rows = []
    for (athlete, event), g in rel.groupby(["athlete_name", "event"]):
        is_track = bool(g["is_track"].iloc[0])
        pb_idx = g["perf_numeric"].idxmin() if is_track else g["perf_numeric"].idxmax()
        pb = g.loc[pb_idx]
        latest_year = int(g["year"].max())
        latest = g[g["year"] == latest_year]
        sb_idx = latest["perf_numeric"].idxmin() if is_track else latest["perf_numeric"].idxmax()
        sb = latest.loc[sb_idx]
        sb_pct = float(sb["pct_of_pb"])
        days_since = (as_of - pb["perf_date_parsed"]).days if pd.notna(pb["perf_date_parsed"]) else None
        if int(pb["year"]) == latest_year:
            status = "PB this season"
        elif sb_pct >= 99:
            status = "Within 1%"
        elif sb_pct >= 97:
            status = "Within 3%"
        else:
            status = "Off by >3%"
        rows.append({
            "athlete_name": athlete,
            "event": event,
            "pb": pb["performance"],
            "pb_date": pb["date"],
            "pb_year": int(pb["year"]),
            "pb_meeting": pb["meeting"],
            "days_since_pb": days_since,
            "latest_season": latest_year,
            "latest_sb": sb["performance"],
            "latest_sb_pct_of_pb": round(sb_pct, 2),
            "status": status,
            "marks": int(len(g)),
        })
    out = pd.DataFrame(rows)
    return out.sort_values("days_since_pb", ascending=False) if not out.empty else out


def get_pb_progression(df: pd.DataFrame) -> pd.DataFrame:
    """Every performance that was a PB at the time it was set (chronological)."""
    rows = []
    for (athlete, event), g in df.groupby(["athlete_name", "event"]):
        g = g.sort_values("perf_date_parsed")
        is_track = bool(g["is_track"].iloc[0])
        best = None
        for idx, row in g.iterrows():
            v = row["perf_numeric"]
            if best is None or (v < best if is_track else v > best):
                best = v
                rows.append(row)
    return pd.DataFrame(rows)


# =========================================================
# IN-SEASON SHAPE
# =========================================================

def get_season_shape(df: pd.DataFrame) -> pd.DataFrame:
    """Per athlete/event/season: where in the season the best mark fell."""
    rel = add_relative_to_best(df)
    rows = []
    for (athlete, event, year), g in rel.groupby(["athlete_name", "event", "year"]):
        g = g.sort_values("perf_date_parsed")
        is_track = bool(g["is_track"].iloc[0])
        sb_idx = g["perf_numeric"].idxmin() if is_track else g["perf_numeric"].idxmax()
        order = list(g.index)
        pos = order.index(sb_idx) + 1
        first, last = g["perf_date_parsed"].iloc[0], g["perf_date_parsed"].iloc[-1]
        rows.append({
            "athlete_name": athlete,
            "event": event,
            "year": int(year),
            "competitions": len(g),
            "season_start": first.strftime("%d %b") if pd.notna(first) else "",
            "season_end": last.strftime("%d %b") if pd.notna(last) else "",
            "sb": g.loc[sb_idx, "performance"],
            "sb_date": g.loc[sb_idx, "date"],
            "sb_race_number": pos,
            "sb_position_in_season": f"{pos} of {len(g)}",
            "first_mark_pct_of_sb": round(float(g["pct_of_sb"].iloc[0]), 2),
            "last_mark_pct_of_sb": round(float(g["pct_of_sb"].iloc[-1]), 2),
        })
    return pd.DataFrame(rows)


# =========================================================
# CHAMPIONSHIPS VS ORDINARY MEETS
# =========================================================

CHAMPIONSHIP_PATTERN = re.compile(
    r"champ|trials|english schools|bucs|inter.?count|national|final|games|aaa|uk school|"
    r"welsh schools|scottish schools|sias|esaa|indoor champs|area champs|regional champs",
    re.I,
)
LEAGUE_PATTERN = re.compile(r"league|open meet|open graded|graded|bmc|pb classic|relays", re.I)


def classify_meeting(meeting: str) -> str:
    name = str(meeting or "")
    if CHAMPIONSHIP_PATTERN.search(name) and not LEAGUE_PATTERN.search(name):
        return "Championship"
    return "Other"


def get_championship_comparison(df: pd.DataFrame) -> pd.DataFrame:
    """% of PB at championship meets vs everything else, plus medals/wins."""
    rel = add_relative_to_best(df)
    rel["meeting_type"] = rel["meeting"].apply(classify_meeting)
    pos = pd.to_numeric(rel["position"], errors="coerce")
    rel["is_win"] = pos == 1
    rel["is_podium"] = pos <= 3
    rows = []
    for (athlete, event), g in rel.groupby(["athlete_name", "event"]):
        champ = g[g["meeting_type"] == "Championship"]
        other = g[g["meeting_type"] == "Other"]
        if champ.empty:
            continue
        champ_mean = champ["pct_of_pb"].mean()
        other_mean = other["pct_of_pb"].mean() if not other.empty else np.nan
        rows.append({
            "athlete_name": athlete,
            "event": event,
            "championship_marks": len(champ),
            "championship_mean_pct_of_pb": round(champ_mean, 2),
            "other_marks": len(other),
            "other_mean_pct_of_pb": round(other_mean, 2) if pd.notna(other_mean) else None,
            "delta_pct_points": round(champ_mean - other_mean, 2) if pd.notna(other_mean) else None,
            "championship_wins": int(champ["is_win"].sum()),
            "championship_podiums": int(champ["is_podium"].sum()),
            "championship_best": champ.loc[champ["perf_numeric"].idxmin() if g["is_track"].iloc[0] else champ["perf_numeric"].idxmax(), "performance"],
        })
    out = pd.DataFrame(rows)
    return out.sort_values("delta_pct_points", ascending=False, na_position="last") if not out.empty else out


def get_results_record(df: pd.DataFrame) -> pd.DataFrame:
    """Wins / podiums / placed marks per athlete across all meets."""
    pos = pd.to_numeric(df["position"], errors="coerce")
    tmp = df.assign(_pos=pos, _type=df["meeting"].apply(classify_meeting))
    rows = []
    for athlete, g in tmp.groupby("athlete_name"):
        placed = g["_pos"].notna()
        rows.append({
            "athlete_name": athlete,
            "marks_with_position": int(placed.sum()),
            "wins": int((g["_pos"] == 1).sum()),
            "podiums": int((g["_pos"] <= 3).sum()),
            "win_rate_pct": round((g["_pos"] == 1).sum() / placed.sum() * 100, 1) if placed.any() else None,
            "championship_wins": int(((g["_pos"] == 1) & (g["_type"] == "Championship")).sum()),
            "championship_podiums": int(((g["_pos"] <= 3) & (g["_type"] == "Championship")).sum()),
        })
    return pd.DataFrame(rows)


# =========================================================
# COMPETITION LOAD
# =========================================================

def add_days_since_previous(df: pd.DataFrame) -> pd.DataFrame:
    """Per athlete, days since their previous competition day (any event)."""
    df = df.copy()
    comp_days = (
        df[["athlete_name", "perf_date_parsed"]]
        .dropna()
        .drop_duplicates()
        .sort_values(["athlete_name", "perf_date_parsed"])
    )
    comp_days["days_since_prev"] = comp_days.groupby("athlete_name")["perf_date_parsed"].diff().dt.days
    df = df.merge(comp_days, on=["athlete_name", "perf_date_parsed"], how="left")
    return df


def get_competition_load(df: pd.DataFrame) -> pd.DataFrame:
    """Per athlete/season: competition days, span and gaps between outings."""
    rows = []
    for (athlete, year), g in df.groupby(["athlete_name", "year"]):
        days = g["perf_date_parsed"].dropna().drop_duplicates().sort_values()
        if days.empty:
            continue
        gaps = days.diff().dt.days.dropna()
        rows.append({
            "athlete_name": athlete,
            "year": int(year),
            "competition_days": len(days),
            "marks": len(g),
            "events_contested": g["event"].nunique(),
            "first": days.iloc[0].strftime("%d %b"),
            "last": days.iloc[-1].strftime("%d %b"),
            "season_span_days": int((days.iloc[-1] - days.iloc[0]).days),
            "mean_gap_days": round(gaps.mean(), 1) if not gaps.empty else None,
            "min_gap_days": int(gaps.min()) if not gaps.empty else None,
            "max_gap_days": int(gaps.max()) if not gaps.empty else None,
        })
    return pd.DataFrame(rows)


# =========================================================
# SQUAD AGE-PERFORMANCE CURVE
# =========================================================

def fit_age_curve(df_event: pd.DataFrame, min_points: int = 8) -> Optional[dict]:
    """Quadratic fit of performance against age across everyone in ``df_event``.

    Returns None when there isn't enough spread to fit. ``peak_age`` is the
    vertex of the parabola when it points the right way (a minimum for timed
    events, a maximum for distance/points), otherwise None.
    """
    d = df_event.dropna(subset=["age_decimal", "perf_numeric"])
    if len(d) < min_points or d["age_decimal"].nunique() < 4:
        return None
    x = d["age_decimal"].to_numpy(dtype=float)
    y = d["perf_numeric"].to_numpy(dtype=float)
    a, b, c = np.polyfit(x, y, 2)
    is_track = bool(d["is_track"].iloc[0])
    peak = None
    if a != 0:
        vertex = -b / (2 * a)
        opens_right_way = (a > 0) if is_track else (a < 0)
        if opens_right_way and x.min() - 2 <= vertex <= x.max() + 2:
            peak = round(float(vertex), 1)
    grid = np.linspace(x.min(), x.max(), 60)
    pred = np.polyval([a, b, c], x)
    ss_res = float(((y - pred) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    return {
        "coeffs": (float(a), float(b), float(c)),
        "curve_x": grid,
        "curve_y": np.polyval([a, b, c], grid),
        "peak_age": peak,
        "n": int(len(d)),
        "athletes": int(d["athlete_name"].nunique()),
        "r_squared": round(1 - ss_res / ss_tot, 3) if ss_tot > 0 else None,
        "age_min": round(float(x.min()), 1),
        "age_max": round(float(x.max()), 1),
    }


def get_age_curve_residuals(df_event: pd.DataFrame, fit: dict) -> pd.DataFrame:
    """How far each athlete sits from the squad curve, as % (positive = better)."""
    d = df_event.dropna(subset=["age_decimal", "perf_numeric"]).copy()
    expected = np.polyval(fit["coeffs"], d["age_decimal"].to_numpy(dtype=float))
    is_track = bool(d["is_track"].iloc[0])
    with np.errstate(divide="ignore", invalid="ignore"):
        d["vs_curve_pct"] = np.where(is_track, (expected - d["perf_numeric"]) / expected, (d["perf_numeric"] - expected) / expected) * 100
    rows = []
    for athlete, g in d.groupby("athlete_name"):
        latest = g.sort_values("perf_date_parsed").iloc[-1]
        rows.append({
            "athlete_name": athlete,
            "marks": len(g),
            "age_range": f"{g['age_decimal'].min():.1f}-{g['age_decimal'].max():.1f}",
            "mean_vs_curve_pct": round(g["vs_curve_pct"].mean(), 2),
            "latest_vs_curve_pct": round(float(latest["vs_curve_pct"]), 2),
            "best_vs_curve_pct": round(g["vs_curve_pct"].max(), 2),
        })
    out = pd.DataFrame(rows)
    return out.sort_values("mean_vs_curve_pct", ascending=False) if not out.empty else out


# =========================================================
# PROJECTION (naive linear trend on seasonal bests)
# =========================================================

def project_next_season(sb_df: pd.DataFrame, recent_seasons: int = 4, min_seasons: int = 3) -> pd.DataFrame:
    """Linear fit on the last ``recent_seasons`` seasonal bests, extended one year.

    Deliberately naive: it assumes the recent rate of change continues. The
    band is +/- one residual standard deviation of the fit (or the
    season-to-season spread when there are too few points for residuals).
    """
    rows = []
    for (athlete, event), g in sb_df.groupby(["athlete_name", "event"]):
        g = g.dropna(subset=["year", "perf_numeric"]).sort_values("year").tail(recent_seasons)
        if len(g) < min_seasons or g["year"].nunique() < min_seasons:
            continue
        x = g["year"].to_numpy(dtype=float)
        y = g["perf_numeric"].to_numpy(dtype=float)
        slope, intercept = np.polyfit(x, y, 1)
        resid = y - (slope * x + intercept)
        band = float(resid.std(ddof=1)) if len(y) > 2 else float(np.abs(np.diff(y)).mean())
        next_year = int(x.max()) + 1
        projected = slope * next_year + intercept
        is_track = bool(g["is_track"].iloc[0])
        best_so_far = y.min() if is_track else y.max()
        rows.append({
            "athlete_name": athlete,
            "event": event,
            "seasons_used": len(g),
            "from_year": int(x.min()),
            "to_year": int(x.max()),
            "latest_sb_numeric": float(y[-1]),
            "latest_sb": g["performance"].iloc[-1],
            "slope_per_year": round(float(slope), 3),
            "projected_year": next_year,
            "projected_numeric": round(float(projected), 2),
            "band_low": round(float(projected - band), 2),
            "band_high": round(float(projected + band), 2),
            "would_be_pb": bool(projected < best_so_far) if is_track else bool(projected > best_so_far),
            "is_track": is_track,
        })
    return pd.DataFrame(rows)


def format_numeric_perf(value: float, is_track: bool) -> str:
    """Seconds -> 'm:ss.cc' above a minute; distances/points to 2 dp."""
    if value is None or pd.isna(value):
        return ""
    if not is_track:
        return f"{value:.2f}"
    if value >= 60:
        mins = int(value // 60)
        secs = value - mins * 60
        return f"{mins}:{secs:05.2f}"
    return f"{value:.2f}"


# =========================================================
# EVENT SUITABILITY (ratios between an athlete's events)
# =========================================================

# (longer_or_harder, shorter_or_easier, typical_low, typical_high, below_band_means, above_band_means)
# Bands are indicative ranges seen across well-trained athletes, not thresholds
# from any governing body - edit to taste.
EVENT_RATIO_BENCHMARKS = [
    ("200", "100", 2.00, 2.10, "strong speed-endurance; 200 is the better event", "pure speed; 200 falling off relative to 100"),
    ("400", "200", 2.15, 2.30, "strong lactic tolerance; 400 suits", "speed-leaning; 400 undertrained relative to 200"),
    ("800", "400", 2.18, 2.35, "endurance-leaning 800 runner", "speed-type; 800 could improve with aerobic work"),
    ("1500", "800", 2.05, 2.14, "aerobic strength; could move up", "speed-based miler; 1500 relies on 800 speed"),
    ("5000", "1500", 3.60, 3.90, "very aerobic; 5000+ suits", "1500-type; 5000 is a stretch"),
    ("100", "60", 1.54, 1.62, "excellent speed maintenance 60->100", "great start, fading over 100"),
    ("110H", "100", 1.28, 1.40, "efficient hurdler", "hurdling technique costing time vs flat speed"),
    ("100H", "100", 1.14, 1.24, "efficient hurdler", "hurdling technique costing time vs flat speed"),
    ("400H", "400", 1.08, 1.15, "efficient over the barriers", "hurdles costing a lot vs flat 400"),
    ("TJ", "LJ", 2.00, 2.15, "stronger long jumper (TJ relatively weak)", "natural triple jumper (TJ relatively strong)"),
]


def get_event_ratios(df: pd.DataFrame) -> pd.DataFrame:
    """Compare each athlete's PBs across paired events against typical ratio bands."""
    track = df[df["is_track"] | df["event_code"].isin(["LJ", "TJ"])]
    pbs = {}
    for (athlete, code), g in track.groupby(["athlete_name", "event_code"]):
        is_track = bool(g["is_track"].iloc[0])
        idx = g["perf_numeric"].idxmin() if is_track else g["perf_numeric"].idxmax()
        pbs[(athlete, code)] = (float(g.loc[idx, "perf_numeric"]), g.loc[idx, "performance"])
    rows = []
    for athlete in sorted({a for a, _ in pbs}):
        for longer, shorter, lo, hi, below, above in EVENT_RATIO_BENCHMARKS:
            if (athlete, longer) not in pbs or (athlete, shorter) not in pbs:
                continue
            l_val, l_str = pbs[(athlete, longer)]
            s_val, s_str = pbs[(athlete, shorter)]
            if s_val <= 0:
                continue
            ratio = l_val / s_val
            if ratio < lo:
                verdict, reading = "below band", below
            elif ratio > hi:
                verdict, reading = "above band", above
            else:
                verdict, reading = "typical", "balanced across the pair"
            rows.append({
                "athlete_name": athlete,
                "pair": f"{longer} / {shorter}",
                "pb_longer": l_str,
                "pb_shorter": s_str,
                "ratio": round(ratio, 3),
                "typical_range": f"{lo:.2f}-{hi:.2f}",
                "verdict": verdict,
                "reading": reading,
            })
    return pd.DataFrame(rows)


# =========================================================
# STANDARDS (national context from a user-supplied table)
# =========================================================

STANDARDS_COLUMNS = ["event", "sex", "age_group", "level", "standard", "source"]


def load_standards(path: str) -> pd.DataFrame:
    """Read a standards CSV: event, sex (M/F/blank), age_group, level, standard, source."""
    std = pd.read_csv(path, dtype=str).fillna("")
    missing = [c for c in STANDARDS_COLUMNS if c not in std.columns and c != "source"]
    if missing:
        raise ValueError(f"standards file is missing columns: {missing}")
    std["event_code"] = std["event"].apply(normalise_event_code)
    std["sex"] = std["sex"].str.strip().str.upper().str[:1]
    # age_group may list several labels separated by "|" (e.g. "U17|U16" so a
    # school-year standard matches both the old and new Po10 age-group labels)
    std["age_group"] = std["age_group"].str.upper().str.split("|")
    std = std.explode("age_group")
    std["age_group"] = std["age_group"].apply(normalise_age_group)
    std = std[std["age_group"] != ""]
    std["kind"] = std["event"].apply(infer_event_kind)
    std["standard_numeric"] = [parse_perf_numeric(v, k) for v, k in zip(std["standard"], std["kind"])]
    std = std.dropna(subset=["standard_numeric"])
    return std


def compare_to_standards(df: pd.DataFrame, standards: pd.DataFrame, sex_overrides: Optional[dict] = None) -> pd.DataFrame:
    """Best mark per athlete/event/age-group against the standards for that group.

    Age groups come from Po10's per-performance label (normalised), falling back
    to a label derived from the athlete's age when Po10's is blank or odd. Sex
    comes from the profile, the age-group suffix, or ``sex_overrides``
    ({athlete_name: "M"/"F"}).
    """
    rows = []
    if df.empty or standards.empty:
        return pd.DataFrame()
    ag = resolve_age_groups(df)
    sex = resolve_sex(df, sex_overrides)
    tmp = df.assign(_ag=ag, _sex=sex)
    tmp = tmp[tmp["_ag"] != ""]
    for (athlete, code, group), g in tmp.groupby(["athlete_name", "event_code", "_ag"]):
        is_track = bool(g["is_track"].iloc[0])
        idx = g["perf_numeric"].idxmin() if is_track else g["perf_numeric"].idxmax()
        best_val = float(g.loc[idx, "perf_numeric"])
        athlete_sex = g["_sex"].iloc[0]
        cand = standards[(standards["event_code"] == code) & (standards["age_group"] == group)]
        if athlete_sex:
            cand = cand[(cand["sex"] == athlete_sex) | (cand["sex"] == "")]
        if cand.empty:
            continue
        cand = cand.sort_values("standard_numeric", ascending=not is_track)  # easiest first
        met = cand[(cand["standard_numeric"] >= best_val) if is_track else (cand["standard_numeric"] <= best_val)]
        unmet = cand[(cand["standard_numeric"] < best_val) if is_track else (cand["standard_numeric"] > best_val)]
        next_std = unmet.iloc[0] if not unmet.empty else None
        rows.append({
            "athlete_name": athlete,
            "event": g["event"].iloc[0],
            "age_group": group,
            "best_in_group": g.loc[idx, "performance"],
            "best_year": int(g.loc[idx, "year"]),
            "standards_met": ", ".join(met["level"].tolist()) if not met.empty else "-",
            "next_standard": f"{next_std['level']} ({next_std['standard']})" if next_std is not None else "all met",
            "gap_to_next": round(abs(best_val - float(next_std["standard_numeric"])), 2) if next_std is not None else None,
            "gap_to_next_pct": round(abs(best_val - float(next_std["standard_numeric"])) / best_val * 100, 2) if next_std is not None else None,
            "source": next_std["source"] if next_std is not None else cand["source"].iloc[0],
        })
    out = pd.DataFrame(rows)
    return out.sort_values(["athlete_name", "event", "age_group"]) if not out.empty else out


# =========================================================
# AGE-GROUP LABEL HANDLING (for standards matching)
# =========================================================

def normalise_age_group(label) -> str:
    """Collapse Po10 / governing-body age-group labels to one form.

    'U20M', 'U20 W', 'u20' -> 'U20'; 'SENM', 'SM', 'Senior', 'SEN W' -> 'SEN';
    'V35W', 'M35', 'W40' -> 'V35' / 'V40'. Unknown labels are returned upper-cased.
    """
    s = re.sub(r"\s+", "", str(label or "")).upper()
    if not s or s in ("NAN", "NONE"):
        return ""
    s = s.replace("SENIOR", "SEN")
    if s in ("SM", "SW", "S", "SENIORS"):
        return "SEN"
    m = re.match(r"^(U\d{2}|V\d{2}|SEN)[MWF]?$", s)
    if m:
        return m.group(1)
    m = re.match(r"^[MW](\d{2})$", s)          # masters written as M35 / W40
    if m:
        return "V" + m.group(1)
    return s


def sex_from_age_group(label) -> str:
    """'U20M' -> 'M', 'U17W' -> 'F', otherwise ''."""
    s = re.sub(r"\s+", "", str(label or "")).upper()
    m = re.match(r"^(?:U\d{2}|V\d{2}|SEN)([MWF])$", s)
    if not m:
        return ""
    return "F" if m.group(1) in ("W", "F") else "M"


def _age_on(dob: pd.Timestamp, on: pd.Timestamp) -> int:
    years = on.year - dob.year
    if (on.month, on.day) < (dob.month, dob.day):
        years -= 1
    return years


def age_group_from_dob(dob, year: int) -> str:
    """Po10-style age-group label for a performance in ``year`` by someone born ``dob``.

    Used only when the scraped label is blank/unrecognised. From 2026 UK
    athletics uses even groups decided by age on 31 December (U14/U16/U18/U20);
    before that U13/U15/U17 went by age on the previous 31 August and U20 by
    age on 31 December. Masters bands are five years from 35.
    """
    if dob is None or pd.isna(dob):
        return ""
    year = int(year)
    on_dec31 = _age_on(dob, pd.Timestamp(year=year, month=12, day=31))
    if year >= 2026:
        for cap, label in ((13, "U14"), (15, "U16"), (17, "U18"), (19, "U20"), (22, "U23")):
            if on_dec31 <= cap:
                return label
    else:
        on_aug31 = _age_on(dob, pd.Timestamp(year=year - 1, month=8, day=31))
        for cap, label in ((12, "U13"), (14, "U15"), (16, "U17")):
            if on_aug31 <= cap:
                return label
        for cap, label in ((19, "U20"), (22, "U23")):
            if on_dec31 <= cap:
                return label
    if on_dec31 < 35:
        return "SEN"
    return f"V{(on_dec31 // 5) * 5}"


def resolve_age_groups(df: pd.DataFrame) -> pd.Series:
    """Normalised age-group label per row, derived from age where Po10's label is unusable."""
    labels = df["age_group"].apply(normalise_age_group) if "age_group" in df.columns else pd.Series("", index=df.index)
    known = labels.str.match(r"^(U\d{2}|V\d{2}|SEN)$")
    if known.all():
        return labels
    dob = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")
    if "dob_parsed" in df.columns:
        dob = df["dob_parsed"]
    if "dob_estimated" in df.columns:
        dob = dob.fillna(df["dob_estimated"])
    derived = pd.Series([age_group_from_dob(d, y) for d, y in zip(dob, df["year"])], index=df.index)
    return labels.where(known, derived)


def resolve_sex(df: pd.DataFrame, overrides: Optional[dict] = None) -> pd.Series:
    """'M'/'F'/'' per row: scraped gender, else age-group suffix, else per-athlete override."""
    sex = df["gender"].astype(str).str.strip().str.upper().str[:1] if "gender" in df.columns else pd.Series("", index=df.index)
    sex = sex.replace({"N": ""})  # 'nan'
    from_ag = df["age_group"].apply(sex_from_age_group) if "age_group" in df.columns else pd.Series("", index=df.index)
    sex = sex.where(sex != "", from_ag)
    if overrides:
        mapped = df["athlete_name"].map(lambda n: str(overrides.get(n, "") or "").upper()[:1])
        sex = sex.where(sex != "", mapped.fillna(""))
    return sex.fillna("")


def standards_match_diagnostics(df: pd.DataFrame, standards: pd.DataFrame) -> dict:
    """What the data and the standards file each contain, to explain a non-match."""
    raw_labels = sorted(df["age_group"].dropna().astype(str).unique().tolist()) if "age_group" in df.columns else []
    resolved = sorted(resolve_age_groups(df).replace("", pd.NA).dropna().unique().tolist()) if not df.empty else []
    data_events = sorted(df["event_code"].dropna().unique().tolist()) if "event_code" in df.columns else []
    return {
        "data_age_group_labels_raw": raw_labels,
        "data_age_groups_resolved": resolved,
        "data_event_codes": data_events,
        "standards_age_groups": sorted(standards["age_group"].unique().tolist()),
        "standards_event_codes": sorted(standards["event_code"].unique().tolist()),
        "overlap_age_groups": sorted(set(resolved) & set(standards["age_group"])),
        "overlap_event_codes": sorted(set(data_events) & set(standards["event_code"])),
    }