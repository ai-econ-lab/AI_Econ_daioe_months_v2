from pathlib import Path

import plotly.express as px
import polars as pl
from shiny import reactive, render
from shiny.express import input as app_input
from shiny.express import ui
from shinywidgets import render_widget

# --- Constants ---
MIN_POINTS_FOR_TRENDLINE = 2
DATA_PATH = Path(__file__).parent / "data" / "scb_months_lvl1.parquet"

# Brand-aligned color sequence for occupation dots
BRAND_COLORS = [
    "#4D6CFA",  # violet (primary accent)
    "#BA274A",  # red
    "#0C0A3E",  # deep blue
    "#5BC0BE",  # teal
    "#F9A03F",  # amber
    "#8B5CF6",  # purple
    "#2A2E45",  # gray-blue
    "#E8A838",  # gold
    "#6B9BC3",  # steel blue
]

# Human-readable labels for DAIOE weighted-average metrics
METRIC_LABELS = {
    "daioe_allapps_wavg":    "All AI Applications",
    "daioe_stratgames_wavg": "Strategic Games",
    "daioe_videogames_wavg": "Video Games",
    "daioe_imgrec_wavg":     "Image Recognition",
    "daioe_imgcompr_wavg":   "Image Compression",
    "daioe_imggen_wavg":     "Image Generation",
    "daioe_readcompr_wavg":  "Reading Comprehension",
    "daioe_lngmod_wavg":     "Language Models",
    "daioe_translat_wavg":   "Translation",
    "daioe_speechrec_wavg":  "Speech Recognition",
    "daioe_genai_wavg":      "Generative AI",
}

HORIZON_LABELS = {
    "pct_chg_1m": "1 Month",
    "pct_chg_3m": "3 Months",
    "pct_chg_6m": "6 Months",
}

# Columns to show in the data table (exclude the 60+ DAIOE variants)
TABLE_COLS = [
    "year", "month", "sex", "occupation", "emp_count",
    "pct_chg_1m", "pct_chg_3m", "pct_chg_6m",
    "daioe_allapps_wavg", "daioe_genai_wavg", "daioe_lngmod_wavg",
    "daioe_speechrec_wavg", "daioe_imgrec_wavg", "daioe_imggen_wavg",
    "daioe_translat_wavg", "daioe_readcompr_wavg",
    "daioe_stratgames_wavg", "daioe_videogames_wavg", "daioe_imgcompr_wavg",
]


# --- Data Loading ---
def load_data():
    if not DATA_PATH.exists():
        return pl.DataFrame()
    return pl.read_parquet(DATA_PATH)


df_full = load_data()

daioe_metrics = [
    col for col in df_full.columns if col.startswith("daioe_") and col.endswith("_wavg")
]
change_metrics = list(HORIZON_LABELS.keys())
sexes = df_full["sex"].unique().to_list() if not df_full.is_empty() else []
years = sorted(df_full["year"].unique().to_list()) if not df_full.is_empty() else []
occupations = (
    sorted(df_full["occupation"].unique().to_list())
    if not df_full.is_empty() and "occupation" in df_full.columns
    else []
)

# Build metric choice dict — fall back to auto-label for any unmapped columns
metric_choices = {
    m: METRIC_LABELS.get(m, m.replace("daioe_", "").replace("_wavg", "").replace("_", " ").title())
    for m in daioe_metrics
}

# Default to "All AI Applications" if present, else last metric
default_metric = (
    "daioe_allapps_wavg" if "daioe_allapps_wavg" in daioe_metrics
    else (daioe_metrics[-1] if daioe_metrics else None)
)


# --- Page Options ---
ui.page_opts(title="AI Exposure & Employment", fillable=True)

# --- Sidebar ---
with ui.sidebar(title="Filters"):
    ui.input_select(
        "ai_metric",
        "AI Exposure Metric",
        choices=metric_choices,
        selected=default_metric,
    )
    ui.input_select(
        "change_horizon",
        "Employment Change Horizon",
        choices=HORIZON_LABELS,
        selected="pct_chg_3m",
    )
    ui.input_slider(
        "year_filter",
        "Year Range",
        min=min(years) if years else 2015,
        max=max(years) if years else 2026,
        value=[min(years), max(years)] if years else [2015, 2026],
        sep="",
    )
    ui.input_checkbox_group(
        "sex_filter",
        "Sex",
        choices=sexes,
        selected=sexes,
    )
    ui.input_selectize(
        "occ_filter",
        "Occupation (blank = all)",
        choices=occupations,
        multiple=True,
    )
    ui.hr()
    ui.markdown("""
    **About**

    This dashboard visualizes the relationship between AI Occupational Exposure
    (DAIOE) and employment changes across Swedish occupational categories.

    Data: [Statistics Sweden (SCB)](https://www.scb.se) &
    DAIOE scores via the AI-Econ Lab.
    """)


# --- Reactive Logic ---
@reactive.calc
def filtered_df():
    if df_full.is_empty():
        return pl.DataFrame()

    df = df_full.filter(
        (pl.col("year") >= app_input.year_filter()[0])
        & (pl.col("year") <= app_input.year_filter()[1])
        & (pl.col("sex").is_in(app_input.sex_filter())),
    )

    if app_input.occ_filter():
        df = df.filter(pl.col("occupation").is_in(app_input.occ_filter()))

    return df


# --- KPI Cards ---
with ui.layout_columns(fill=False):
    with ui.value_box(theme="primary"):
        "Avg AI Exposure"

        @render.text
        def avg_exposure():
            df = filtered_df()
            if df.is_empty():
                return "—"
            val = df[app_input.ai_metric()].mean()
            return f"{val:.3f}"

        ui.p(
            "Weighted average DAIOE score",
            style="font-size:0.8rem; opacity:0.85; margin:0;",
        )

    with ui.value_box(theme="secondary"):
        "Median Employment Change"

        @render.text
        def median_change():
            df = filtered_df()
            if df.is_empty():
                return "—"
            val = df[app_input.change_horizon()].median()
            return f"{val:+.2f}%"

        @render.ui
        def median_change_label():
            return ui.p(
                f"Over {HORIZON_LABELS.get(app_input.change_horizon(), '')}",
                style="font-size:0.8rem; opacity:0.85; margin:0;",
            )

    with ui.value_box(theme="info"):
        "Observations"

        @render.text
        def obs_count():
            return f"{len(filtered_df()):,}"

        ui.p(
            "Data points after filtering",
            style="font-size:0.8rem; opacity:0.85; margin:0;",
        )


# --- Scatter Plot ---
with ui.card(full_screen=True):
    @render.ui
    def scatter_header():
        metric_label = metric_choices.get(app_input.ai_metric(), app_input.ai_metric())
        horizon_label = HORIZON_LABELS.get(app_input.change_horizon(), app_input.change_horizon())
        return ui.card_header(f"{metric_label} Exposure vs. {horizon_label} Employment Change")

    @render_widget
    def scatter_plot():
        df = filtered_df().to_pandas()
        metric = app_input.ai_metric()
        horizon = app_input.change_horizon()
        metric_label = metric_choices.get(metric, metric)
        horizon_label = HORIZON_LABELS.get(horizon, horizon)

        if df.empty:
            return px.scatter(title="No data available for the selected filters.")

        use_trendline = len(df) > MIN_POINTS_FOR_TRENDLINE

        fig = px.scatter(
            df,
            x=metric,
            y=horizon,
            color="occupation",
            size="emp_count" if "emp_count" in df.columns else None,
            hover_data=["month", "year", "sex", "emp_count"],
            labels={
                metric:  f"AI Exposure Score — {metric_label}",
                horizon: f"% Employment Change ({horizon_label})",
                "occupation": "Occupation",
                "emp_count":  "Employment",
                "month": "Month",
                "year":  "Year",
                "sex":   "Sex",
            },
            color_discrete_sequence=BRAND_COLORS,
            template="plotly_white",
            opacity=0.72,
            trendline="ols" if use_trendline else None,
            trendline_scope="overall" if use_trendline else None,
        )

        fig.update_layout(
            legend_title_text="Occupation",
            font_family="Nunito Sans",
            title_font_family="Montserrat",
            plot_bgcolor="#FFFFFF",
            paper_bgcolor="#FFFFFF",
            legend=dict(
                bgcolor="rgba(249,247,241,0.9)",
                bordercolor="#E0DDD6",
                borderwidth=1,
            ),
            margin=dict(l=60, r=30, t=40, b=60),
        )

        if use_trendline:
            fig.update_traces(
                selector=dict(mode="lines"),
                line=dict(color="#0C0A3E", width=2, dash="dot"),
            )

        return fig


# --- Data Table ---
with ui.card(full_screen=True):
    ui.card_header("Filtered Data")

    @render.data_frame
    def data_table():
        df = filtered_df()
        if df.is_empty():
            return render.DataGrid(df.to_pandas())

        # Show selected metric + selected horizon prominently; keep table manageable
        metric = app_input.ai_metric()
        horizon = app_input.change_horizon()

        priority_cols = ["year", "month", "sex", "occupation", "emp_count", metric, horizon]
        extra_cols = [c for c in TABLE_COLS if c not in priority_cols and c in df.columns]
        display_cols = [c for c in priority_cols + extra_cols if c in df.columns]

        return render.DataGrid(
            df.select(display_cols).to_pandas(),
            filters=True,
        )
