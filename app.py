from pathlib import Path

import faicons as fa
import polars as pl
from shiny import reactive, render
from shiny.express import app_opts, ui
from shiny.express import input as app_input
from shinywidgets import render_widget

from src.calcs import (
    get_comp_radar,
    get_comp_summary,
    get_comparison_employment,
    get_occ_ai_exposure,
    get_occ_employment,
    get_occ_summary,
)
from src.constants import FIRST_COLS, METRICS
from src.data import INTRO_MD, OCC_CHOICES, OCCS, YEAR_MAX, YEAR_MIN, YEARS, lf
from src.utils import (
    as_great_table_html,
    download_extension,
    download_media_type,
    export_filtered_data,
)
from src.visuals import (
    build_ai_exposure_bar,
    build_comp_radar_plot,
    build_comparison_employment_plot,
    build_employment_chart,
    build_employment_count_chart,
    build_value_boxes,
    export_fig,
)

LOGOS_PATH = Path(__file__).parent / "logos"
app_opts(static_assets={"/logos": LOGOS_PATH})

ui.page_opts(
    # title="AI Exposure & Monthly Employment Explorer",
    fillable=True,
    theme=ui.Theme.from_brand(__file__),
)

_DEFAULT_OCC = OCCS[0] if OCCS else None


# ── Tab navigation ────────────────────────────────────────────

with ui.navset_pill(id="main_tabs"):
    # ── Tab 1: Occupation View ────────────────────────────────

    with ui.nav_panel("Occupation View"), ui.layout_sidebar():
        with ui.sidebar(title="Occupation View", width=280):
            ui.div(
                ui.img(
                    src="/logos/lab.svg",
                    alt="AI-Econ Lab logo",
                    style="width:100%; max-width:180px;",
                ),
                style="text-align:center; margin-bottom:1rem;",
            )
            ui.markdown(INTRO_MD)
            ui.hr()
            ui.input_selectize(
                "occ_occupation",
                "Occupation",
                choices=OCC_CHOICES,
                selected=_DEFAULT_OCC,
            )
            ui.input_select(
                "occ_year",
                "Year (snapshot)",
                choices={str(y): str(y) for y in YEARS},
                selected=str(YEAR_MAX),
            )
            ui.hr()
            ui.p("Employment trend filters:", class_="fw-semibold mb-1 small")
            ui.input_slider(
                "occ_year_range",
                "Year Range",
                min=YEAR_MIN,
                max=YEAR_MAX,
                value=[YEAR_MIN, YEAR_MAX],
                sep="",
            )

        # Value boxes
        @render.ui
        def occ_value_boxes():
            summary = occ_summary()
            if summary is None:
                return ui.p(
                    "No data for the selected occupation and year.",
                    class_="text-muted p-3",
                )
            return build_value_boxes(summary, app_input.occ_occupation())

        # Stacked cards (full width)
        with ui.layout_columns(col_widths=12):
            with ui.card(full_screen=True, height="700px"):
                with ui.card_header(class_="d-flex align-items-center"):
                    ui.span("AI Exposure by Sub-Domain")
                    with ui.span(class_="ms-auto"):

                        @render.download(
                            filename="ai_exposure.png",
                            media_type="image/png",
                            label=fa.icon_svg("download"),
                        )
                        async def dl_ai_bar():
                            yield export_fig(
                                build_ai_exposure_bar(
                                    occ_ai_exposure().to_pandas(),
                                    app_input.occ_occupation(),
                                    int(app_input.occ_year()),
                                ),
                            )

                @render_widget
                def occ_ai_bar():
                    df = occ_ai_exposure().to_pandas()
                    return build_ai_exposure_bar(
                        df,
                        app_input.occ_occupation(),
                        int(app_input.occ_year()),
                    )

            with ui.card(full_screen=True, height="700px"):
                with ui.card_header(class_="d-flex align-items-center"):
                    ui.span("Monthly Employment Count")
                    with ui.span(class_="ms-auto"):

                        @render.download(
                            filename="monthly_employment_count.png",
                            media_type="image/png",
                            label=fa.icon_svg("download"),
                        )
                        async def dl_occ_employment_count():
                            yield export_fig(
                                build_employment_count_chart(
                                    occ_employment().to_pandas(),
                                    app_input.occ_occupation(),
                                ),
                            )

                @render_widget
                def occ_employment_count_chart():
                    df = occ_employment().to_pandas()
                    return build_employment_count_chart(df, app_input.occ_occupation())

            with ui.card(full_screen=True, height="700px"):
                with ui.card_header(class_="d-flex align-items-center"):
                    ui.span("Monthly Employment Change")
                    with ui.span(class_="ms-auto"):

                        @render.download(
                            filename="monthly_employment.png",
                            media_type="image/png",
                            label=fa.icon_svg("download"),
                        )
                        async def dl_occ_employment():
                            yield export_fig(
                                build_employment_chart(
                                    occ_employment().to_pandas(),
                                    app_input.occ_occupation(),
                                ),
                            )

                @render_widget
                def occ_employment_chart():
                    df = occ_employment().to_pandas()
                    return build_employment_chart(df, app_input.occ_occupation())

    # ── Tab 2: Comparison View ────────────────────────────────

    with ui.nav_panel("Comparison View"), ui.layout_sidebar():
        with ui.sidebar(title="Comparison View", width=280):
            ui.input_selectize(
                "comp_occupations",
                "Occupations (up to 5)",
                choices=OCC_CHOICES,
                multiple=True,
                options={"maxItems": 5, "placeholder": "Select occupations..."},
            )
            ui.input_select(
                "comp_year",
                "Year (AI snapshot)",
                choices={str(y): str(y) for y in YEARS},
                selected=str(YEAR_MAX),
            )

        # Employment summary table
        with ui.card(fill=True, fillable=True):
            ui.card_header("Occupations Summary")

            @render.ui
            def comp_summary_table():
                occs = list(app_input.comp_occupations() or [])
                if not occs:
                    return ui.p(
                        "Select at least one occupation.",
                        class_="text-muted p-3",
                    )
                df = get_comp_summary(
                    lf,
                    occs,
                    int(app_input.comp_year()),
                ).to_pandas()
                return ui.div(
                    as_great_table_html(df, METRICS),
                    style="overflow: auto; width: 100%; height: 100%;",
                )

        # AI percentile radar chart
        with ui.card(full_screen=True, height="700px"):
            with ui.card_header(class_="d-flex align-items-center"):
                ui.span("AI Percentile Radar Comparison")
                with ui.span(class_="ms-auto"):

                    @render.download(
                        filename="ai_radar.png",
                        media_type="image/png",
                        label=fa.icon_svg("download"),
                    )
                    async def dl_comp_radar():
                        yield export_fig(
                            build_comp_radar_plot(
                                comp_radar_data().to_pandas(),
                                METRICS,
                            ),
                        )

            @render_widget
            def comp_radar_chart():
                df = comp_radar_data().to_pandas()
                return build_comp_radar_plot(df, METRICS)

        # Employment comparison line chart
        with ui.card(full_screen=True, height="700px"):
            with ui.card_header(class_="d-flex align-items-center"):
                ui.span("Monthly Employment Change")
                with ui.span(class_="ms-auto"):

                    @render.download(
                        filename="comparison_employment.png",
                        media_type="image/png",
                        label=fa.icon_svg("download"),
                    )
                    async def dl_comp_employment():
                        yield export_fig(
                            build_comparison_employment_plot(
                                comparison_data().to_pandas(),
                            ),
                        )

            @render_widget
            def comp_employment_chart():
                df = comparison_data().to_pandas()
                return build_comparison_employment_plot(df)

    # ── Tab 3: Download ───────────────────────────────────────

    with ui.nav_panel("Download"), ui.layout_sidebar():
        with ui.sidebar(title="Download Filters", width=280):
            ui.input_slider(
                "dl_year_range",
                "Year Range",
                min=YEAR_MIN,
                max=YEAR_MAX,
                value=[YEAR_MIN, YEAR_MAX],
                sep="",
            )
            ui.input_selectize(
                "dl_occupations",
                "Occupation (blank = all)",
                choices=OCC_CHOICES,
                multiple=True,
            )
            ui.input_select(
                "dl_format",
                "Format",
                choices={"csv": "CSV", "parquet": "Parquet", "excel": "Excel"},
                selected="csv",
            )

            @render.download(
                filename=lambda: (
                    f"daioe_months.{download_extension(app_input.dl_format())}"
                ),
                media_type=lambda: download_media_type(app_input.dl_format()),
            )
            async def download_data():
                df = download_frame().to_pandas()
                yield export_filtered_data(df, app_input.dl_format())

        ui.p(
            "Export the filtered row-level dataset or inspect a compact preview before downloading.",
            class_="text-muted mb-3",
        )

        with ui.layout_columns(col_widths=[6, 6]):
            with ui.value_box(theme="primary"):
                "Rows"

                @render.text
                def dl_row_count():
                    return f"{len(download_frame()):,}"

            with ui.value_box(theme="primary"):
                "Columns"

                @render.text
                def dl_col_count():
                    return f"{len(download_frame().columns):,}"

        # Data preview
        with ui.card(full_screen=True):
            ui.card_header("Data Preview (first 50 rows)")

            @render.ui
            def dl_preview():
                df = download_frame().head(50)
                all_cols = df.columns
                ordered = [c for c in FIRST_COLS if c in all_cols]
                rest = [c for c in all_cols if c not in ordered]
                return as_great_table_html(
                    df.select(ordered + rest).to_pandas(),
                    METRICS,
                )


# ── Reactive calculations ─────────────────────────────────────


@reactive.calc
def occ_summary():
    return get_occ_summary(lf, app_input.occ_occupation(), int(app_input.occ_year()))


@reactive.calc
def occ_ai_exposure():
    return get_occ_ai_exposure(
        lf,
        app_input.occ_occupation(),
        int(app_input.occ_year()),
    )


@reactive.calc
def occ_employment():
    yr = app_input.occ_year_range()
    return get_occ_employment(
        lf,
        app_input.occ_occupation(),
        (yr[0], yr[1]),
    )


@reactive.calc
def comparison_data():
    occs = list(app_input.comp_occupations() or [])
    if not occs:
        return pl.DataFrame(
            schema={
                "year": pl.Int64,
                "month": pl.String,
                "occupation": pl.String,
                "emp_count": pl.Float64,
                "pct_chg_1m": pl.Float64,
            },
        )
    return get_comparison_employment(lf, occs)


@reactive.calc
def comp_radar_data():
    occs = list(app_input.comp_occupations() or [])
    if not occs:
        return pl.DataFrame()
    return get_comp_radar(lf, occs, int(app_input.comp_year()))


@reactive.calc
def download_frame():
    yr = app_input.dl_year_range()
    q = lf.filter(
        (pl.col("year") >= yr[0]) & (pl.col("year") <= yr[1]),
    )
    if app_input.dl_occupations():
        q = q.filter(pl.col("occupation").is_in(list(app_input.dl_occupations())))
    return q.collect()
