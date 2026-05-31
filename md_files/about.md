This dashboard brings together monthly employment statistics from Statistics Sweden (SCB) and AI-exposure scores from the DAIOE framework to support research into how AI may be reshaping labour market outcomes across Swedish occupations.

---

### Data Sources

| Source | Description |
|---|---|
| [Labour Force Survey (AKU), SCB](https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__AM__AM0401__AM0401I/NAKUSysselYrke2012M/) | Monthly employment counts and changes by occupation and gender |
| [DAIOE Framework](https://www.ai-econlab.com/ai-exposure-daioe) | Data-driven AI Occupational Exposure scores across multiple AI capability sub-domains |

---

### Coverage

- **Geography**: Sweden (national totals)
- **Occupation level**: SSYK 2012 major groups (1-digit classification, 9 categories)
- **Time range**: {MONTH_EARLIEST} to {MONTH_LATEST}, updated monthly
- **Employment unit**: thousands of people (e.g. 150 = 150,000)

---

### Key Concepts

**SSYK 2012**
The Swedish Standard Classification of Occupations (2012 edition). Groups all occupations into 9 broad major categories based on skill level and field of work.

**DAIOE: AI Exposure Scores**
Data-driven AI Occupational Exposure scores quantify how strongly the tasks within an occupation may be affected by different AI capabilities. Scores are computed across multiple sub-domains (e.g. language, vision, reasoning) and aggregated as weighted averages at the occupation level.

**Percentile Rank**
Shows where an occupation sits relative to all others on a given sub-domain. A percentile rank of 80 means the occupation scores higher than 80% of all occupations; it is a relative, not absolute, measure.

**Exposure Level**
An ordinal scale from 1 (Very Low) to 5 (Very High) summarising the weighted-average AI exposure score for a sub-domain. Used for quick comparisons; the underlying index score provides more precision.

**Employment Change**
Month-to-month or multi-month percentage change computed from absolute employment counts. Positive values indicate growth; negative values indicate decline. Changes are computed from aggregated employment counts and absolute changes, not by averaging gender-specific percentage rates.

---

### Caveats

- AI exposure measures potential task-level exposure to AI capabilities. It is not a prediction of employment decline, job loss, or automation outcomes.
- Month-to-month employment changes are volatile and may reflect seasonal patterns, survey revisions, or reclassifications unrelated to AI adoption.
- Percentile ranks are relative to other occupations in the dataset. A high rank does not imply a high absolute exposure score, and rankings may shift as new occupations or years are added.
- SSYK 2012 major groups are broad; occupations within a group can vary considerably in their actual AI exposure.

---

### About the Project

This tool is developed by the [AI-Econ Lab](https://www.ai-econlab.com) as part of ongoing research into the intersection of artificial intelligence and labour markets. For questions or collaboration enquiries, please visit [ai-econlab.com](https://www.ai-econlab.com).
