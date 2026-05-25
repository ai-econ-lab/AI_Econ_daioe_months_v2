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


def _sex_filter(lf: pl.LazyFrame, sex: str) -> pl.LazyFrame:
    """Filter by sex; 'All' is a no-op."""
    if sex == "All":
        return lf
    return lf.filter(pl.col("sex") == sex)


def get_occ_summary(
    lf: pl.LazyFrame,
    occupation: str,
    year: int,
    sex: str = "All",
) -> dict | None:
    """
    Return employment and percentage changes for the latest month of the given year.

    Sums emp_count and chg columns across sexes per month, derives pct changes from
    aggregated totals, then picks the most recent month.
    Returns a dict with keys: employment, pct_1m, pct_3m, year, month.
    Returns None if no data matches the filters.
    """
    df = (
        _sex_filter(lf, sex)
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
        .drop("_month_date")
        .collect()
    )

    if df.is_empty():
        return None

    row = df.row(0, named=True)

    return {
        "employment": row["emp_count"],
        "pct_1m": row["pct_chg_1m"],
        "pct_3m": row["pct_chg_3m"],
        "year": int(row["year"]),
        "month": str(row["month"]),
    }


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
    extra_sexes: tuple[str, ...] = (),
) -> pl.DataFrame:
    """
    Return monthly employment data with optional per-sex breakdowns.

    Always includes an 'All' series (aggregate across sexes).
    Pass extra_sexes to overlay individual sex lines (e.g. ('women', 'men')).
    Returns a DataFrame with columns: year, month, sex, emp_count, pct_chg_1m.
    """
    year_min, year_max = year_range
    base = lf.filter(
        (pl.col("occupation") == occupation)
        & (pl.col("year") >= year_min)
        & (pl.col("year") <= year_max),
    )

    def _monthly(lf_in: pl.LazyFrame, label: str) -> pl.DataFrame:
        return (
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
                    pl.lit(label).alias("sex"),
                ],
            )
            .sort("_date")
            .drop("_date")
            .collect()
        )

    frames = [_monthly(base, "All")]
    for s in extra_sexes:
        frames.append(_monthly(base.filter(pl.col("sex") == s), s.capitalize()))

    return pl.concat(frames)


def get_comparison_employment(
    lf: pl.LazyFrame,
    occupations: list[str],
    sex: str = "All",
) -> pl.DataFrame:
    """
    Return total employment and 1-month % change per year/month/occupation for the comparison view.

    Aggregates across the selected sex (or all sexes when sex='All').
    Returns a DataFrame with columns: year, month, occupation, emp_count, pct_chg_1m.
    """
    return (
        _sex_filter(lf, sex)
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
        .drop("_date")
        .collect()
    )


def get_comp_summary(
    lf: pl.LazyFrame,
    occupations: list[str],
    year: int,
    sex: str = "All",
) -> pl.DataFrame:
    """
    Return a per-occupation employment summary for the latest month of the selected year.

    Groups by occupation + month, aggregates for the selected sex (or all sexes),
    derives pct changes from aggregated totals, then picks the most recent month per occupation.
    Returns a DataFrame with columns: occupation, emp_count, pct_chg_1m, pct_chg_3m, pct_chg_6m.
    """
    return (
        _sex_filter(lf, sex)
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
        .sort(["occupation", "_month_date"], descending=[False, True])
        .group_by("occupation")
        .head(1)
        .select(["occupation", "emp_count", "pct_chg_1m", "pct_chg_3m", "pct_chg_6m"])
        .sort("occupation")
        .collect()
    )


def get_all_occ_summary(lf: pl.LazyFrame, year: int, sex: str = "All") -> pl.DataFrame:
    """
    Return latest-month employment summary for every occupation in the given year.

    Aggregates for the selected sex (or all sexes) and picks the most recent month per occupation.
    Returns a DataFrame with columns: occupation, emp_count, pct_chg_1m, pct_chg_3m.
    """
    return (
        _sex_filter(lf, sex)
        .filter(pl.col("year") == year)
        .group_by(["occupation", "month"])
        .agg(
            [
                pl.col("emp_count").sum(),
                _null_safe_sum("chg_1m"),
                _null_safe_sum("chg_3m"),
            ],
        )
        .with_columns(
            [
                _safe_pct("chg_1m", "emp_count", "pct_chg_1m"),
                _safe_pct("chg_3m", "emp_count", "pct_chg_3m"),
                pl.col("month").str.strptime(pl.Date, "%Y-%b").alias("_month_date"),
            ],
        )
        .sort(["occupation", "_month_date"], descending=[False, True])
        .group_by("occupation")
        .head(1)
        .select(["occupation", "emp_count", "pct_chg_1m", "pct_chg_3m"])
        .sort("occupation")
        .collect()
    )


def get_all_occ_ai_exposure(lf: pl.LazyFrame, year: int) -> pl.DataFrame:
    """
    Return AI percentile scores for every occupation, long format with domain labels.

    Returns a DataFrame with columns: occupation, domain, percentile.
    Sorted by occupation ascending, percentile descending within each occupation.
    """
    label_map = {col: AI_LABELS[col[5:]] for col in AI_PCTL_COLS}
    wide_df = (
        lf.filter(pl.col("year") == year)
        .group_by("occupation")
        .agg([pl.col(c).mean() for c in AI_PCTL_COLS])
        .collect()
    )
    return (
        wide_df.unpivot(
            on=AI_PCTL_COLS,
            index="occupation",
            variable_name="pctl_col",
            value_name="percentile",
        )
        .with_columns(
            pl.col("pctl_col")
            .replace(old=list(label_map.keys()), new=list(label_map.values()))
            .alias("domain"),
        )
        .drop("pctl_col")
        .sort(["occupation", "percentile"], descending=[False, True])
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
