from pathlib import Path

import plotly.express as px
import polars as pl
from shiny import reactive, render
from shiny.express import app_opts, ui
from shiny.express import input as app_input
from shinywidgets import render_widget

# --- Constants ---
MIN_POINTS_FOR_TRENDLINE = 2
DATA_PATH = Path(__file__).parent / "data" / "scb_months_lvl1.parquet"
LOGOS_PATH = Path(__file__).parent / "logos"


# --- Data Loading ---
def load_data():
    if not DATA_PATH.exists():
        return pl.DataFrame()
    return pl.read_parquet(DATA_PATH)


df_full = load_data()

# Identify metric columns
daioe_metrics = [
    col for col in df_full.columns if col.startswith("daioe_") and col.endswith("_wavg")
]
change_metrics = ["pct_chg_1m", "pct_chg_3m", "pct_chg_6m"]
sexes = df_full["sex"].unique().to_list() if not df_full.is_empty() else []
years = sorted(df_full["year"].unique().to_list()) if not df_full.is_empty() else []
occupations = (
    sorted(df_full["occupation"].unique().to_list())
    if not df_full.is_empty() and "occupation" in df_full.columns
    else []
)

# --- Page Options ---
app_opts(static_assets={"/logos": LOGOS_PATH})

ui.page_opts(
    title="AI Exposure & Employment Dashboard",
    fillable=True,
    theme=ui.Theme.from_brand(__file__),
)

ui.tags.style("""
.app-logo-wrap {
    display: flex;
    justify-content: center;
    margin: 0.25rem 0 1rem;
}

.app-logo {
    width: min(180px, 80%);
    height: auto;
    border-radius: 6px;
}
""")

# --- Sidebar ---
with ui.sidebar():
    ui.div(
        ui.img(src="/logos/lab.svg", alt="AI-Econ Lab logo", class_="app-logo"),
        class_="app-logo-wrap",
    )
    ui.input_select(
        "ai_metric",
        "Select AI Exposure Metric (Weighted Avg)",
        choices={
            m: m.replace("daioe_", "").replace("_wavg", "").title()
            for m in daioe_metrics
        },
        selected=daioe_metrics[-1] if daioe_metrics else None,
    )
    ui.input_select(
        "change_horizon",
        "Select Employment Change Horizon",
        choices={
            m: m.replace("pct_chg_", "").replace("m", " Month").title()
            for m in change_metrics
        },
        selected="pct_chg_3m",
    )
    ui.input_slider(
        "year_filter",
        "Filter by Year",
        min=min(years) if years else 2015,
        max=max(years) if years else 2026,
        value=[min(years), max(years)] if years else [2015, 2026],
        sep="",
    )
    ui.input_checkbox_group(
        "sex_filter",
        "Filter by Sex",
        choices=sexes,
        selected=sexes,
    )
    ui.input_selectize(
        "occ_filter",
        "Filter by Occupation (Leave blank for all)",
        choices=occupations,
        multiple=True,
    )
    ui.hr()
    ui.markdown("""
    **About this Dashboard**
    This app visualizes the relationship between AI Occupational Exposure (DAIOE)
    and monthly employment changes in Sweden.
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


# --- Main Layout ---
with ui.layout_columns(fill=False):
    with ui.value_box(theme="primary"):
        "Avg Exposure"

        @render.text
        def avg_exposure():
            df = filtered_df()
            if df.is_empty():
                return "0.0"
            val = df[app_input.ai_metric()].mean()
            return f"{val:.2f}"

    with ui.value_box(theme="secondary"):
        "Median % Change"

        @render.text
        def median_change():
            df = filtered_df()
            if df.is_empty():
                return "0.0%"
            val = df[app_input.change_horizon()].median()
            return f"{val:+.2f}%"

    with ui.value_box(theme="info"):
        "Observation Count"

        @render.text
        def obs_count():
            return f"{len(filtered_df()):,}"


with ui.card(full_screen=True):
    ui.card_header("AI Exposure vs. Employment Change")

    @render_widget
    def scatter_plot():
        df = filtered_df().to_pandas()
        if df.empty:
            return px.scatter(title="No data available for selected filters")

        fig = px.scatter(
            df,
            x=app_input.ai_metric(),
            y=app_input.change_horizon(),
            color="occupation",
            size="emp_count" if "emp_count" in df.columns else None,
            hover_data=["month", "sex", "emp_count"],
            labels={
                app_input.ai_metric(): "AI Exposure Score",
                app_input.change_horizon(): "% Change in Employment",
            },
            template="plotly_white",
            opacity=0.7,
            trendline="ols" if len(df) > MIN_POINTS_FOR_TRENDLINE else None,
            trendline_scope="overall" if len(df) > MIN_POINTS_FOR_TRENDLINE else None,
        )
        fig.update_layout(legend_title_text="Occupation")
        return fig


with ui.card(full_screen=True):
    ui.card_header("Filtered Data Table")

    @render.data_frame
    def data_table():
        return render.DataGrid(filtered_df().to_pandas())
