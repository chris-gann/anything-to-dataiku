---
name: migration-report
description: "Use at the end of every source→Dataiku migration (Alteryx, Jupyter, Excel, SAS). Generates a detailed markdown report covering what was migrated, how it works, and the reasoning behind each design decision, then publishes it to the project wiki. This is the definition of done for any migration."
---

# Migration Report

The migration report is the **final, required step** of every migration performed by this plugin. It captures not just *what* was built, but *why* it was built that way — the consolidation choices, the visual-vs-Python decisions, the naming rationale, and any lossy translations. A future reader (or future Claude) should be able to understand and maintain the migrated flow from the report alone.

## When to run

Only AFTER `jobs.build_and_wait(...)` succeeds on the terminal datasets. Do not generate a report for a failed or partial migration — fix the migration first.

## Where it goes

Publish as a wiki article in the project Claude just created. Use the `wikis` skill for the API mechanics — do not reimplement.

- **Article name:** `Migration Report — <source-filename>` (e.g. `Migration Report — sales-forecast.xlsx`).
- **Home article:** if the project wiki is empty (the common case for a just-created migration project), set this article as the home article. If the wiki already has a home article, leave it alone and just add this as a top-level article.
- If a report for the same source already exists (re-running a migration), overwrite its body rather than creating a duplicate.

## Reasoning is first-class

Every recipe entry must have a **Why** line. Do not just describe what the recipe does (the flow already shows that) — capture the *decision*. Examples:

- *Why:* "Three Alteryx column-ops (Select → Formula → Filter) were consolidated into one Prepare recipe because none of them break the chain (no aggregation, join, or fan-out)."
- *Why:* "This step is a Python recipe because the source used `SUMPRODUCT` across a non-contiguous range, which has no visual equivalent."
- *Why:* "The groupby cell was split from the preceding prepare cell because aggregation breaks the chain (Jupyter RULE 3)."

If you can't explain *why*, the decision probably needs revisiting before you file the report.

## Report structure

Use this skeleton. Omit sections that are N/A for the source type, but keep the order.

```markdown
# Migration Report — <source-filename>

**Source type:** Alteryx | Jupyter notebook | Excel workbook | SAS
**Source file:** `<absolute-or-relative-path>`
**Dataiku project:** `<project-key>` — <project-name>
**Migrated on:** <YYYY-MM-DD>

## 1. Overview

One short paragraph (3–5 sentences). What the source workflow does in plain
language, what the migrated Dataiku flow produces, and anything a reader
should know before diving in (e.g. "This migration preserves all business
logic verbatim except for one hand-translated SUMPRODUCT — see §7").

## 2. Source summary

Short, source-specific summary of the input:
- **Alteryx:** tool count, major branches, inputs/outputs identified.
- **Jupyter:** cell count, libraries used, source CSVs/DBs read.
- **Excel:** sheet inventory, source vs derived sheets, cross-sheet refs, formula counts.

Include the output of the relevant parser (`alteryx.parse_workflow`,
`jupyter.parse_notebook`, `excel.parse_workbook`) summarized — not dumped
in full. A reader should get oriented in 30 seconds.

## 3. Dataset inventory

A table of every dataset in the Dataiku project:

| Dataset | Role | Connection | Source | Notes |
|---------|------|------------|--------|-------|
| `sales_raw` | Input | filesystem_managed | `Sales` sheet (xlsx) | Uploaded as CSV |
| `sales_enriched` | Intermediate | filesystem_managed | Join recipe output | |
| `monthly_summary` | **Terminal** | filesystem_managed | Group recipe output | Built by RECURSIVE_BUILD |

Mark terminal datasets (the ones passed to the final `build_and_wait`) in bold.

## 4. Recipe walkthrough

For EACH recipe in build order (follow the DAG, not creation order):

### <recipe_name>  (type: prepare | group | join | stack | sort | distinct | window | sync | sql | python)

- **Inputs:** `dataset_a`, `dataset_b`
- **Output:** `dataset_c`
- **Source mapping:** <which Alteryx tools / Jupyter cells / Excel sheet+columns this recipe came from>
- **What it does:** one short paragraph. Reference actual processor names or columns.
- **Why designed this way:** the *decision*. If this recipe consolidates multiple source steps, say so and explain what broke / didn't break the chain. If it's a Python recipe, justify why visual wasn't possible.

Keep each recipe entry tight — 4–8 lines. A report for a 20-recipe migration
should still read in a few minutes.

## 5. Consolidation decisions

Explicit list of every place where N source steps collapsed into 1 Dataiku
recipe (the RULE 3 consolidation from every migration ruleset). Example:

- `clean_sales` (prepare): consolidates Alteryx tools t12 (Select), t13
  (Formula), t14 (Filter). Chain did not break — all column-ops.
- `monthly_pivot` (pivot): not consolidated upstream because the preceding
  `groupby` in cell 8 is a chain-breaker.

This section is where readers look to understand the mental model. Be thorough.

## 6. Visual vs Python decisions

For EVERY Python recipe, one line explaining why it is not visual:

- `t47_generate_rows` (python): Alteryx `GenerateRows` has no visual
  equivalent; no chain of Dataiku processors can produce expanding rows
  from a single input row.
- `sumproduct_calc` (python): Excel `SUMPRODUCT` across non-contiguous
  ranges doesn't map to grouping or prepare.

If there are no Python recipes, write "All recipes are visual. No Python
fallbacks were required." That itself is worth celebrating in the report.

## 7. Lossy translations and skipped items

Anything that did NOT translate cleanly, or was intentionally left out:

- Alteryx annotations / comments — preserved as recipe descriptions
  where applicable, otherwise dropped.
- Excel cell formatting, conditional formatting, charts — not migrated
  (Dataiku datasets are unformatted tabular data).
- Jupyter matplotlib cells, model training cells — not migrated unless
  the user specifically requested ML via `ml-training` skill.
- Any formula/tool you marked `unsupported` — list it here with the
  source coordinate (e.g. `sheet=Forecast, cell=AN42`) and why.

If there are no lossy items, say so explicitly. Empty section is wrong;
"None" is right.

## 8. Build verification

- **Terminal datasets built:** `<name1>`, `<name2>`, ...
- **Build mode:** `RECURSIVE_BUILD`
- **Row counts** (one line per terminal dataset — query with
  `helpers.export.count_rows`):
  - `monthly_summary`: 1,247 rows
  - `forecast_by_product`: 36 rows

If a row count looks suspicious (e.g. 0 rows, or drastically different
from the source), flag it in this section.

## 9. Suggested next steps

Short, concrete bullets for the project owner:

- Column types to verify in `<dataset>` — parser may have inferred strings
  for columns that should be numeric/date.
- Scenarios to set up if the source was scheduled (Alteryx scheduled
  workflow, Excel recalc on open, etc.).
- Connections to migrate: if the source used a specific filesystem path,
  whether this should point at a production connection.
```

## Wiki API (use the `wikis` skill)

You should delegate to the `wikis` skill patterns. The minimum you need:

```python
wiki = project.get_wiki()

article_name = f"Migration Report — {source_filename}"

# Check if an article with this name already exists (re-migration case)
existing = None
for a in wiki.list_articles():
    if a.get_data().get_name() == article_name:
        existing = a
        break

if existing:
    data = existing.get_data()
    data.set_body(report_markdown)
    data.save()
    article = existing
else:
    article = wiki.create_article(
        article_name=article_name,
        content=report_markdown,
        parent_id=None,
    )

# If the wiki has no home article yet, make this the home.
settings = wiki.get_settings()
if not settings.get_home_article_id():
    settings.set_home_article_id(article.article_id)
    settings.save()
```

See `.claude/skills/wikis/SKILL.md` for the full wiki API.

## Gathering report inputs

Assemble the report from THREE sources, in this priority:

1. **Your own conversation memory of the migration.** You just designed the flow. The *reasoning* for consolidation, naming, and visual-vs-Python decisions is in your head — write it down while it's fresh. This is the hardest-to-reconstruct part and the most valuable.
2. **The parsed source.** Re-call the parser once (`alteryx.parse_workflow` / `jupyter.parse_notebook` / `excel.parse_workbook`) to pull the source-side tables (tool list, cell list, sheet list) for §2 and the mapping columns in §4.
3. **The built Dataiku project.** Use `helpers.inspection.project_summary(client, project_key)` for the dataset + recipe inventory, and `helpers.export.count_rows` for §8 row counts.

Do not narrate the report purely from project state — project state can't tell you *why* you did something. Narrate from memory, verify with project state.

## Tone & length

- Length: scale with migration size. A 5-recipe migration produces a ~1-page report. A 40-recipe migration produces several pages.
- Tone: factual, concise, present tense. No marketing language. No "successfully migrated" filler.
- Audience: a Dataiku engineer who did not perform this migration and needs to maintain the flow 6 months from now. Write for them.

## Related skills

- [wikis](../wikis/) — Wiki article API (source of the publication mechanics)
- [projects](../projects/) — Project-level metadata
- [flow-management](../flow-management/) — Flow / recipe inspection if you need to re-read structure
- [jobs](../jobs/) — Build status and logs for §8
