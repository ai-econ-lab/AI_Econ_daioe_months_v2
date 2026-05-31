from pathlib import Path

import faicons as fa
import polars as pl
from shiny import reactive, render
from shiny.express import app_opts, ui
from shiny.express import input as app_input
from shinywidgets import render_widget

from src.calcs import (
    get_all_occ_ai_exposure,
    get_all_occ_summary,
    get_comp_radar,
    get_comp_summary,
    get_comparison_employment,
    get_occ_ai_exposure,
    get_occ_employment,
    get_occ_summary,
)
from src.constants import FIRST_COLS, METRICS
from src.data import (
    ABOUT_MD,
    GENDERS,
    INTRO_MD,
    OCC_CHOICES,
    OCCS,
    YEAR_MAX,
    YEAR_MIN,
    YEARS,
    lf,
)
from src.utils import (
    as_great_table_html,
    download_extension,
    download_media_type,
    export_filtered_data,
)
from src.visuals import (
    build_ai_exposure_bar,
    build_comp_radar_plot,
    build_comparison_employment_count_plot,
    build_comparison_employment_plot,
    build_employment_chart,
    build_employment_count_chart,
    build_occupation_ribbon,
    build_value_boxes,
    export_fig,
)

LOGOS_PATH = Path(__file__).parent / "logos"
CSS_PATH = Path(__file__).parent / "css"
app_opts(static_assets={"/logos": LOGOS_PATH, "/css": CSS_PATH})

ui.page_opts(
    fillable=True,
    theme=ui.Theme.from_brand(__file__),
)

ui.tags.link(rel="stylesheet", href="/css/ticker.css")

_DEFAULT_OCC = OCCS[0] if OCCS else None
_GENDER_CHOICES = {"All": "All", **{s: s.capitalize() for s in GENDERS}}


# ── Tab navigation ────────────────────────────────────────────

with ui.navset_pill(id="main_tabs"):
    # ── Tab 1: Occupation View ────────────────────────────────

    with ui.nav_panel("Single Occupation"), ui.layout_sidebar():
        with ui.sidebar(title="Single Occupation", width=280):
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
                options={"placeholder": "Search occupation..."},
            )
            ui.p(
                "SSYK 2012 major groups (9 categories).",
                class_="text-muted small mt-n1 mb-2",
            )
            ui.input_selectize(
                "occ_gender",
                "Show gender lines",
                choices={s: s.capitalize() for s in GENDERS},
                multiple=True,
                options={"placeholder": "Select to overlay..."},
            )
            ui.input_select(
                "occ_year",
                "Year",
                choices={str(y): str(y) for y in YEARS},
                selected=str(YEAR_MAX),
            )
            ui.p(
                "Year for the AI exposure scores.",
                class_="text-muted small mt-n1 mb-2",
            )
            ui.hr()
            ui.p("Employment trend filters:", class_="fw-semibold mb-1 small")
            ui.input_slider(
                "occ_year_range",
                "Employment date range",
                min=YEAR_MIN,
                max=YEAR_MAX,
                value=[max(YEAR_MIN, YEAR_MAX - 3), YEAR_MAX],
                sep="",
            )
            ui.input_checkbox(
                "occ_smooth",
                "Apply 3-month moving average",
                value=False,
            )

        # Value boxes
        @render.ui
        def occ_ribbon():
            summary_df = all_occ_summary()
            if summary_df.is_empty():
                return None
            return build_occupation_ribbon(
                summary_df.to_pandas(),
                all_occ_ai().to_pandas(),
                int(app_input.occ_year()),
            )

        @render.ui
        def occ_value_boxes():
            summary = occ_summary()
            if summary.is_empty():
                return ui.p(
                    "No data for the selected occupation and year.",
                    class_="text-muted p-3",
                )
            return build_value_boxes(summary, app_input.occ_occupation())

        # Stacked cards (full width)
        with ui.layout_columns(col_widths=12):
            with ui.card(full_screen=True, height="700px"):
                with ui.card_header(class_="d-flex align-items-center gap-2"):
                    ui.span("Monthly Employment Change")
                    with ui.popover(placement="bottom"):
                        fa.icon_svg("circle-info", height="1.2em")
                        "Month-to-month percentage change. Values above zero indicate growth; below zero indicate decline."
                    with ui.span(class_="ms-auto"):

                        @render.download(
                            filename="monthly_employment.png",
                            media_type="image/png",
                            label=ui.span(
                                fa.icon_svg("download"),
                                title="Download as PNG",
                            ),
                        )
                        def dl_occ_employment():
                            yield export_fig(
                                build_employment_chart(
                                    occ_employment().to_pandas(),
                                    app_input.occ_occupation(),
                                    smooth=app_input.occ_smooth(),
                                ),
                            )

                @render_widget
                def occ_employment_chart():
                    df = occ_employment().to_pandas()
                    return build_employment_chart(
                        df,
                        app_input.occ_occupation(),
                        smooth=app_input.occ_smooth(),
                    )

            with ui.card(full_screen=True, height="700px"):
                with ui.card_header(class_="d-flex align-items-center gap-2"):
                    ui.span("AI Exposure by Sub-Domain")
                    with ui.popover(placement="bottom"):
                        fa.icon_svg("circle-info", height="1.2em")
                        "Each bar shows how this occupation ranks against all others for that AI sub-domain. Higher percentile = higher relative AI exposure."
                    with ui.span(class_="ms-auto"):

                        @render.download(
                            filename="ai_exposure.png",
                            media_type="image/png",
                            label=ui.span(
                                fa.icon_svg("download"),
                                title="Download as PNG",
                            ),
                        )
                        def dl_ai_bar():
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
                with ui.card_header(class_="d-flex align-items-center gap-2"):
                    ui.span("Employment (thousands)")
                    with ui.popover(placement="bottom"):
                        fa.icon_svg("circle-info", height="1.2em")
                        "Total national employment in thousands of people (all genders combined). Use 'Show gender lines' to overlay per-gender trends."
                    with ui.span(class_="ms-auto"):

                        @render.download(
                            filename="monthly_employment_count.png",
                            media_type="image/png",
                            label=ui.span(
                                fa.icon_svg("download"),
                                title="Download as PNG",
                            ),
                        )
                        def dl_occ_employment_count():
                            yield export_fig(
                                build_employment_count_chart(
                                    occ_employment().to_pandas(),
                                    app_input.occ_occupation(),
                                    smooth=app_input.occ_smooth(),
                                ),
                            )

                @render_widget
                def occ_employment_count_chart():
                    df = occ_employment().to_pandas()
                    return build_employment_count_chart(
                        df,
                        app_input.occ_occupation(),
                        smooth=app_input.occ_smooth(),
                    )

    # ── Tab 2: Comparison View ────────────────────────────────

    with ui.nav_panel("Compare Occupations"), ui.layout_sidebar():
        with ui.sidebar(title="Compare Occupations", width=280):
            ui.input_selectize(
                "comp_occupations",
                "Occupations",
                choices=OCC_CHOICES,
                multiple=True,
                options={"maxItems": 5, "placeholder": "Search occupation..."},
                selected=OCCS[:2],
            )
            ui.p(
                "Select up to five occupations to compare.",
                class_="text-muted small mt-n1 mb-2",
            )
            ui.input_select(
                "comp_gender",
                "Gender",
                choices=_GENDER_CHOICES,
                selected="All",
            )
            ui.input_select(
                "comp_year",
                "Year",
                choices={str(y): str(y) for y in YEARS},
                selected=str(YEAR_MAX),
            )
            ui.hr()
            ui.p("Trend filters:", class_="fw-semibold mb-1 small")
            ui.input_slider(
                "comp_year_range",
                "Employment date range",
                min=YEAR_MIN,
                max=YEAR_MAX,
                value=[max(YEAR_MIN, YEAR_MAX - 3), YEAR_MAX],
                sep="",
            )
            ui.input_checkbox(
                "comp_smooth",
                "Apply 3-month moving average",
                value=False,
            )

        # Employment summary table
        with ui.card(fill=True, fillable=True):
            ui.card_header("Occupations Summary")

            @render.ui
            def comp_summary_table():
                df = comp_summary_data()
                if df.is_empty():
                    return ui.p(
                        "Select up to five occupations from the sidebar to compare employment changes and AI exposure scores.",
                        class_="text-muted p-3",
                    )
                return ui.div(
                    as_great_table_html(df.to_pandas(), METRICS),
                    style="overflow: auto; width: 100%; height: 100%;",
                )

        # AI percentile radar chart
        with ui.card(full_screen=True, height="700px"):
            with ui.card_header(class_="d-flex align-items-center gap-2"):
                ui.span("AI Exposure Comparison (percentile rank)")
                with ui.popover(placement="bottom"):
                    fa.icon_svg("circle-info", height="1.2em")
                    "Each axis shows a percentile rank (0-100). Outer position = higher relative AI exposure than other occupations."
                with ui.span(class_="ms-auto"):

                    @render.download(
                        filename="ai_radar.png",
                        media_type="image/png",
                        label=ui.span(fa.icon_svg("download"), title="Download as PNG"),
                    )
                    def dl_comp_radar():
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
            with ui.card_header(class_="d-flex align-items-center gap-2"):
                ui.span("Monthly Employment Change")
                with ui.popover(placement="bottom"):
                    fa.icon_svg("circle-info", height="1.2em")
                    "1-month percentage change in employment for each selected occupation."
                with ui.span(class_="ms-auto"):

                    @render.download(
                        filename="comparison_employment.png",
                        media_type="image/png",
                        label=ui.span(fa.icon_svg("download"), title="Download as PNG"),
                    )
                    def dl_comp_employment():
                        yield export_fig(
                            build_comparison_employment_plot(
                                comparison_data().to_pandas(),
                                smooth=app_input.comp_smooth(),
                            ),
                        )

            @render_widget
            def comp_employment_chart():
                df = comparison_data().to_pandas()
                return build_comparison_employment_plot(
                    df,
                    smooth=app_input.comp_smooth(),
                )

        # Employment count comparison line chart
        with ui.card(full_screen=True, height="700px"):
            with ui.card_header(class_="d-flex align-items-center gap-2"):
                ui.span("Employment (thousands)")
                with ui.popover(placement="bottom"):
                    fa.icon_svg("circle-info", height="1.2em")
                    "Absolute monthly employment in thousands for each selected occupation."
                with ui.span(class_="ms-auto"):

                    @render.download(
                        filename="comparison_employment_count.png",
                        media_type="image/png",
                        label=ui.span(fa.icon_svg("download"), title="Download as PNG"),
                    )
                    def dl_comp_employment_count():
                        yield export_fig(
                            build_comparison_employment_count_plot(
                                comparison_data().to_pandas(),
                                smooth=app_input.comp_smooth(),
                            ),
                        )

            @render_widget
            def comp_employment_count_chart():
                df = comparison_data().to_pandas()
                return build_comparison_employment_count_plot(
                    df,
                    smooth=app_input.comp_smooth(),
                )

    # ── Tab 3: Download ───────────────────────────────────────

    with ui.nav_panel("Download Data"), ui.layout_sidebar():
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
                "Occupations",
                choices=OCC_CHOICES,
                multiple=True,
                options={"placeholder": "Leave empty to include all..."},
            )
            ui.p(
                "Leave empty to include all occupations.",
                class_="text-muted small mt-n1 mb-2",
            )
            ui.input_select(
                "dl_gender",
                "Gender",
                choices=_GENDER_CHOICES,
                selected="All",
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
            def download_data():
                df = download_frame().to_pandas()
                yield export_filtered_data(df, app_input.dl_format())

        ui.p(
            "Export row-level monthly occupation data including employment counts, percentage changes, and AI exposure scores. Use the sidebar to filter by year and occupation.",
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

    # ── Tab 4: About ─────────────────────────────────────────

    with ui.nav_panel("About"), ui.card(fill=True, fillable=True):
        ui.card_header("About This Dashboard")
        ui.div(
            ui.img(
                src="/logos/lab.svg",
                alt="AI-Econ Lab logo",
                style="height:60px; display:block; margin:1rem 0 1.5rem;",
            ),
        )
        ui.markdown(ABOUT_MD)


# ── Reactive calculations ─────────────────────────────────────


@reactive.calc
def occ_summary():
    return get_occ_summary(
        lf,
        app_input.occ_occupation(),
        int(app_input.occ_year()),
    )


@reactive.calc
def all_occ_summary():
    return get_all_occ_summary(lf, int(app_input.occ_year()))


@reactive.calc
def all_occ_ai():
    return get_all_occ_ai_exposure(lf, int(app_input.occ_year()))


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
        tuple(app_input.occ_gender()),
        smooth=app_input.occ_smooth(),
    )


@reactive.calc
def comp_summary_data():
    occs = list(app_input.comp_occupations() or [])
    if not occs:
        return pl.DataFrame()
    return get_comp_summary(
        lf, occs, int(app_input.comp_year()), app_input.comp_gender()
    )


@reactive.calc
def comparison_data():
    occs = list(app_input.comp_occupations() or [])
    if not occs:
        return pl.DataFrame()
    yr = app_input.comp_year_range()
    return get_comparison_employment(
        lf,
        occs,
        app_input.comp_gender(),
        (yr[0], yr[1]),
        smooth=app_input.comp_smooth(),
    )


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
    if app_input.dl_gender() != "All":
        q = q.filter(pl.col("gender") == app_input.dl_gender())
    return q.collect()
