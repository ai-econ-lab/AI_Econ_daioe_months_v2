---
title: DAIOE Monthly Explorer
emoji: 🤖
colorFrom: indigo
colorTo: blue
sdk: docker
app_file: app.py
pinned: false
---

# DAIOE Monthly Explorer: Swedish Occupations

An interactive dashboard that brings together monthly employment statistics from Statistics Sweden (SCB) and AI-exposure scores from the DAIOE framework. Built to support research into how AI may be reshaping labour market outcomes across Swedish occupations.

## Features

**Single Occupation**
Inspect one occupation at a time. View a scrolling ribbon of all occupations, employment value boxes (all-sexes aggregate), an AI exposure bar chart ranked by percentile across sub-domains, a monthly employment change line chart, and an absolute employment count chart. An optional sex breakdown overlays per-sex lines on the employment charts.

**Compare Occupations**
Select up to five occupations side by side. Includes a summary table with employment and percentage changes, a radar chart comparing AI percentile scores across sub-domains, and a combined employment change line chart.

**Download Data**
Filter by year range, occupation, and sex, then export the underlying row-level data as CSV, Parquet, or Excel.

**About**
Data sources, key concept definitions, coverage details, and caveats.

## Data Sources

| Source | Description |
| --- | --- |
| [Swedish Occupational Register, SCB](https://www.scb.se/en/finding-statistics/statistics-by-subject-area/labour-market/labour-force-supply/the-swedish-occupational-register-with-statistics/) | Monthly employment counts and changes by occupation and sex |
| [DAIOE Framework](https://www.ai-econlab.com/ai-exposure-daioe) | Data-driven AI Occupational Exposure scores across multiple AI capability sub-domains |

**Coverage:** Sweden, SSYK 2012 major groups (1-digit, 9 categories), updated monthly.

## Tech Stack

- **[Shiny for Python](https://shiny.posit.co/py/)** (Express syntax) for the interactive UI
- **[Polars](https://pola.rs/)** for all data wrangling via lazy evaluation
- **[Plotly](https://plotly.com/python/)** for interactive charts
- **[Great Tables](https://posit-dev.github.io/great-tables/)** for styled summary tables
- **[uv](https://github.com/astral-sh/uv)** for dependency management
- **Docker** for containerised deployment on Hugging Face Spaces

## Local Development

```bash
# Install dependencies
uv sync

# Run the app with auto-reload
uv run shiny run app.py --reload

# Lint and format
uv tool run ruff check src/ app.py
uv tool run ruff format src/ app.py

# Build and run the Docker image
docker build -t ai-econ-daioe-months .
docker run --rm -p 7860:7860 ai-econ-daioe-months
```

## Project Structure

```
app.py                          # Shiny Express app (UI + reactive graph)
src/
  data.py                       # Parquet scan, input choices, markdown loading
  constants.py                  # METRICS dict, AI column lists, exposure labels
  calcs.py                      # Pure Polars query functions (no UI)
  visuals.py                    # Plotly figure builders and value box renderer
  utils.py                      # Great Tables rendering and download helpers
css/
  ticker.css                    # Occupation ribbon / ticker styles
data/
  scb_months_lvl1.parquet       # Runtime dataset (auto-updated by CI)
md_files/
  intro.md                      # Sidebar intro text
  about.md                      # About tab content
.github/workflows/              # CI pipeline (see below)
```

## CI Pipeline

```
scb_pull -> daioe_pull -> development -> main -> Hugging Face Spaces
```

Each stage runs on push, daily cron at 00:00 UTC, or manual `workflow_dispatch`.

| Stage | Workflow | What it does |
| --- | --- | --- |
| `scb_pull` | `01_scb_pull_to_daioe_pull.yml` | Fetches SCB employment data, produces `scb_months.parquet`, commits to `daioe_pull` |
| `daioe_pull` | `02_daioe_pull_to_development.yml` | Merges DAIOE AI-exposure scores, produces `scb_months_lvl1.parquet`, commits to `development` |
| `development` | `03_development_to_main.yml` | Validates and promotes all deploy files to `main` |
| `main` | `sync_to_hub.yml` | Syncs `main` to the Hugging Face Space, triggering a Docker rebuild |

## About the Project

Developed by the [AI-Econ Lab](https://www.ai-econlab.com) as part of ongoing research into the intersection of artificial intelligence and labour markets.
