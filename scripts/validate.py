"""
validate.py.
------------
Gate for the monthly dataset the app deploys. Runs in 03_development_to_main.yml
before anything is promoted to `main` (and so before the Hugging Face Space is
rebuilt), and exits non-zero listing every failed check.

Usage:
    python scripts/validate.py data/scb_months_lvl1.parquet
    python scripts/validate.py NEW.parquet --previous DEPLOYED.parquet
"""

import argparse
import sys
from pathlib import Path

import polars as pl
import polars.selectors as cs

KEY = ["code_1", "sex", "month"]
EXPECTED_CODES = {str(i) for i in range(1, 10)}
EXPECTED_SEXES = {"men", "women"}
FIRST_MONTH = "2015-Jan"

# Plausibility bounds for the national total (thousands of employed persons,
# summed over the nine occupation groups and both sexes). Swedish employment
# aged 15-74 has been roughly 4.4 to 5.5 million; summing SCB's three
# overlapping employment categories gave about 14 million.
TOTAL_EMPLOYMENT_BOUNDS = (3_000, 8_000)

# Every occupation group except the (excluded) armed forces has a DAIOE score,
# so a missing one means unscored occupations are propagating again.
GUARD_METRIC = "daioe_allapps_wavg"


def check_structure(df: pl.DataFrame) -> list[str]:
    """Check keys, dimensions and month coverage."""
    required = [*KEY, "occupation", "year", "emp_count", GUARD_METRIC]
    missing = [c for c in required if c not in df.columns]
    if missing:
        return [f"missing required columns: {missing}"]

    failures = []
    duplicates = df.height - df.select(KEY).unique().height
    if duplicates:
        failures.append(f"{duplicates} duplicate rows on key {KEY}")

    codes = set(df["code_1"].unique())
    if codes != EXPECTED_CODES:
        failures.append(f"occupation codes are {sorted(codes)}, expected 1-9")

    sexes = set(df["sex"].unique())
    if sexes != EXPECTED_SEXES:
        failures.append(f"sexes are {sorted(sexes)}, expected {sorted(EXPECTED_SEXES)}")

    months = (
        df.select(pl.col("month").str.strptime(pl.Date, "%Y-%b").alias("d"))
        .unique()
        .sort("d")["d"]
        .to_list()
    )
    expected = pl.date_range(months[0], months[-1], interval="1mo", eager=True)
    if months != expected.to_list():
        failures.append("months are not contiguous")
    if months[0].strftime("%Y-%b") != FIRST_MONTH:
        failures.append(f"first month is {months[0]:%Y-%b}, expected {FIRST_MONTH}")

    per_month = df.group_by("month").agg(pl.len())["len"].n_unique()
    if per_month != 1:
        failures.append("months do not all have the same number of rows")
    return failures


def check_values(df: pl.DataFrame) -> list[str]:
    """Check for NaN/inf, range violations and the exposure null pattern."""
    failures = []

    for column in df.select(cs.float()).columns:
        bad = df.select(
            (pl.col(column).is_nan() | pl.col(column).is_infinite()).sum(),
        ).item()
        if bad:
            failures.append(f"{column}: {bad} NaN/inf values")

    if (df["emp_count"] < 0).any():
        failures.append("emp_count has negative values")

    low, high = TOTAL_EMPLOYMENT_BOUNDS
    totals = df.group_by("month").agg(pl.col("emp_count").sum().alias("total"))
    outside = totals.filter((pl.col("total") < low) | (pl.col("total") > high))
    if outside.height:
        worst = outside.sort("total")["total"].to_list()
        failures.append(
            f"{outside.height} months have total employment outside {low:,}-{high:,} "
            f"thousand (range {worst[0]:,.0f}-{worst[-1]:,.0f})",
        )

    for column in df.select(cs.starts_with("pctl_")).columns:
        lo, hi = df[column].min(), df[column].max()
        if lo is not None and not (0 <= lo and hi <= 100):
            failures.append(f"{column}: outside 0-100 (min {lo}, max {hi})")

    for column in df.select(cs.ends_with("_Level_Exposure")).columns:
        lo, hi = df[column].min(), df[column].max()
        if lo is not None and not (1 <= lo and hi <= 5):
            failures.append(f"{column}: outside 1-5 (min {lo}, max {hi})")

    # A percentile and level exist exactly when the score does. A percentile
    # on a null score is how unscored occupations got ranked as most exposed.
    for wavg in df.select(cs.ends_with("_wavg") & cs.starts_with("daioe_")).columns:
        metric = wavg[len("daioe_") : -len("_wavg")]
        for derived in (f"pctl_daioe_{metric}_wavg", f"daioe_{metric}_Level_Exposure"):
            if derived not in df.columns:
                continue
            mismatch = df.select(
                (pl.col(wavg).is_null() != pl.col(derived).is_null()).sum(),
            ).item()
            if mismatch:
                failures.append(
                    f"{derived}: null pattern differs from {wavg} in {mismatch} rows"
                )

    unscored = df[GUARD_METRIC].null_count()
    if unscored:
        failures.append(f"{GUARD_METRIC}: {unscored} rows have no score (groups 1-9)")

    return failures


def check_against_previous(df: pl.DataFrame, previous: pl.DataFrame) -> list[str]:
    """Check the new dataset has not shrunk or lost columns or months."""
    failures = []

    lost = sorted(set(previous.columns) - set(df.columns))
    if lost:
        failures.append(f"columns missing versus the deployed data: {lost}")
    if df.height < previous.height:
        failures.append(f"{df.height} rows, fewer than the deployed {previous.height}")

    def latest(frame: pl.DataFrame):
        return frame.select(
            pl.col("month").str.strptime(pl.Date, "%Y-%b").max(),
        ).item()

    if latest(df) < latest(previous):
        failures.append(
            f"latest month {latest(df):%Y-%b} is older than the deployed "
            f"{latest(previous):%Y-%b}",
        )
    return failures


def main() -> None:
    """Validate a dataset and exit non-zero if any check fails."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("path", type=Path, help="parquet file to validate")
    parser.add_argument("--previous", type=Path, help="currently deployed parquet")
    args = parser.parse_args()

    df = pl.read_parquet(args.path)
    failures = check_structure(df)
    if not failures:
        failures = check_values(df)
    if args.previous is not None:
        failures += check_against_previous(df, pl.read_parquet(args.previous))

    if failures:
        print(f"FAILED: {len(failures)} check(s) on {args.path}")
        for failure in failures:
            print(f"  - {failure}")
        sys.exit(1)
    print(f"OK: {args.path} passed all checks ({df.height} rows)")


if __name__ == "__main__":
    main()
