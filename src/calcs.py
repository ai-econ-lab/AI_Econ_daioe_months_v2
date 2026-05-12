import polars as pl


AI_WAVG_COLS = [
    "daioe_genai_wavg",
    "daioe_allapps_wavg",
    "daioe_stratgames_wavg",
    "daioe_videogames_wavg",
    "daioe_imgrec_wavg",
    "daioe_imgcompr_wavg",
    "daioe_imggen_wavg",
    "daioe_readcompr_wavg",
    "daioe_lngmod_wavg",
    "daioe_translat_wavg",
    "daioe_speechrec_wavg",
]

AI_LABELS = {
    "daioe_genai_wavg": "🧠 Generative AI",
    "daioe_allapps_wavg": "📚 All Applications",
    "daioe_stratgames_wavg": "♟️ Strategy Games",
    "daioe_videogames_wavg": "🎮 Video Games",
    "daioe_imgrec_wavg": "🖼️ Image Recognition",
    "daioe_imgcompr_wavg": "🧩 Image Comprehension",
    "daioe_imggen_wavg": "🎨 Image Generation",
    "daioe_readcompr_wavg": "📖 Reading Comprehension",
    "daioe_lngmod_wavg": "✍️ Language Modeling",
    "daioe_translat_wavg": "🌐 Translation",
    "daioe_speechrec_wavg": "🎙️ Speech Recognition",
}

AI_LEVEL_COLS = [c.replace("_wavg", "_Level_Exposure") for c in AI_WAVG_COLS]
AI_PCTL_COLS = [f"pctl_{c}" for c in AI_WAVG_COLS]

EXPOSURE_LABELS = {1: "Very Low", 2: "Low", 3: "Medium", 4: "High", 5: "Very High"}


def get_occ_summary(lf: pl.LazyFrame, occupation: str, year: int) -> dict | None:
    """
    Aggregate employment and percentage changes for one occupation and year.

    Sums emp_count across sexes per month, then averages across months.
    Returns a dict with keys: employment, pct_1m, pct_3m, pct_6m, year.
    Returns None if no data matches the filters.
    """
    df = (
        lf.filter(
            (pl.col("occupation") == occupation) & (pl.col("year") == year),
        )
        .group_by("month")
        .agg([
            pl.col("emp_count").sum(),
            pl.col("pct_chg_1m").mean(),
            pl.col("pct_chg_3m").mean(),
            pl.col("pct_chg_6m").mean(),
            pl.col("year").first(),
        ])
        .collect()
    )

    if df.is_empty():
        return None

    def _mean_or_none(col: str) -> float | None:
        val = df[col].mean()
        return None if val is None else float(val)

    return {
        "employment": float(df["emp_count"].mean()),
        "pct_1m": _mean_or_none("pct_chg_1m"),
        "pct_3m": _mean_or_none("pct_chg_3m"),
        "pct_6m": _mean_or_none("pct_chg_6m"),
        "year": int(df["year"][0]),
    }


def get_occ_ai_exposure(
    lf: pl.LazyFrame, occupation: str, year: int,
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
    for wavg_col, level_col, pctl_col in zip(AI_WAVG_COLS, AI_LEVEL_COLS, AI_PCTL_COLS, strict=False):
        raw_level = df[level_col].mean()
        level_val = round(raw_level) if raw_level is not None else None
        rows.append({
            "domain": AI_LABELS[wavg_col],
            "score": df[wavg_col].mean(),
            "level": level_val,
            "level_label": EXPOSURE_LABELS.get(level_val, "Unknown") if level_val else "Unknown",
            "percentile": df[pctl_col].mean(),
        })
    return pl.DataFrame(rows).sort("score")


def get_occ_employment_by_sex(
    lf: pl.LazyFrame,
    occupation: str,
    year_range: tuple[int, int],
    sexes: list[str],
) -> pl.DataFrame:
    """
    Return monthly employment counts per sex for a given occupation and year range.

    Returns a DataFrame with columns: year, month, sex, emp_count, pct_chg_1m.
    Used to power the employment trend line chart in the Occupation View.
    """
    year_min, year_max = year_range
    return (
        lf.filter(
            (pl.col("occupation") == occupation)
            & (pl.col("year") >= year_min)
            & (pl.col("year") <= year_max)
            & (pl.col("sex").is_in(sexes)),
        )
        .group_by(["year", "month", "sex"])
        .agg([
            pl.col("emp_count").sum(),
            pl.col("pct_chg_1m").mean(),
        ])
        .sort(["sex", "year", "month"])
        .collect()
    )


def get_comparison_employment(
    lf: pl.LazyFrame,
    occupations: list[str],
    sexes: list[str],
) -> pl.DataFrame:
    """
    Return total employment per year/month/occupation for the comparison view.

    Aggregates across the selected sexes.
    Returns a DataFrame with columns: year, month, occupation, emp_count, pct_chg_1m.
    """
    return (
        lf.filter(
            pl.col("occupation").is_in(occupations)
            & pl.col("sex").is_in(sexes),
        )
        .group_by(["year", "month", "occupation"])
        .agg([
            pl.col("emp_count").sum(),
            pl.col("pct_chg_1m").mean(),
        ])
        .sort(["occupation", "year", "month"])
        .collect()
    )


def get_comp_summary(
    lf: pl.LazyFrame,
    occupations: list[str],
    sexes: list[str],
    year: int,
) -> pl.DataFrame:
    """
    Return a per-occupation employment summary for the selected year.

    Returns a DataFrame with columns: occupation, emp_count, pct_chg_1m, pct_chg_3m, pct_chg_6m.
    Used to populate the summary table in the Comparison View.
    """
    return (
        lf.filter(
            pl.col("occupation").is_in(occupations)
            & pl.col("sex").is_in(sexes)
            & (pl.col("year") == year),
        )
        .group_by("occupation")
        .agg([
            pl.col("emp_count").mean().alias("emp_count"),
            pl.col("pct_chg_1m").mean().alias("pct_chg_1m"),
            pl.col("pct_chg_3m").mean().alias("pct_chg_3m"),
            pl.col("pct_chg_6m").mean().alias("pct_chg_6m"),
        ])
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
            pl.col("occupation").is_in(occupations)
            & (pl.col("year") == year),
        )
        .group_by("occupation")
        .agg([pl.col(c).mean() for c in AI_PCTL_COLS])
        .collect()
    )
