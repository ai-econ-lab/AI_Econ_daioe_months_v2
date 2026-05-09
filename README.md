---
title: Monthly Employed Persons by Occupation and DAIOEs
emoji: 🌍
colorFrom: yellow
colorTo: indigo
sdk: docker
pinned: false
license: mit
---

# Monthly Employed Persons by Occupation and DAIOEs

![AI-Econ Lab logo](logos/lab.svg)

## Overview

This repository builds and deploys **AI Exposure & Employment Dashboard** — a Shiny app
for exploring monthly Swedish employment by occupation alongside DAIOE measures of AI
exposure. The app is packaged with Docker and syncs to Hugging Face Spaces from the
`main` branch.

The dashboard reads `data/scb_months_lvl1.parquet`, filters observations by year, sex,
occupation, AI exposure metric, and employment-change horizon, then shows summary value
boxes (average AI exposure, median employment change, observation count), a Plotly
scatter plot with an OLS trendline, and a filterable data table.

## Runtime Files

The deployable app is intentionally small:

- `app.py` defines the Shiny Express app.
- `_brand.yml` defines the Shiny theme and points to the lab logo.
- `logos/lab.svg` is shown in the app sidebar and README.
- `data/scb_months_lvl1.parquet` is the app dataset.
- `Dockerfile`, `.dockerignore`, `pyproject.toml`, and `uv.lock` define the containerized runtime.

## Dependencies

Key Python packages (see `pyproject.toml` for pinned versions):

| Package | Purpose |
| --- | --- |
| `shiny[theme]` | Shiny for Python web framework |
| `shinywidgets` | Plotly widget integration |
| `plotly` | Interactive scatter plots |
| `polars` | Fast dataframe operations |
| `pandas` | DataFrame conversion for Plotly |
| `pyarrow` | Parquet file I/O |
| `statsmodels` | OLS trendline in scatter plot |

Requires **Python ≥ 3.14**.

## Local Development

Install dependencies with `uv`:

```bash
uv sync
```

Run the app locally:

```bash
uv run shiny run app.py --reload
```

Or run with the project virtual environment directly:

```bash
.venv/bin/python -m shiny run app.py --reload
```

## Docker

Build the image:

```bash
docker build -t ai-econ-daioe-months .
```

Run it locally:

```bash
docker run --rm -p 7860:7860 ai-econ-daioe-months
```

The container serves the app on `http://127.0.0.1:7860`.

## Branch Workflow

This repository uses separate branches for each stage of the data and deployment
pipeline.

| Branch | Purpose | Main output |
| --- | --- | --- |
| `scb_pull` | Pulls or prepares the monthly SCB employment data. The `SCB Pull -> DAIOE Pull` workflow runs `main.py` on this branch. | `data/scb_months.parquet` |
| `daioe_pull` | Receives the SCB output and enriches or merges it with DAIOE exposure data. The `DAIOE Pull -> Development` workflow runs `main.py` here. | `data/scb_months_lvl1.parquet` |
| `development` | Integration branch for the merged dataset and deployable app files before promotion. The `Development -> Main` workflow promotes the deploy bundle from here. | deploy-ready app files |
| `main` | Production/deployment branch. This branch contains the Dockerized Shiny app and syncs to Hugging Face Spaces. | running dashboard |

The pipeline is therefore:

```text
scb_pull -> daioe_pull -> development -> main -> Hugging Face Spaces
```

## GitHub Actions

The repository contains four workflows:

- `.github/workflows/01_scb_pull_to_daioe_pull.yml` builds the base SCB parquet and pushes it to `daioe_pull`.
- `.github/workflows/02_daioe_pull_to_development.yml` builds the DAIOE-enriched parquet and pushes it to `development`.
- `.github/workflows/03_development_to_main.yml` promotes deployable app files to `main`.
- `.github/workflows/sync_to_hub.yml` syncs `main` to the Hugging Face Space `joseph-data/app_months`.

The scheduled workflows run daily at `00:00 UTC`, and each can also be run manually
with `workflow_dispatch`.

## Data Shape

The app dataset (`data/scb_months_lvl1.parquet`) has monthly occupation-level rows with:

- `year`, `month`, `sex`, `occupation`, `emp_count` — dimensions and employment count
- `pct_chg_1m`, `pct_chg_3m`, `pct_chg_6m` — percentage employment change over 1, 3, and 6 months

DAIOE weighted-average exposure columns (`daioe_*_wavg`) used as x-axis metrics:

| Column | Label |
| --- | --- |
| `daioe_allapps_wavg` | All AI Applications |
| `daioe_stratgames_wavg` | Strategic Games |
| `daioe_videogames_wavg` | Video Games |
| `daioe_imgrec_wavg` | Image Recognition |
| `daioe_imgcompr_wavg` | Image Compression |
| `daioe_imggen_wavg` | Image Generation |
| `daioe_readcompr_wavg` | Reading Comprehension |
| `daioe_lngmod_wavg` | Language Models |
| `daioe_translat_wavg` | Translation |
| `daioe_speechrec_wavg` | Speech Recognition |
| `daioe_genai_wavg` | Generative AI |
