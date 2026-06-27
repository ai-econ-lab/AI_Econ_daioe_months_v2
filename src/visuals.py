from __future__ import annotations

import contextlib
import copy
import re
from typing import TYPE_CHECKING

import faicons as fa
import polars as pl
from shiny import ui

if TYPE_CHECKING:
    import pandas as pd
    import plotly.graph_objects as go

SCB_SOURCE_MD = (
    "Source: [Swedish Occupational Register, SCB]"
    "(https://www.scb.se/en/finding-statistics/statistics-by-subject-area/"
    "labour-market/labour-force-supply/"
    "the-swedish-occupational-register-with-statistics/)"
)

DAIOE_SOURCE_MD = "Source: [DAIOEs](https://www.ai-econlab.com/ai-exposure-daioe)"

_EMOJI_PREFIX = re.compile(r"^[^\x00-\x7F]+\s*")

# Brand colours from _brand.yml
_C_BG = "rgba(0,0,0,0)"
_C_GRID = "#E5E5E5"
_C_TEXT = "#1C2826"
_C_TITLE = "#0C0A3E"

_FONT_BASE = "Nunito Sans"
_FONT_HEAD = "Montserrat"


def _nullify(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Replace NaN with Python None in specified columns so Plotly serialises them as JSON null."""
    df = df.copy()
    for col in cols:
        if col in df.columns:
            df[col] = df[col].astype(object).where(df[col].notna(), None)
    return df


_BASE_LAYOUT: dict = {
    "paper_bgcolor": _C_BG,
    "plot_bgcolor": _C_BG,
    "font": {"family": _FONT_BASE, "color": _C_TEXT, "size": 13},
    "title_font": {"family": _FONT_HEAD, "color": _C_TITLE, "size": 15},
    "hoverlabel": {"font": {"family": _FONT_BASE, "size": 12}},
    "margin": {"l": 20, "r": 20, "t": 45, "b": 20},
}


def _empty_figure() -> go.Figure:
    """Return a blank figure with a centered 'No data available' annotation."""
    import plotly.graph_objects as go

    fig = go.Figure()
    fig.add_annotation(
        text="No data available",
        showarrow=False,
        font={"size": 16, "color": "#999"},
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
    )
    fig.update_layout(**_BASE_LAYOUT)
    return fig


def _apply_xaxes(fig: go.Figure) -> None:
    fig.update_xaxes(
        gridcolor=_C_GRID,
        zeroline=False,
        tickangle=-45,
        tickformat="%b %Y",
        dtick="M3",
    )


def _apply_yaxes(fig: go.Figure) -> None:
    fig.update_yaxes(gridcolor=_C_GRID, zeroline=False)


def _hlegend() -> dict:
    return {
        "orientation": "h",
        "yanchor": "bottom",
        "y": -0.35,
        "xanchor": "center",
        "x": 0.5,
        "title": None,
    }


def build_value_boxes(summary: pl.DataFrame, occupation: str) -> ui.Tag:
    """
    Build the employment summary value boxes for a given occupation.

    Returns a div containing a heading, three value boxes (employment count,
    1-month change, 3-month change), and a markdown source note.
    """

    def _arrow(v: float) -> str:
        return "▼" if v < 0 else "▲"

    def _theme(v: float) -> str:
        return "danger" if v < 0 else "success"

    def _fmt_pct(v: float | None) -> str:
        return f"{_arrow(v)} {v:.0f}%" if v is not None else "N/A"

    def _fmt_theme(v: float | None) -> str:
        return _theme(v) if v is not None else "secondary"

    row = summary.row(0, named=True)
    emp = row["emp_count"]
    pct1 = row["pct_chg_1m"]
    pct3 = row["pct_chg_3m"]
    month = row["month"]

    return ui.div(
        ui.h6(
            f"National Employment of {occupation} (All Genders)",
            class_="mt-3 mb-2 fw-semibold",
        ),
        ui.layout_columns(
            ui.value_box(
                title="Employment ('000)",
                showcase=fa.icon_svg("users"),
                value=f"{emp:,.0f}",
                theme="primary",
            ),
            ui.value_box(
                title="1-month change",
                value=_fmt_pct(pct1),
                showcase=fa.icon_svg(
                    "arrow-trend-up"
                    if pct1 is None or pct1 >= 0
                    else "arrow-trend-down",
                ),
                theme=_fmt_theme(pct1),
            ),
            ui.value_box(
                title="3-month change",
                value=_fmt_pct(pct3),
                showcase=fa.icon_svg(
                    "arrow-trend-up"
                    if pct3 is None or pct3 >= 0
                    else "arrow-trend-down",
                ),
                theme=_fmt_theme(pct3),
            ),
            col_widths=[4, 4, 4],
        ),
        ui.markdown(f"Employment count as at **{month}**.\n\n{SCB_SOURCE_MD}"),
    )


def build_employment_count_chart(
    df: pd.DataFrame,
    occupation: str,
    *,
    smooth: bool = False,
) -> go.Figure:
    """
    Build a Plotly line chart of total monthly employment count over time.

    1-month % change is shown on hover. When df contains multiple gender series,
    each is drawn as a separate coloured line. Returns an empty figure if df is empty.
    """
    import pandas as pd

    import plotly.express as px

    if df.empty:
        return _empty_figure()

    multi_gender = "gender" in df.columns and df["gender"].nunique() > 1  # noqa: PD101

    df = df.assign(
        pct_chg_1m_label=df["pct_chg_1m"].map(
            lambda v: f"{v:.1f}%" if pd.notna(v) else "N/A",
        ),
        _date=pd.to_datetime(df["month"], format="%Y-%b"),
    ).sort_values(["gender", "_date"] if multi_gender else "_date")
    df = _nullify(df, ["emp_count"])

    fig = px.line(
        df,
        x="_date",
        y="emp_count",
        color="gender" if multi_gender else None,
        markers=True,
        custom_data=["pct_chg_1m_label", "month"],
        labels={"_date": "Month", "emp_count": "Employment", "gender": "Gender"},
    )
    fig.update_traces(
        line={"width": 3},
        marker={"size": 8},
        hovertemplate=(
            "Month: %{customdata[1]}<br>"
            "Employment: %{y:,.0f}<br>"
            "1-mo Change: %{customdata[0]}<extra></extra>"
        ),
    )
    title_suffix = " (3-Month Moving Average)" if smooth else ""
    fig.update_layout(
        **_BASE_LAYOUT,
        title={
            "text": f"Monthly Employment of {occupation} in Sweden{title_suffix}",
            "x": 0.01,
            "xanchor": "left",
        },
        showlegend=multi_gender,
        **({"legend": _hlegend()} if multi_gender else {}),
    )
    _apply_xaxes(fig)
    _apply_yaxes(fig)
    return fig


def build_employment_chart(
    df: pd.DataFrame,
    occupation: str,
    *,
    smooth: bool = False,
) -> go.Figure:
    """
    Build a Plotly line chart of total 1-month employment % change over time.

    Absolute employment count is shown on hover. When df contains multiple gender
    series, each is drawn as a separate coloured line. Returns an empty figure if
    df is empty.
    """
    import pandas as pd

    import plotly.express as px

    if df.empty:
        return _empty_figure()

    multi_gender = "gender" in df.columns and df["gender"].nunique() > 1  # noqa: PD101

    df = _nullify(df, ["pct_chg_1m"])
    df = df.assign(
        emp_count_label=df["emp_count"].map(
            lambda v: f"{v:,.0f}" if pd.notna(v) else "N/A",
        ),
        _date=pd.to_datetime(df["month"], format="%Y-%b"),
    ).sort_values(["gender", "_date"] if multi_gender else "_date")

    fig = px.line(
        df,
        x="_date",
        y="pct_chg_1m",
        color="gender" if multi_gender else None,
        markers=True,
        custom_data=["emp_count_label", "month"],
        labels={
            "_date": "Month",
            "pct_chg_1m": "Employment change (%)",
            "gender": "Gender",
        },
    )
    fig.update_traces(
        line={"width": 3},
        marker={"size": 8},
        hovertemplate=(
            "Month: %{customdata[1]}<br>"
            "Change: %{y:.1f}%<br>"
            "Employment: %{customdata[0]}<extra></extra>"
        ),
        connectgaps=True,
    )
    fig.add_hline(y=0, line_color="grey", line_width=1)
    title_suffix = " (3-Month Moving Average)" if smooth else ""
    fig.update_layout(
        **_BASE_LAYOUT,
        title={
            "text": f"Monthly Employment Change of {occupation} in Sweden{title_suffix}",
            "x": 0.01,
            "xanchor": "left",
        },
        yaxis={"ticksuffix": "%"},
        showlegend=multi_gender,
        **({"legend": _hlegend()} if multi_gender else {}),
    )
    _apply_xaxes(fig)
    _apply_yaxes(fig)
    return fig


def build_comparison_employment_plot(
    df: pd.DataFrame,
    *,
    smooth: bool = False,
) -> go.Figure:
    """Build a line chart comparing 1-month employment % change across selected occupations."""
    import pandas as pd
    import plotly.express as px

    if df.empty:
        return _empty_figure()

    df = _nullify(df, ["pct_chg_1m"])
    df = df.assign(
        emp_count_label=df["emp_count"].map(
            lambda v: f"{v:,.0f}" if pd.notna(v) else "N/A",
        ),
        _date=pd.to_datetime(df["month"], format="%Y-%b"),
    ).sort_values(["occupation", "_date"])

    fig = px.line(
        df,
        x="_date",
        y="pct_chg_1m",
        color="occupation",
        markers=True,
        custom_data=["emp_count_label", "month"],
        labels={"pct_chg_1m": "Employment Change (%)", "_date": "Month"},
    )
    fig.update_traces(
        line={"width": 3},
        marker={"size": 8},
        hovertemplate=(
            "<b>%{fullData.name}</b><br>"
            "Month: %{customdata[1]}<br>"
            "Change: %{y:.1f}%<br>"
            "Employment: %{customdata[0]}<extra></extra>"
        ),
        connectgaps=True,
    )
    fig.add_hline(y=0, line_color="grey", line_width=1)
    title_suffix = " (3-Month Moving Average)" if smooth else ""
    fig.update_layout(
        **_BASE_LAYOUT,
        title={
            "text": f"Monthly Employment Change by Occupation in Sweden{title_suffix}",
            "x": 0.01,
            "xanchor": "left",
        },
        legend=_hlegend(),
        yaxis={"ticksuffix": "%"},
    )
    _apply_xaxes(fig)
    _apply_yaxes(fig)
    return fig


def build_comparison_employment_count_plot(
    df: pd.DataFrame,
    *,
    smooth: bool = False,
) -> go.Figure:
    """Build a line chart comparing absolute monthly employment counts across selected occupations."""
    import pandas as pd
    import plotly.express as px

    if df.empty:
        return _empty_figure()

    df = df.assign(
        pct_chg_1m_label=df["pct_chg_1m"].map(
            lambda v: f"{v:.1f}%" if pd.notna(v) else "N/A",
        ),
        _date=pd.to_datetime(df["month"], format="%Y-%b"),
    ).sort_values(["occupation", "_date"])
    df = _nullify(df, ["emp_count"])

    title_suffix = " (3-Month Moving Average)" if smooth else ""
    fig = px.line(
        df,
        x="_date",
        y="emp_count",
        color="occupation",
        markers=True,
        custom_data=["pct_chg_1m_label", "month"],
        labels={"emp_count": "Employment ('000)", "_date": "Month"},
    )
    fig.update_traces(
        line={"width": 3},
        marker={"size": 8},
        hovertemplate=(
            "<b>%{fullData.name}</b><br>"
            "Month: %{customdata[1]}<br>"
            "Employment: %{y:,.0f}<br>"
            "1-mo Change: %{customdata[0]}<extra></extra>"
        ),
    )
    fig.update_layout(
        **_BASE_LAYOUT,
        title={
            "text": f"Monthly Employment by Occupation in Sweden{title_suffix}",
            "x": 0.01,
            "xanchor": "left",
        },
        legend=_hlegend(),
    )
    _apply_xaxes(fig)
    _apply_yaxes(fig)
    return fig


def build_comp_radar_plot(df: pd.DataFrame, metrics: dict[str, str]) -> go.Figure:
    """Build a radar chart comparing AI percentile scores across selected occupations."""
    import plotly.graph_objects as go

    if df.empty:
        return _empty_figure()

    pctl_cols = [f"pctl_{k}_wavg" for k in metrics]
    df = _nullify(df, pctl_cols)

    categories = list(metrics.values())
    fig = go.Figure()

    for row in df.to_dict("records"):
        r_values = [row[f"pctl_{k}_wavg"] for k in metrics]
        r_values_closed = [*r_values, r_values[0]]
        categories_closed = [*categories, categories[0]]

        fig.add_trace(
            go.Scatterpolar(
                r=r_values_closed,
                theta=categories_closed,
                fill="toself",
                name=row["occupation"],
                hovertemplate="%{theta}: %{r:.1f}%<extra></extra>",
            ),
        )

    fig.update_layout(
        **_BASE_LAYOUT,
        polar={"radialaxis": {"visible": True, "range": [0, 100]}},
        showlegend=True,
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": -0.25,
            "xanchor": "center",
            "x": 0.5,
        },
    )
    return fig


def build_ai_exposure_bar(
    df: pd.DataFrame,
    occupation: str,
    year: int,
) -> go.Figure:
    """
    Build a horizontal bar chart of AI exposure level per sub-domain.

    Bar colour intensity is driven by the percentile rank score.
    Hover shows exposure level label, index score, and percentile rank.
    """
    import plotly.graph_objects as go

    if df.empty:
        return _empty_figure()

    df = _nullify(df, ["score", "level", "percentile"])

    fig = go.Figure(
        go.Bar(
            x=df["percentile"],
            y=df["domain"],
            orientation="h",
            marker={
                "color": df["percentile"],
                "colorscale": "Blues",
                "colorbar": {"title": "Percentile Rank"},
                "showscale": True,
                "cmin": 0,
                "cmax": 100,
            },
            customdata=list(
                zip(df["level_label"], df["level"], df["score"], strict=False),
            ),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Percentile Rank: %{x:.0f}<br>"
                "Exposure Level: %{customdata[0]} (%{customdata[1]}/5)<br>"
                "Index Score: %{customdata[2]:.3f}<extra></extra>"
            ),
        ),
    )
    fig.update_layout(
        **_BASE_LAYOUT,
        title={
            "text": f"{occupation} Level of AI Exposure ({year})",
            "x": 0.01,
            "xanchor": "left",
        },
        xaxis={"title": "Percentile Rank", "range": [0, 100]},
        yaxis={"title": None},
    )
    fig.update_xaxes(gridcolor=_C_GRID, zeroline=False)
    fig.update_yaxes(gridcolor=_C_GRID, zeroline=False)
    return fig


def _strip_emoji(val: object) -> object:
    if isinstance(val, str):
        return _EMOJI_PREFIX.sub("", val)
    if isinstance(val, (list, tuple)):
        stripped = [_EMOJI_PREFIX.sub("", v) if isinstance(v, str) else v for v in val]
        return type(val)(stripped)
    return val


_kaleido_started = False


def export_fig(fig: go.Figure, width: int = 1000, height: int = 650) -> bytes:
    """Return PNG bytes of a figure with a solid white background and no emoji labels."""
    global _kaleido_started
    if not _kaleido_started:
        import kaleido

        kaleido.start_sync_server(silence_warnings=True)
        _kaleido_started = True
    fig = copy.deepcopy(fig)
    for trace in fig.data:
        for field in ("y", "x", "theta", "text", "name"):
            val = getattr(trace, field, None)
            if val is not None:
                with contextlib.suppress(AttributeError, TypeError):
                    trace.update({field: _strip_emoji(val)})  # type: ignore[union-attr]
    is_polar = any(getattr(t, "type", "") == "scatterpolar" for t in fig.data)
    fig.update_layout(paper_bgcolor="white", plot_bgcolor="white")
    if is_polar:
        fig.update_layout(polar_bgcolor="white")
    return fig.to_image(format="png", scale=2, width=width, height=height)
