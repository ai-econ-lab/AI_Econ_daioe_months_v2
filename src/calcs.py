import polars as pl

from .constants import (
    AI_LABELS,
    AI_LEVEL_COLS,
    AI_PCTL_COLS,
    AI_WAVG_COLS,
    EXPOSURE_LABELS,
)


def _null_safe_sum(col: str) -> pl.Expr:
    """Sum a change column, returning null (not 0) when every value in the group is null."""
    return (
        pl.when(pl.col(col).is_null().all())
        .then(pl.lit(None, dtype=pl.Float64))
        .otherwise(pl.col(col).sum())
        .alias(col)
    )


def _safe_pct(chg_col: str, emp_col: str, alias: str) -> pl.Expr:
    """Derive pct change from aggregated totals: chg / prev_emp * 100, null-safe."""
    prev = pl.col(emp_col) - pl.col(chg_col)
    return (
        pl.when(pl.col(chg_col).is_not_null() & (prev != 0))
        .then(pl.col(chg_col) / prev * 100)
        .otherwise(None)
        .alias(alias)
    )


def _gender_filter(lf: pl.LazyFrame, gender: str) -> pl.LazyFrame:
    """Filter by gender; 'All' is a no-op."""
    if gender == "All":
        return lf
    return lf.filter(pl.col("gender") == gender)


def get_occ_summary(
    lf: pl.LazyFrame,
    occupation: str,
    year: int,
    gender: str = "All",
) -> pl.DataFrame:
    """
    Return employment and percentage changes for the latest month of the given year.

    Sums emp_count and chg columns across genders per month, derives pct changes from
    aggregated totals, then picks the most recent month.
    Returns a single-row DataFrame with columns: emp_count, pct_chg_1m, pct_chg_3m, year, month.
    Returns an empty DataFrame if no data matches the filters.
    """
    return (
        _gender_filter(lf, gender)
        .filter(
            (pl.col("occupation") == occupation) & (pl.col("year") == year),
        )
        .group_by("month")
        .agg(
            [
                pl.col("emp_count").sum(),
                _null_safe_sum("chg_1m"),
                _null_safe_sum("chg_3m"),
                pl.col("year").first(),
            ],
        )
        .with_columns(
            [
                _safe_pct("chg_1m", "emp_count", "pct_chg_1m"),
                _safe_pct("chg_3m", "emp_count", "pct_chg_3m"),
                pl.col("month").str.strptime(pl.Date, "%Y-%b").alias("_month_date"),
            ],
        )
        .sort("_month_date", descending=True)
        .head(1)
        .select(["emp_count", "pct_chg_1m", "pct_chg_3m", "year", "month"])
        .collect()
    )


def get_occ_ai_exposure(
    lf: pl.LazyFrame,
    occupation: str,
    year: int,
) -> pl.DataFrame:
    """
    Return mean weighted AI exposure scores, exposure levels, and percentile ranks per sub-domain.

    Returns a long-format DataFrame with columns: domain, score, level, level_label, percentile.
    Used to power the ranked horizontal bar chart.
    """
    select_cols = AI_WAVG_COLS + AI_LEVEL_COLS + AI_PCTL_COLS
    df = (
        lf.filter(
            (pl.col("occupation") == occupation) & (pl.col("year") == year),
        )
        .select(select_cols)
        .collect()
    )

    rows = []
    for wavg_col, level_col, pctl_col in zip(
        AI_WAVG_COLS,
        AI_LEVEL_COLS,
        AI_PCTL_COLS,
        strict=False,
    ):
        raw_level = df[level_col].mean()
        level_val = round(raw_level) if raw_level is not None else None
        rows.append(
            {
                "domain": AI_LABELS[wavg_col],
                "score": df[wavg_col].mean(),
                "level": level_val,
                "level_label": EXPOSURE_LABELS.get(level_val, "Unknown")
                if level_val
                else "Unknown",
                "percentile": df[pctl_col].mean(),
            },
        )
    return pl.DataFrame(rows).sort("score")


def get_occ_employment(
    lf: pl.LazyFrame,
    occupation: str,
    year_range: tuple[int, int],
    extra_genders: tuple[str, ...] = (),
    *,
    smooth: bool = False,
) -> pl.DataFrame:
    """
    Return monthly employment data with optional per-gender breakdowns.

    Always includes an 'All' series (aggregate across genders).
    Pass extra_genders to overlay individual gender lines (e.g. ('women', 'men')).
    Returns a DataFrame with columns: year, month, gender, emp_count, pct_chg_1m.
    """
    year_min, year_max = year_range
    base = lf.filter(pl.col("occupation") == occupation)

    def _monthly(lf_in: pl.LazyFrame, label: str) -> pl.DataFrame:
        q = (
            lf_in.group_by(["year", "month"])
            .agg(
                [
                    pl.col("emp_count").sum(),
                    _null_safe_sum("chg_1m"),
                ],
            )
            .with_columns(
                [
                    _safe_pct("chg_1m", "emp_count", "pct_chg_1m"),
                    pl.col("month").str.strptime(pl.Date, "%Y-%b").alias("_date"),
                    pl.lit(label).alias("gender"),
                ],
            )
            .sort("_date")
        )
        if smooth:
            q = q.with_columns(
                [
                    pl.col("emp_count")
                    .rolling_mean(window_size=3, min_samples=1)
                    .alias("emp_count"),
                    pl.col("pct_chg_1m")
                    .rolling_mean(window_size=3, min_samples=1)
                    .alias("pct_chg_1m"),
                ],
            )
        return (
            q.filter((pl.col("year") >= year_min) & (pl.col("year") <= year_max))
            .drop("_date")
            .collect()
        )

    frames = [_monthly(base, "All")]
    for s in extra_genders:
        frames.append(_monthly(base.filter(pl.col("gender") == s), s.capitalize()))

    return pl.concat(frames)


def get_comparison_employment(
    lf: pl.LazyFrame,
    occupations: list[str],
    gender: str = "All",
    year_range: tuple[int, int] | None = None,
    *,
    smooth: bool = False,
) -> pl.DataFrame:
    """
    Return total employment and 1-month % change per year/month/occupation for the comparison view.

    Aggregates across the selected gender (or all genders when gender='All').
    When year_range is provided, the filter is applied after smoothing to preserve lookback context.
    Returns a DataFrame with columns: year, month, occupation, emp_count, pct_chg_1m.
    """
    q = (
        _gender_filter(lf, gender)
        .filter(pl.col("occupation").is_in(occupations))
        .group_by(["year", "month", "occupation"])
        .agg(
            [
                pl.col("emp_count").sum(),
                _null_safe_sum("chg_1m"),
            ],
        )
        .with_columns(
            [
                _safe_pct("chg_1m", "emp_count", "pct_chg_1m"),
                pl.col("month").str.strptime(pl.Date, "%Y-%b").alias("_date"),
            ],
        )
        .sort(["occupation", "_date"])
    )
    if smooth:
        q = q.with_columns(
            [
                pl.col("emp_count")
                .rolling_mean(window_size=3, min_samples=1)
                .over("occupation")
                .alias("emp_count"),
                pl.col("pct_chg_1m")
                .rolling_mean(window_size=3, min_samples=1)
                .over("occupation")
                .alias("pct_chg_1m"),
            ],
        )
    if year_range is not None:
        q = q.filter(
            (pl.col("year") >= year_range[0]) & (pl.col("year") <= year_range[1]),
        )
    return q.drop("_date").collect()


def get_comp_summary(
    lf: pl.LazyFrame,
    occupations: list[str],
    year: int,
    gender: str = "All",
) -> pl.DataFrame:
    """
    Return a per-occupation employment summary for the latest month of the selected year.

    Groups by occupation + month, aggregates for the selected gender (or all genders),
    derives pct changes from aggregated totals, then picks the most recent month per occupation.
    Returns a DataFrame with columns: occupation, emp_count, pct_chg_1m, pct_chg_3m, pct_chg_6m.
    """
    return (
        _gender_filter(lf, gender)
        .filter(
            pl.col("occupation").is_in(occupations) & (pl.col("year") == year),
        )
        .group_by(["occupation", "month"])
        .agg(
            [
                pl.col("emp_count").sum(),
                _null_safe_sum("chg_1m"),
                _null_safe_sum("chg_3m"),
                _null_safe_sum("chg_6m"),
            ],
        )
        .with_columns(
            [
                _safe_pct("chg_1m", "emp_count", "pct_chg_1m"),
                _safe_pct("chg_3m", "emp_count", "pct_chg_3m"),
                _safe_pct("chg_6m", "emp_count", "pct_chg_6m"),
                pl.col("month").str.strptime(pl.Date, "%Y-%b").alias("_month_date"),
            ],
        )
        .filter(pl.col("_month_date") == pl.col("_month_date").max().over("occupation"))
        .select(["occupation", "emp_count", "pct_chg_1m", "pct_chg_3m", "pct_chg_6m"])
        .sort("occupation")
        .collect()
    )


def get_comp_radar(
    lf: pl.LazyFrame,
    occupations: list[str],
    year: int,
) -> pl.DataFrame:
    """
    Return mean AI percentile scores per occupation for the radar chart.

    Returns a DataFrame with columns: occupation, pctl_<metric>_wavg for each metric.
    """
    return (
        lf.filter(
            pl.col("occupation").is_in(occupations) & (pl.col("year") == year),
        )
        .group_by("occupation")
        .agg([pl.col(c).mean() for c in AI_PCTL_COLS])
        .collect()
    )
