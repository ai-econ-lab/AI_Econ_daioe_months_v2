"""Domain constants shared across calcs, visuals, and utils."""

METRICS: dict[str, str] = {
    "daioe_genai": "🧠 Generative AI",
    "daioe_allapps": "📚 All Applications",
    "daioe_stratgames": "♟️ Strategy Games",
    "daioe_videogames": "🎮 Video Games",
    "daioe_imgrec": "🖼️ Image Recognition",
    "daioe_imgcompr": "🧩 Image Comprehension",
    "daioe_imggen": "🎨 Image Generation",
    "daioe_readcompr": "📖 Reading Comprehension",
    "daioe_lngmod": "✍️ Language Modeling",
    "daioe_translat": "🌐 Translation",
    "daioe_speechrec": "🎙️ Speech Recognition",
}

AI_WAVG_COLS: list[str] = [
    "daioe_genai_wavg",
    "daioe_allapps_wavg",
    "daioe_stratgames_wavg",
    "daioe_videogames_wavg",
    "daioe_imgrec_wavg",
    "daioe_imgcompr_wavg",
    "daioe_imggen_wavg",
    "daioe_readcompr_wavg",
    "daioe_lngmod_wavg",
    "daioe_translat_wavg",
    "daioe_speechrec_wavg",
]

AI_LABELS: dict[str, str] = {f"{k}_wavg": v for k, v in METRICS.items()}

AI_LEVEL_COLS: list[str] = [c.replace("_wavg", "_Level_Exposure") for c in AI_WAVG_COLS]
AI_PCTL_COLS: list[str] = [f"pctl_{c}" for c in AI_WAVG_COLS]

EXPOSURE_LABELS: dict[int, str] = {
    1: "Very Low",
    2: "Low",
    3: "Medium",
    4: "High",
    5: "Very High",
}

FIRST_COLS: list[str] = [
    "code_1",
    "occupation",
    "year",
    "month",
    "gender",
    "emp_count",
    "weight_sum",
    "chg_1m",
    "chg_3m",
    "chg_6m",
    "pct_chg_1m",
    "pct_chg_3m",
    "pct_chg_6m",
]
