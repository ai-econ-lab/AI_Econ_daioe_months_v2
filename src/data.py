"""Data loading, lazy frame, and data-derived input constants."""

from pathlib import Path

import polars as pl

BASE_DIR = Path(__file__).resolve().parent.parent

INTRO_MD: str = (BASE_DIR / "md_files" / "intro.md").read_text(encoding="utf-8")

_ABOUT_TEMPLATE: str = (BASE_DIR / "md_files" / "about.md").read_text(encoding="utf-8")

DATA_PATH = BASE_DIR / "data" / "scb_months_lvl1.parquet"

lf = (
    pl.read_parquet(DATA_PATH)
    .rename({"sex": "gender"})
    .with_columns(pl.col("month").str.strptime(pl.Date, "%Y-%b").alias("month_date"))
    .lazy()
)

# Query metadata in parallel using collect_all
lf_occs = lf.select(pl.col("occupation").unique().sort())
lf_genders = lf.select(pl.col("gender").unique().sort())
lf_years = lf.select(pl.col("year").unique().sort())
lf_months = lf.select(["month", "month_date"]).unique().sort("month_date")

_meta_dfs = pl.collect_all([lf_occs, lf_genders, lf_years, lf_months])

OCCS: list[str] = _meta_dfs[0].to_series().to_list()
OCC_CHOICES: dict[str, str] = {o: o for o in OCCS}
GENDERS: list[str] = _meta_dfs[1].to_series().to_list()
YEARS: list[int] = _meta_dfs[2].to_series().to_list()

_months_sorted = _meta_dfs[3]
MONTH_EARLIEST: str = _months_sorted.head(1)["month"][0]
MONTH_LATEST: str = _months_sorted.tail(1)["month"][0]

YEAR_MIN: int = min(YEARS)
YEAR_MAX: int = max(YEARS)

ABOUT_MD: str = _ABOUT_TEMPLATE.format(
    MONTH_EARLIEST=MONTH_EARLIEST,
    MONTH_LATEST=MONTH_LATEST,
)
