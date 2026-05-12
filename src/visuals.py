import faicons as fa
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from shiny import ui

SCB_SOURCE_MD = (
    "Source: [Swedish Occupational Register, SCB]"
    "(https://www.scb.se/en/finding-statistics/statistics-by-subject-area/"
    "labour-market/labour-force-supply/"
    "the-swedish-occupational-register-with-statistics/)"
)

DAIOE_SOURCE_MD = "Source: [DAIOEs](https://www.ai-econlab.com/ai-exposure-daioe)"

# Brand colours from _brand.yml
_C_BG = "rgba(0,0,0,0)"
_C_GRID = "#E5E5E5"
_C_TEXT = "#1C2826"  # black
_C_TITLE = "#0C0A3E"  # primary / blue

_FONT_BASE = "Nunito Sans"
_FONT_HEAD = "Montserrat"

_BASE_LAYOUT = {
    "paper_bgcolor": _C_BG,
    "plot_bgcolor": _C_BG,
    "font": {"family": _FONT_BASE, "color": _C_TEXT, "size": 13},
    "title_font": {"family": _FONT_HEAD, "color": _C_TITLE, "size": 15},
    "hoverlabel": {"font": {"family": _FONT_BASE, "size": 12}},
    "margin": {"l": 20, "r": 20, "t": 45, "b": 20},
}


def build_value_boxes(summary: dict, occupation: str) -> ui.Tag:
    """
    Build the employment summary value boxes for a given occupation.

    Returns a div containing a heading, four value boxes (employment,
    1/3/6-month change), and a markdown source note.
    """

    def _arrow(v):
        return "▼" if v < 0 else "▲"

    def _theme(v):
        return "danger" if v < 0 else "success"

    def _fmt_pct(v):
        return f"{_arrow(v)} {v:.0f}%" if v is not None else "N/A"

    def _fmt_theme(v):
        return _theme(v) if v is not None else "secondary"

    emp = summary["employment"]
    pct1 = summary["pct_1m"]
    pct3 = summary["pct_3m"]
    pct6 = summary["pct_6m"]
    year = summary["year"]

    return ui.div(
        ui.h6(f"National Employment of {occupation}", class_="mt-3 mb-2 fw-semibold"),
        ui.layout_columns(
            ui.value_box(
                title="Avg Monthly Employment",
                showcase=fa.icon_svg("users"),
                value=f"{emp:,.0f}",
                theme="primary",
            ),
            ui.value_box(
                title="1-month change",
                value=_fmt_pct(pct1),
                showcase=fa.icon_svg("arrow-trend-up" if pct1 is None or pct1 >= 0 else "arrow-trend-down"),
                theme=_fmt_theme(pct1),
            ),
            ui.value_box(
                title="3-month change",
                value=_fmt_pct(pct3),
                showcase=fa.icon_svg("arrow-trend-up" if pct3 is None or pct3 >= 0 else "arrow-trend-down"),
                theme=_fmt_theme(pct3),
            ),
            ui.value_box(
                title="6-month change",
                value=_fmt_pct(pct6),
                showcase=fa.icon_svg("arrow-trend-up" if pct6 is None or pct6 >= 0 else "arrow-trend-down"),
                theme=_fmt_theme(pct6),
            ),
            col_widths=[3, 3, 3, 3],
        ),
        ui.markdown(f"Average monthly employment as at **{year}**.\n\n{SCB_SOURCE_MD}"),
    )


def build_sex_chart(df: pd.DataFrame, occupation: str) -> go.Figure:
    """
    Build a Plotly line chart of monthly employment count by sex over time.

    Returns an empty figure if df is empty.
    """
    if df.empty:
        return go.Figure()

    df = df.fillna(0)

    # Sort months chronologically for the x-axis
    sorted_months = sorted(df["month"].unique(), key=lambda m: pd.to_datetime(m, format="%Y-%b"))

    fig = px.line(
        df,
        x="month",
        y="emp_count",
        color="sex",
        markers=True,
        custom_data=["pct_chg_1m"],
        labels={
            "month": "Month",
            "emp_count": "Employment",
            "sex": "Sex",
        },
        category_orders={"month": sorted_months},
    )
    fig.update_traces(
        hovertemplate=(
            "<b>%{fullData.name}</b><br>"
            "Month: %{x}<br>"
            "Employment: %{y:,.0f}<br>"
            "1-mo Change: %{customdata[0]:.1f}%<extra></extra>"
        ),
    )
    fig.update_layout(
        **_BASE_LAYOUT,
        title={
            "text": f"Monthly Employment of {occupation} in Sweden",
            "x": 0.01,
            "xanchor": "left",
        },
        legend={"title": None},
    )
    fig.update_xaxes(gridcolor=_C_GRID, zeroline=False, tickangle=-45)
    fig.update_yaxes(gridcolor=_C_GRID, zeroline=False)
    return fig


def build_comparison_employment_plot(df: pd.DataFrame) -> go.Figure:
    """Build a line chart comparing monthly employment % change across selected occupations."""
    if df.empty:
        return go.Figure()

    df = df.fillna(0)

    sorted_months = sorted(df["month"].unique(), key=lambda m: pd.to_datetime(m, format="%Y-%b"))

    fig = px.line(
        df,
        x="month",
        y="pct_chg_1m",
        color="occupation",
        markers=True,
        custom_data=["emp_count"],
        labels={"pct_chg_1m": "Employment Change (%)", "month": "Month"},
        category_orders={"month": sorted_months},
    )
    fig.update_traces(
        hovertemplate=(
            "<b>%{fullData.name}</b><br>"
            "Month: %{x}<br>"
            "Change: %{y:.1f}%<br>"
            "Employment: %{customdata[0]:,.0f}<extra></extra>"
        ),
    )
    fig.add_hline(y=0, line_color="grey", line_width=1)
    fig.update_layout(
        **_BASE_LAYOUT,
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": -0.35,
            "xanchor": "center",
            "x": 0.5,
            "title": None,
        },
        yaxis={"ticksuffix": "%"},
    )
    fig.update_xaxes(gridcolor=_C_GRID, zeroline=False, tickangle=-45)
    fig.update_yaxes(gridcolor=_C_GRID, zeroline=False)
    return fig


def build_comp_radar_plot(df: pd.DataFrame, metrics: dict[str, str]) -> go.Figure:
    """Build a radar chart comparing AI percentile scores across selected occupations."""
    if df.empty:
        return go.Figure()

    df = df.fillna(0)

    categories = list(metrics.values())
    fig = go.Figure()

    for _, row in df.iterrows():
        r_values = [row[f"pctl_{k}_wavg"] for k in metrics]
        r_values_closed = [*r_values, r_values[0]]
        categories_closed = [*categories, categories[0]]

        fig.add_trace(go.Scatterpolar(
            r=r_values_closed,
            theta=categories_closed,
            fill="toself",
            name=row["occupation"],
            hovertemplate="%{theta}: %{r:.1f}%<extra></extra>",
        ))

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


def build_ai_exposure_bar(df: pd.DataFrame, occupation: str, year: int) -> go.Figure:
    """
    Build a horizontal bar chart of AI exposure per sub-domain.

    X-axis: percentile rank (0-100).
    Y-axis: AI sub-domains with emoji labels, sorted by score ascending.
    Bar colour intensity driven by percentile rank.
    Hover shows exposure level label, index score, and percentile rank.
    """
    if df.empty:
        return go.Figure()

    df = df.fillna({"score": 0.0, "level": 0, "percentile": 0.0})

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
                zip(df["level_label"], df["level"], df["score"], strict=False)
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
