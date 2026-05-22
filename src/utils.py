"""Download helpers, table rendering, and column label formatters."""

import importlib.util
import io
import re

import pandas as pd
from great_tables import GT
from shiny import ui


def metric_display_name(metric_key: str, metrics: dict[str, str]) -> str:
    """Return a human-readable metric label with leading icons stripped."""
    label = metrics.get(metric_key, metric_key.replace("_", " ").title())
    return re.sub(r"^[^A-Za-z0-9]+\s*", "", label).strip()


def readable_column_name(col: str, metrics: dict[str, str]) -> str:
    """Convert a raw dataset column name into a readable table header."""
    exact: dict[str, str] = {
        "code_1": "SSYK Major Group",
        "occupation": "Occupation",
        "year": "Year",
        "month": "Month",
        "sex": "Sex",
        "emp_count": "Employees",
        "weight_sum": "Weight Sum",
        "chg_1m": "Emp Change 1mo (#)",
        "chg_3m": "Emp Change 3mo (#)",
        "chg_6m": "Emp Change 6mo (#)",
        "pct_chg_1m": "Emp Change 1mo (%)",
        "pct_chg_3m": "Emp Change 3mo (%)",
        "pct_chg_6m": "Emp Change 6mo (%)",
    }
    if col in exact:
        return exact[col]

    col_l = col.lower()
    if col_l.startswith("pctl_") and col_l.endswith("_wavg"):
        metric_key = col[5:-5]
        return f"{metric_display_name(metric_key, metrics)} Percentile (Weighted Avg)"
    if col_l.endswith("_wavg"):
        metric_key = col[:-5]
        return f"{metric_display_name(metric_key, metrics)} (Weighted Avg)"
    if col_l.endswith("_avg"):
        metric_key = col[:-4]
        return f"{metric_display_name(metric_key, metrics)} (Average)"
    if col_l.endswith("_level_exposure"):
        metric_key = col[: -len("_level_exposure")]
        return f"{metric_display_name(metric_key, metrics)} Exposure Level"

    fallback = col.replace("_", " ").title()
    return (
        fallback.replace("Ssyk", "SSYK").replace("Ai", "AI").replace("Daioe", "DAIOE")
    )


def as_great_table_html(df: pd.DataFrame, metrics: dict[str, str]) -> ui.TagChild:
    """Render a pandas DataFrame as Great Tables HTML with readable headers."""
    if df.empty:
        return ui.p("No data available for the selected filters.")

    df_display = df.rename(
        columns={c: readable_column_name(c, metrics) for c in df.columns},
    )

    float_cols = [
        c
        for c in df_display.columns
        if c != "Year" and pd.api.types.is_float_dtype(df_display[c])
    ]

    gt = (
        GT(df_display)
        .opt_row_striping()
        .tab_options(
            table_font_names=["Nunito Sans", "Arial", "sans-serif"],
            table_width="100%",
        )
        .opt_stylize(style=2, color="blue")
    )

    if float_cols:
        gt = gt.fmt_number(columns=float_cols, decimals=2)

    return ui.HTML(gt.as_raw_html())


def download_extension(fmt: str) -> str:
    """Map a download format name to its file extension."""
    return {"csv": "csv", "parquet": "parquet", "excel": "xlsx"}.get(fmt, "csv")


def download_media_type(fmt: str) -> str:
    """Return the browser media type for a download format."""
    if fmt == "parquet":
        return "application/octet-stream"
    if fmt == "excel":
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return "text/csv"


def export_filtered_data(df: pd.DataFrame, fmt: str) -> str | bytes:
    """Serialise a DataFrame to csv, parquet, or excel bytes for a Shiny download."""
    if fmt == "parquet":
        return df.to_parquet(index=False)

    if fmt == "excel":
        engine = None
        if importlib.util.find_spec("openpyxl") is not None:
            engine = "openpyxl"
        elif importlib.util.find_spec("xlsxwriter") is not None:
            engine = "xlsxwriter"
        else:
            raise RuntimeError("Excel export requires openpyxl or xlsxwriter.")

        buffer = io.BytesIO()
        df.to_excel(buffer, index=False, engine=engine)
        return buffer.getvalue()

    return df.to_csv(index=False)
