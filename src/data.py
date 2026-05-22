"""Data loading, lazy frame, and data-derived input constants."""

from pathlib import Path

import polars as pl

BASE_DIR = Path(__file__).resolve().parent.parent

INTRO_MD: str = (BASE_DIR / "md_files" / "intro.md").read_text(encoding="utf-8")

DATA_PATH = BASE_DIR / "data" / "scb_months_lvl1.parquet"

lf = pl.scan_parquet(DATA_PATH)
lf.collect_schema()

OCCS: list[str] = (
    lf.select(pl.col("occupation").unique().sort()).collect().to_series().to_list()
)

OCC_CHOICES: dict[str, str] = {o: o for o in OCCS}

SEXES: list[str] = (
    lf.select(pl.col("sex").unique().sort()).collect().to_series().to_list()
)

YEARS: list[int] = (
    lf.select(pl.col("year").unique().sort()).collect().to_series().to_list()
)

YEAR_MIN: int = min(YEARS)
YEAR_MAX: int = max(YEARS)
