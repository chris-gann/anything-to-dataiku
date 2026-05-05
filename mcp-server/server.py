#!/usr/bin/env python3
"""Dataiku MCP Server - Code Execution Paradigm.

This MCP server exposes a single tool that executes Python code with a
pre-configured Dataiku client and helper modules. This follows the
"code execution with MCP" pattern for maximum flexibility and minimal
token overhead.

Supports multiple Dataiku instances - use `use_instance` to switch between them.
Configure instances in .dataiku-instances.json (see .dataiku-instances.example.json).

Usage:
    python server.py
"""

import sys
import os
import json
from io import StringIO
from pathlib import Path
from textwrap import dedent

# Add paths for imports
server_dir = Path(__file__).parent
parent_dir = server_dir.parent
sys.path.insert(0, str(parent_dir))  # For client.py
sys.path.insert(0, str(server_dir))  # For helpers package

from mcp.server.fastmcp import FastMCP
from dataikuapi import DSSClient

import helpers
from helpers import jobs, inspection, search, export, alteryx, jupyter, excel, sas, migration

# =============================================================================
# Instance Configuration - Load from config file
# =============================================================================

CONFIG_FILE = Path(
    os.environ.get(
        "ANYTHING_TO_DATAIKU_CONFIG",
        str(Path.home() / ".dataiku-instances.json"),
    )
)

def load_instances():
    """Load instance configurations from the config file."""
    if not CONFIG_FILE.exists():
        return None, None

    with open(CONFIG_FILE) as f:
        config = json.load(f)

    return config.get("instances", {}), config.get("default", None)

INSTANCES, DEFAULT_INSTANCE = load_instances()

# Check if config is missing
_config_missing = INSTANCES is None or len(INSTANCES) == 0

if _config_missing:
    _instructions = dedent(f"""
    ⚠️  DATAIKU INSTANCES NOT CONFIGURED

    Run /anything-to-dataiku:setup to configure your Dataiku instance,
    or create the config file manually at:
      {CONFIG_FILE}

    Example contents:
    {{
      "default": "MyInstance",
      "instances": {{
        "MyInstance": {{
          "url": "https://your-instance.dataiku.com",
          "api_key": "dkuaps-your-api-key",
          "description": "My Dataiku instance"
        }}
      }}
    }}

    After creating the config, restart Claude Code.
    """).strip()
    INSTANCES = {}
    DEFAULT_INSTANCE = None
else:
    # Build instructions with available instances
    instance_list = "\n".join(
        f'  - {name}: {cfg["description"]} ({cfg["url"]})'
        for name, cfg in INSTANCES.items()
    )
    _instructions = dedent(f"""
    Dataiku DSS control server with multi-instance support.

    **Current instance: {DEFAULT_INSTANCE}** (default)

    Available instances:
    {instance_list}

    Use `use_instance("InstanceName")` to switch instances at the start of a session.

    ==========================================================================
    ALTERYX → DATAIKU MIGRATION RULES (READ FIRST)
    ==========================================================================

    RULE 1 — READ THE .yxmd FILE FIRST.
      Before doing anything, read the entire .yxmd file (it's XML).
      Understand every tool, connection, annotation, and expression.
      This full context is essential for making good consolidation and
      naming decisions. Do NOT rely solely on parsed summaries.

    RULE 2 — PREFER VISUAL RECIPES. Python is a LAST RESORT.
      Every Alteryx tool that has a visual equivalent in Dataiku MUST be
      built as the visual recipe. Do NOT write one big Python recipe.

    RULE 3 — CONSOLIDATE CONSECUTIVE COLUMN-OPS INTO ONE PREPARE RECIPE.
      If you see three Alteryx column-ops in a row (Select → Formula → Filter),
      that is ONE Dataiku Prepare recipe with multiple processor steps — not
      three separate recipes. Chains break on aggregation, join, union, sort,
      pivot, or a fan-out/fan-in topology.

    RULE 4 — SEMANTIC NAMES ONLY. Name datasets and recipes after what they
      represent: `sales_with_abc_classification`, `monthly_units_pivoted`,
      `forecast_error_by_item`. NEVER use tool IDs like `t47` or `compute_t12`.

    RULE 5 — BATCH RECIPE CREATION, THEN BUILD ONCE.
      Create all recipes with `defer_schema=True`, then do ONE final
      `jobs.build_and_wait(client, pk, [terminal_datasets])` with
      build_mode="RECURSIVE_BUILD". Do NOT build after every recipe.

    RULE 6 — GENERATE A MIGRATION REPORT.
      After the final build succeeds, invoke the `migration-report`
      skill to publish a detailed report (with reasoning for every
      design decision) to the project wiki. This is the definition of
      done. Do NOT consider the migration complete without the report.

    Alteryx → Dataiku recipe mapping:
      Select, Filter, Formula, MultiFieldFormula, DateTime, RegEx,
      FindReplace, TextToColumns, DynamicRename, RecordID,
      Transpose, Cleanse                                    → prepare
      Summarize                                             → grouping
      Join, JoinMultiple                                    → join
      AppendFields                                          → join (CROSS)
      Union                                                 → vstack
      Sort                                                  → sort
      Unique                                                → distinct
      Sample                                                → sampling
      CrossTab                                              → pivot
      RunningTotal                                          → window
      GenerateRows, MultiRowFormula                         → python (fallback)

    Recipe builders (all in `migration`, all accept `defer_schema=False`):
      create_prepare_recipe(client, pk, input_name, output_name, processors, connection, defer_schema)
      create_group_recipe(client, pk, input_name, output_name, group_keys, aggregations, connection, global_count=False, defer_schema)
      create_join_recipe(client, pk, inputs, join_conditions, output_name, join_type='LEFT', connection, column_selections, defer_schema)
      create_stack_recipe(client, pk, inputs, output_name, connection, defer_schema)
      create_sort_recipe(client, pk, input_name, output_name, sort_columns, connection, defer_schema)
      create_distinct_recipe(client, pk, input_name, output_name, key_columns, connection, defer_schema)
      create_window_recipe(client, pk, input_name, output_name, aggregations, partition_by, order_by, connection, defer_schema)
      create_sync_recipe(client, pk, input_name, output_name, connection, defer_schema)
      create_python_recipe(client, pk, connection, inputs, output_name, code, defer_schema)  # LAST RESORT

    Dataiku quirks to know:
      - Filter → use `FilterOnCustomFormula` processor (FilterOnFormula is plugin-gated)
      - ColumnsSelector → {{"keep": bool, "appliesTo": "COLUMNS", "columns": [str,...]}}
      - Grouping: set globalCount=False; strip `count` flag from value columns
      - After creating/modifying Python recipes, MUST call
        helpers.jobs.compute_and_apply_schema before building

    ==========================================================================
    JUPYTER → DATAIKU MIGRATION RULES
    ==========================================================================

    RULE 1 — READ THE .ipynb FILE FIRST.
      Read the entire notebook (it's JSON). Understand every code cell,
      every markdown description, the variable flow between cells, and
      the intent of each block. Parsed summaries are a hint, not a
      substitute for reading the notebook.

    RULE 2 — PREFER VISUAL RECIPES. Python is a LAST RESORT.
      Every pandas or SQL operation with a visual equivalent MUST
      become a visual recipe. Only fall back to a Python recipe for
      genuine logic (ML training, API calls, custom algorithms,
      row-wise iteration that pandas can't vectorize).

    RULE 3 — CONSOLIDATE CONSECUTIVE COLUMN-OPS INTO ONE PREPARE RECIPE.
      Cells (or statements within a cell) that only do column ops —
      filter/query, assign, rename, astype, fillna, dropna, str methods,
      pd.to_datetime, drop columns, replace — are ONE prepare recipe
      with multiple processors. Chains break on groupby, merge, concat,
      sort_values, pivot_table, or drop_duplicates.

    RULE 4 — USE MARKDOWN CELLS FOR SEMANTIC NAMES.
      Markdown cells describe what follows. "## Monthly sales aggregation"
      above a groupby cell → recipe `monthly_sales_aggregation`, output
      `monthly_sales`. NEVER use cell indexes like `cell_7` or `step3`.

    RULE 5 — BATCH RECIPE CREATION, THEN BUILD ONCE.
      Same as Alteryx: defer_schema=True on every recipe, one final
      jobs.build_and_wait with RECURSIVE_BUILD on terminal datasets.

    RULE 6 — GENERATE A MIGRATION REPORT.
      After the final build succeeds, invoke the `migration-report`
      skill to publish a detailed report (with reasoning for every
      design decision) to the project wiki. Definition of done.

    Pandas → Dataiku recipe mapping:
      df.groupby().agg() / .sum() / .mean() / .count()  → grouping
      df.merge() / pd.merge()                           → join
      pd.concat([...])                                  → vstack
      df.sort_values()                                  → sort
      df.drop_duplicates()                              → distinct
      df[mask] / df.query()                             → prepare (FilterOnCustomFormula)
      df.assign() / df['x']=... / df.rename() /
        df.astype() / df.fillna() / df.dropna() /
        df.str.* / pd.to_datetime() / df.drop(cols) /
        df.replace()                                    → prepare (CHAIN THESE)
      df.pivot_table() / df.pivot()                     → pivot
      df.melt()                                         → prepare (unpivot processor)
      pd.read_sql() / %%sql cells                       → sql recipe
      ML / sklearn / tf / custom logic                  → python recipe (last resort)

    Input detection (from parsed notebook):
      pd.read_csv / read_excel / read_parquet / read_json / read_table
      → Source datasets. Upload to Dataiku BEFORE building recipes.
      Use existing dataset-management skill patterns for uploads.

    Output detection (from parsed notebook):
      df.to_csv / to_parquet / to_sql / to_excel
      → Terminal datasets. Pass these names to jobs.build_and_wait in
      the final build step.

    Standard Jupyter migration flow:
        # 1. YOU (Claude) read the .ipynb file directly for full context.

        # 2. Parse structure for hints (YOU still make the plan):
        parsed = jupyter.parse_notebook("/path/to/notebook.ipynb")

        # 3. Create project + upload source datasets (the read_* inputs):
        migration.create_project_for_migration(client, "MY_PROJECT", "My Project")
        # Upload each referenced file using dataset-management skill.

        # 4. Build recipes using create_*_recipe helpers.
        #    defer_schema=True on all. Semantic names from markdown.
        #    Consolidate consecutive column-ops into single prepare recipes.

        # 5. One final build on terminal datasets (the to_* outputs):
        jobs.build_and_wait(client, "MY_PROJECT", [...terminal_names...],
                            build_mode="RECURSIVE_BUILD")

    ==========================================================================
    EXCEL → DATAIKU MIGRATION RULES
    ==========================================================================

    RULE 1 — READ THE WORKBOOK STRUCTURE FIRST.
      Call excel.parse_workbook(path) and inspect every sheet. Read
      headers, sample_rows, formula_patterns, and cross_sheet_refs.
      Do NOT skim — Excel files mix data and logic densely, and the
      structure of one sheet often only makes sense in light of another.

    RULE 2 — PREFER VISUAL RECIPES. Python is a LAST RESORT.
      Every Excel formula with a visual equivalent MUST become a visual
      recipe. Only fall back to Python for unsupported constructs:
      array formulas, INDIRECT/OFFSET, VBA macros, multi-step custom
      logic that no chain of processors can express.

    RULE 3 — SOURCE SHEETS BECOME DATASETS, DERIVED SHEETS BECOME RECIPES.
      `source_sheets` (no formulas, only values) → upload as Dataiku
      datasets. `derived_sheets` (cells reference other sheets) → build
      recipes that produce them. `cross_sheet_refs` is the dataflow:
      use it to determine recipe build order.

    RULE 4 — CONSOLIDATE COLUMN-OPS INTO ONE PREPARE RECIPE.
      A sheet whose formulas are all `prepare`-class (conditional, date,
      text, math, arithmetic) is ONE prepare recipe with one processor
      per derived column. Chains break only when the sheet introduces a
      lookup (→ separate join recipe) or aggregation (→ separate group).

    RULE 5 — USE COLUMN HEADERS AND SHEET NAMES FOR SEMANTIC NAMES.
      A sheet named "Monthly_Summary" with SUMIFS by region → recipe
      `monthly_summary_by_region`, output `monthly_summary`. NEVER use
      sheet indexes like `sheet1` or coordinate names like `B5_value`.

    RULE 6 — BATCH RECIPE CREATION, THEN BUILD ONCE.
      Same as Alteryx: defer_schema=True on every recipe, one final
      jobs.build_and_wait with RECURSIVE_BUILD on terminal datasets.

    RULE 7 — GENERATE A MIGRATION REPORT.
      After the final build succeeds, invoke the `migration-report`
      skill to publish a detailed report (with reasoning for every
      design decision) to the project wiki. Definition of done.

    Excel → Dataiku recipe mapping (per formula classification):
      lookup (VLOOKUP, HLOOKUP, XLOOKUP, INDEX/MATCH)    → join
      conditional_aggregation (SUMIF[S], COUNTIF[S],
        AVERAGEIF[S], MAXIFS, MINIFS)                    → grouping
      aggregation (SUM, AVERAGE, MIN, MAX, COUNT,
        MEDIAN over a range)                             → grouping
                                                            (or just a
                                                            total row —
                                                            YOU decide)
      conditional (IF, IFS, SWITCH, AND, OR, IFERROR)    → prepare
      date (EDATE, YEAR, MONTH, DATEDIF, EOMONTH, ...)   → prepare
      text (LEFT, RIGHT, MID, CONCAT, TRIM, TEXT, ...)   → prepare
      math (ROUND, ABS, MOD, POWER, ...)                 → prepare
      arithmetic (only operators + cell refs)            → prepare
      array (SUMPRODUCT, MMULT, {{=...}})                → python (fallback)
      dynamic (INDIRECT, OFFSET)                         → python (fallback)

    Per-sheet `recipe_hint` interpretation:
      data_only   → upload as a Dataiku dataset, no recipe needed
      prepare     → ONE prepare recipe with multiple processors
      join        → join recipe (lookup formulas tell you the keys)
      grouping    → group recipe (group keys = the criteria args)
      mixed       → MULTIPLE recipes — split by classification (Claude
                    decides the split per RULE 4)
      python      → Python fallback (array/dynamic/macro)

    Standard Excel migration flow:
        # 1. YOU (Claude) read the .xlsx (use excel.parse_workbook
        #    + open the file in inspection if needed for context).

        # 2. Parse structure:
        parsed = excel.parse_workbook("/path/to/workbook.xlsx")

        # 3. Create project + upload each source_sheet as a dataset.
        #    Use cross_sheet_refs to determine which sheets are inputs
        #    vs outputs of the implicit pipeline.
        migration.create_project_for_migration(client, "MY_PROJECT", "My Project")
        # Upload each source sheet via dataset-management skill.

        # 4. Build recipes IN DEPENDENCY ORDER (cross_sheet_refs gives
        #    the topology). For each derived sheet, use the recipe_hint:
        #      - join → create_join_recipe (keys from VLOOKUP signatures)
        #      - grouping → create_group_recipe (keys from SUMIFS args)
        #      - prepare → create_prepare_recipe (one processor per column)
        #      - mixed → multiple recipes
        #    All with defer_schema=True. Semantic names from sheet names.

        # 5. One final build on terminal datasets:
        jobs.build_and_wait(client, "MY_PROJECT", [...terminal_names...],
                            build_mode="RECURSIVE_BUILD")

    ==========================================================================
    SAS → DATAIKU MIGRATION RULES
    ==========================================================================

    RULE 1 — READ EVERY .sas FILE FIRST.
      Call sas.parse_project(directory) for an overview, then read each
      .sas file end-to-end. Macros, libname blocks, and cross-file data
      dependencies make summaries lossy. The parser is a navigator, not
      a substitute for the source.

    RULE 2 — PREFER VISUAL RECIPES. Python is a LAST RESORT.
      DATA steps and PROC SQL look intimidating but most decompose into
      visual recipes. Only fall back to Python for: PROC FREQ/MEANS with
      statistical tests (exact, chisq, ttest), PROC ANOVA/GLM/REG/
      LOGISTIC/LIFETEST, DATA steps with ARRAY or explicit DO loops,
      INPUT/OUTPUT statement gymnastics.

    RULE 3 — XPT/SAS7BDAT FILES ARE YOUR INPUT DATASETS.
      Every .xpt and .sas7bdat is a Dataiku dataset. Convert XPORT to
      CSV via `pandas.read_sas(path, format='xport')` then upload using
      dataset-management patterns. The libname-defined directories tell
      you which library each dataset belongs to (e.g. SDTMNEW.AE means
      AE in the sdtmnew library).

    RULE 4 — DATA STEPS WITH MERGE BECOME JOINS.
      A SAS `merge X(in=inX) Y; by usubjid;` is a Dataiku Join recipe.
      The `if inX;` clause selects the join type (LEFT/INNER/RIGHT).
      Variables created inside the same data step (after the merge) are
      a follow-on Prepare recipe — split them. The parser identifies
      `merge` as a feature on data steps with hint=join.

    RULE 5 — PROC SORT → SORT (or skip).
      Standalone proc sort → Sort recipe. BUT: if the next step is the
      only consumer and it would re-sort anyway (e.g. a DATA step with
      `by` that uses first./last.), the sort is just feeding the next
      step — fold it in or skip. Dataiku Group, Join, and Window recipes
      handle their own ordering.

    RULE 6 — PROC SQL: READ EACH CREATE TABLE INDEPENDENTLY.
      A single `proc sql; ... quit;` block often contains 5–10 CREATE
      TABLE statements. Each is its own logical step — DO NOT translate
      the whole block as one SQL recipe by default. Map each CREATE
      TABLE to:
        SELECT cols FROM x GROUP BY y           → grouping recipe
        SELECT cols FROM x LEFT JOIN y ON ...   → join recipe
        SELECT distinct ... FROM x              → distinct recipe
        anything with case/when/computed cols   → join + prepare
      Use a SQL recipe ONLY when the SELECT genuinely needs SQL
      expressivity (window functions, CTEs, complex subqueries).

    RULE 7 — MACROS: DO NOT EXPAND, INSTANTIATE.
      The parser flags `macro_def` and `macro_call` steps separately.
      For each macro_call, READ the macro_def body and decide the
      translation per call:
        - If every call produces a similar shape (e.g. 7× sort+filter+
          first-record-flag), build 7 separate visual recipes with
          semantic names derived from the macro arguments
          (e.g. AOCCFL, AOCCSFL, AOCCPFL → recipe names).
        - If calls are highly parameterized over a column list, ONE
          Python recipe that loops is acceptable.
      Never silently drop a macro_call — every call produces a dataset
      that downstream steps consume.

    RULE 8 — `first.` / `last.` / `retain` → WINDOW recipe.
      A DATA step with `first.var` or `last.var` is a windowed operation
      (partition by `by` columns, take first/last). Use Dataiku Window
      recipe with appropriate aggregations (e.g. row_number for first.).
      `retain` for stateful accumulation across rows is also Window;
      complex retain logic may need Python.

    RULE 9 — STATISTICAL PROCS = PYTHON RECIPE.
      PROC FREQ with `exact`, PROC MEANS with confidence intervals,
      PROC TTEST/ANOVA/GLM/REG/LOGISTIC/LIFETEST etc. — these compute
      statistics, not transform data. Implement as a Python recipe using
      scipy/statsmodels and write the result as a Dataiku dataset.

    RULE 10 — ENDSAS / ODS / PROC PRINT / PROC CONTENTS = SKIP.
      `endsas;`, `ods rtf file=...`, `proc print`, `proc contents`,
      `proc report` are output/diagnostic side effects, not data
      transformations. The parser hints "skip" — honor it.

    RULE 11 — BATCH RECIPE CREATION, THEN BUILD ONCE.
      Same as every other source: defer_schema=True on every recipe,
      one final jobs.build_and_wait with RECURSIVE_BUILD on terminal
      datasets (the final libname.<dataset> outputs).

    RULE 12 — GENERATE A MIGRATION REPORT.
      After the final build succeeds, invoke the `migration-report`
      skill to publish a detailed report (with reasoning for every
      design decision) to the project wiki. Definition of done.

    SAS construct → Dataiku recipe quick reference:
      proc sort                                  → sort
      proc sql with single CREATE TABLE GROUP BY → grouping
      proc sql with single CREATE TABLE JOIN     → join
      proc sql with multiple CREATE TABLEs       → split into N recipes
      proc freq (counts)                         → grouping
      proc freq (with /exact, /chisq)            → python
      proc means / proc summary                  → grouping
      proc tabulate                              → pivot (or grouping)
      proc transpose                             → pivot
      proc append                                → vstack
      proc format                                → prepare value-mapping
      data step: set only                        → sync
      data step: merge ... by ...                → join (+ prepare)
      data step: first./last./retain             → window (or python)
      data step: array, do loop                  → python
      data step: if/then/else, format, label     → prepare
      %macro / %mend                             → not a recipe (template)
      %macro_call(...)                           → 1+ recipe(s) per call
      libname / %include / endsas / ods          → skip

    Standard SAS migration flow:
        # 1. YOU (Claude) read every .sas file end-to-end and study the
        #    define.xml / .json metadata if present.

        # 2. Parse the project for navigation:
        proj = sas.parse_project("/path/to/sas/project")

        # 3. Create project + upload .xpt/.sas7bdat datasets:
        migration.create_project_for_migration(client, "MY_PROJECT", "My Project")
        # For each xpt: pandas.read_sas(path, format='xport') → write as CSV
        # → upload via dataset-management patterns.

        # 4. Build recipes following the dataset_graph topology.
        #    For each step:
        #      - Use the recipe_hint as a starting point.
        #      - For macro_calls, read the macro_def body and build the
        #        instantiated recipe(s) with semantic names from args.
        #      - For proc sql, split each CREATE TABLE into its own recipe.
        #    All with defer_schema=True.

        # 5. One final build on terminal datasets:
        jobs.build_and_wait(client, "MY_PROJECT", [...terminal_names...],
                            build_mode="RECURSIVE_BUILD")

        # 6. Invoke `migration-report` skill (RULE 12).

    Available in the execution namespace:
    - client: Authenticated DSSClient instance
    - helpers.jobs: build_and_wait, run_scenario_and_wait, compute_and_apply_schema
    - helpers.inspection: dataset_info, project_summary
    - helpers.search: find_datasets, find_by_connection
    - helpers.export: to_records, sample, head
    - helpers.alteryx: parse_workflow, extract_embedded_data
    - helpers.jupyter: parse_notebook
    - helpers.excel: parse_workbook
    - helpers.sas: parse_program, parse_project
    - helpers.migration: migrate_workflow, create_*_recipe (see list_helpers for all)

    Standard migration flow:
        # 1. YOU (Claude) read the .yxmd file directly to understand the
        #    full workflow — tools, expressions, connections, annotations.

        # 2. Create project + upload embedded data:
        result = migration.migrate_workflow(client, "MY_PROJECT", "My Project",
                                            "/path/to/workflow.yxmd")
        # result has: project, uploaded_datasets, parsed_workflow

        # 3. Build recipes yourself using create_*_recipe helpers.
        #    Use defer_schema=True on all of them.
        #    Name everything semantically based on your understanding of the XML.
        #    Consolidate consecutive column-ops into single prepare recipes.

        # 4. One final build:
        jobs.build_and_wait(client, "MY_PROJECT", ["final_output_1", "final_output_2"],
                            build_mode="RECURSIVE_BUILD")

    For processor JSON formats, aggregation flags, GREL functions, and
    pitfalls, reference `.claude/skills/recipe-patterns/references/`.
    """).strip()

# =============================================================================
# Server State
# =============================================================================

_current_instance = DEFAULT_INSTANCE
_client = None

def get_dataiku_client():
    """Get or create the Dataiku client for current instance."""
    global _client
    if _current_instance and _current_instance in INSTANCES:
        instance_config = INSTANCES[_current_instance]
        _client = DSSClient(instance_config["url"], instance_config["api_key"])
    return _client

def switch_instance(instance_name: str) -> bool:
    """Switch to a different Dataiku instance."""
    global _current_instance, _client
    if instance_name in INSTANCES:
        _current_instance = instance_name
        _client = None  # Reset client so it reconnects
        return True
    return False

# =============================================================================
# MCP Server Setup
# =============================================================================

# Initialize MCP server
mcp = FastMCP("dataiku", instructions=_instructions)

# Persistent execution namespace
execution_globals = {
    "__builtins__": __builtins__,
    "helpers": helpers,
    "jobs": jobs,
    "inspection": inspection,
    "search": search,
    "export": export,
    "alteryx": alteryx,
    "jupyter": jupyter,
    "excel": excel,
    "sas": sas,
    "migration": migration,
}


@mcp.tool()
def use_instance(instance_name: str) -> str:
    """Switch to a different Dataiku instance.

    Call this at the start of a session to connect to a specific instance.

    Args:
        instance_name: Name of the instance to use (e.g., "Jed", "Analytics")

    Returns:
        Confirmation message with instance details
    """
    if _config_missing:
        return f"No instances configured. Please create {CONFIG_FILE}"

    if instance_name not in INSTANCES:
        available = ", ".join(INSTANCES.keys())
        return f"Unknown instance '{instance_name}'. Available instances: {available}"

    if switch_instance(instance_name):
        config = INSTANCES[instance_name]
        # Reset the client in execution globals
        execution_globals["client"] = get_dataiku_client()
        return f"Switched to instance '{instance_name}'\nURL: {config['url']}\nDescription: {config['description']}"

    return f"Failed to switch to instance '{instance_name}'"


@mcp.tool()
def list_instances() -> str:
    """List all available Dataiku instances.

    Returns:
        List of configured instances with their details
    """
    if _config_missing:
        return f"No instances configured. Please create {CONFIG_FILE}"

    lines = [f"Current instance: {_current_instance}", "", "Available instances:"]
    for name, config in INSTANCES.items():
        marker = " (active)" if name == _current_instance else ""
        lines.append(f"  - {name}{marker}")
        lines.append(f"      URL: {config['url']}")
        lines.append(f"      Description: {config['description']}")
    return "\n".join(lines)


@mcp.tool()
def execute_python(code: str) -> str:
    """Execute Python code with pre-configured Dataiku client.

    The execution environment includes:
    - client: Authenticated DSSClient connected to your Dataiku instance
    - helpers.jobs: build_and_wait, run_scenario_and_wait, run_recipe_and_wait
    - helpers.inspection: dataset_info, project_summary, connection_info
    - helpers.search: find_datasets, find_recipes, find_by_connection
    - helpers.export: to_records, sample, head, get_schema
    - helpers.alteryx: parse_workflow, extract_embedded_data
    - helpers.jupyter: parse_notebook
    - helpers.excel: parse_workbook
    - helpers.sas: parse_program, parse_project
    - helpers.migration: migrate_workflow, create_prepare_recipe,
        create_group_recipe, create_join_recipe, create_stack_recipe,
        create_sort_recipe, create_distinct_recipe, create_window_recipe,
        create_sync_recipe, create_python_recipe (LAST RESORT)

    For Alteryx→Dataiku migrations:
    1. Read the .yxmd file directly for full workflow context
    2. Call migration.migrate_workflow() to create project + upload data
    3. Build recipes using create_*_recipe helpers with defer_schema=True
    4. One final build_and_wait on terminal datasets

    For Jupyter→Dataiku migrations:
    1. Read the .ipynb file directly for full notebook context
    2. Call jupyter.parse_notebook() for structured per-cell hints
    3. Create project + upload the pd.read_* source datasets
    4. Build recipes using create_*_recipe helpers with defer_schema=True
       — PREFER visual recipes, Python is last resort
    5. One final build_and_wait on terminal datasets (the df.to_* outputs)

    For Excel→Dataiku migrations:
    1. Call excel.parse_workbook() for per-sheet structure + formula
       clustering + cross-sheet dataflow
    2. Upload source_sheets as datasets
    3. For each derived_sheet, build a recipe using recipe_hint:
       join / grouping / prepare / mixed / python — in dependency order
       from cross_sheet_refs
    4. defer_schema=True on all, then one final build_and_wait

    For SAS→Dataiku migrations:
    1. Read every .sas file end-to-end (macros + cross-file refs make
       summaries lossy)
    2. Call sas.parse_project() for steps + dataset_graph + macros_registry
    3. Upload .xpt/.sas7bdat data_files as datasets (pandas.read_sas)
    4. Translate per step using recipe_hint. Macros: read macro_def body
       and instantiate one recipe per macro_call. PROC SQL: split each
       CREATE TABLE into its own recipe.
    5. defer_schema=True on all, one final build_and_wait, then
       invoke migration-report

    Variables persist across calls within the same session.

    Args:
        code: Python code to execute

    Returns:
        stdout output from the code, or error message if execution fails
    """
    if _config_missing:
        return f"No instances configured. Please create {CONFIG_FILE}"

    # Ensure client is in namespace
    execution_globals["client"] = get_dataiku_client()

    # Capture stdout
    stdout_capture = StringIO()
    old_stdout = sys.stdout
    sys.stdout = stdout_capture

    try:
        # Execute the code
        exec(code, execution_globals)
        output = stdout_capture.getvalue()
        return output if output else "(executed successfully, no output)"
    except Exception as e:
        import traceback
        error_output = stdout_capture.getvalue()
        tb = traceback.format_exc()
        return f"{error_output}\nError: {type(e).__name__}: {e}\n\n{tb}"
    finally:
        sys.stdout = old_stdout


@mcp.tool()
def list_helpers() -> str:
    """List all available helper functions and their signatures.

    Returns:
        Formatted list of all helper modules and functions
    """
    output = []

    output.append("=== helpers.jobs ===")
    output.append("  build_and_wait(client, project_key, dataset_name, build_mode='RECURSIVE_BUILD', timeout=600)")
    output.append("  run_scenario_and_wait(client, project_key, scenario_id, timeout=600)")
    output.append("  run_recipe_and_wait(client, project_key, recipe_name, timeout=600)")
    output.append("  wait_for_job(job, timeout=600, poll_interval=2)")
    output.append("  get_job_log(client, project_key, job_id)")
    output.append("  compute_and_apply_schema(client, project_key, recipe_name)  # REQUIRED after creating/modifying recipes")
    output.append("")

    output.append("=== helpers.inspection ===")
    output.append("  dataset_info(client, project_key, dataset_name, sample_size=5)")
    output.append("  project_summary(client, project_key)")
    output.append("  list_projects_summary(client)")
    output.append("  connection_info(client, connection_name)")
    output.append("  list_connections_summary(client)")
    output.append("  user_info(client, login=None)")
    output.append("")

    output.append("=== helpers.search ===")
    output.append("  find_datasets(client, pattern, project_key=None)")
    output.append("  find_recipes(client, pattern, project_key=None)")
    output.append("  find_scenarios(client, pattern, project_key=None)")
    output.append("  find_by_connection(client, connection_name)")
    output.append("  find_by_type(client, dataset_type, project_key=None)")
    output.append("  find_users(client, pattern)")
    output.append("")

    output.append("=== helpers.export ===")
    output.append("  to_records(client, project_key, dataset_name, limit=100)")
    output.append("  sample(client, project_key, dataset_name, n=10)")
    output.append("  get_schema(client, project_key, dataset_name)")
    output.append("  get_column_names(client, project_key, dataset_name)")
    output.append("  count_rows(client, project_key, dataset_name)")
    output.append("  head(client, project_key, dataset_name, n=5)")
    output.append("  describe(client, project_key, dataset_name)")
    output.append("  to_csv_string(client, project_key, dataset_name, limit=100)")
    output.append("")

    output.append("=== helpers.alteryx ===")
    output.append("  parse_workflow(filepath) -> dict  # Structured summary: nodes, connections, data inputs, flow order")
    output.append("  extract_embedded_data(filepath, tool_id) -> dict  # Extract TextInput data: columns, rows, num_rows")
    output.append("  data_to_csv(columns, rows) -> str  # Convert extracted data to CSV string")
    output.append("")

    output.append("=== helpers.jupyter ===")
    output.append("  parse_notebook(filepath) -> dict  # Per-cell structure + visual-recipe hints")
    output.append("    Returns: num_cells, cells[], inputs_summary, outputs_summary")
    output.append("    Each code cell: imports, inputs (pd.read_*), outputs (df.to_*),")
    output.append("    pandas_ops, sql_cell, visual_recipe_hint (prepare/grouping/join/vstack/")
    output.append("    sort/distinct/pivot/sql/python). Markdown cells: heading.")
    output.append("")

    output.append("=== helpers.excel ===")
    output.append("  parse_workbook(filepath) -> dict  # Per-sheet structure + formula clustering")
    output.append("    Returns: filename, has_macros, sheets[], named_ranges, cross_sheet_refs,")
    output.append("    source_sheets, derived_sheets")
    output.append("    Each sheet: dimensions, header_row, headers, sample_rows, cell_stats,")
    output.append("    formula_patterns (CLUSTERED by column × normalized pattern with class +")
    output.append("    referenced_sheets + count + row_range), formula_summary, tables,")
    output.append("    recipe_hint (data_only/prepare/join/grouping/mixed/python).")
    output.append("")

    output.append("=== helpers.sas ===")
    output.append("  parse_program(filepath) -> dict  # Per-step structure for one .sas file")
    output.append("    Returns: filename, num_lines, steps[], datasets_in, datasets_out,")
    output.append("    libnames, includes, macros_defined, macros_called.")
    output.append("    Each step: type (data/proc/macro_def/macro_call/libname/include/endsas),")
    output.append("    line_start/end, name, source, inputs, outputs, features, recipe_hint")
    output.append("    (sort/sql/grouping/join/prepare/window/pivot/sync/python/skip/template).")
    output.append("  parse_project(directory) -> dict  # Walks a SAS project directory")
    output.append("    Returns: programs[], data_files (.xpt/.sas7bdat), metadata_files (define.*),")
    output.append("    include_graph, macros_registry, dataset_graph (cross-file producers/consumers).")
    output.append("")

    output.append("=== helpers.migration ===")
    output.append("  # Setup")
    output.append("  migrate_workflow(client, project_key, project_name, filepath, connection='filesystem_managed') -> dict  # create project + upload embedded data")
    output.append("  create_project_for_migration(client, project_key, project_name, description='', owner='admin') -> dict")
    output.append("  upload_embedded_data(client, project_key, filepath, tool_id, dataset_name) -> dict")
    output.append("  # Visual recipe builders (all accept defer_schema=False) — PREFER THESE OVER PYTHON")
    output.append("  create_prepare_recipe(client, pk, input_name, output_name, processors, connection='filesystem_managed', defer_schema=False) -> dict")
    output.append("  create_group_recipe(client, pk, input_name, output_name, group_keys, aggregations, connection='filesystem_managed', global_count=False, defer_schema=False) -> dict")
    output.append("  create_join_recipe(client, pk, inputs, join_conditions, output_name, join_type='LEFT', connection='filesystem_managed', column_selections=None, defer_schema=False) -> dict  # join_type='CROSS' for AppendFields")
    output.append("  create_stack_recipe(client, pk, inputs, output_name, connection='filesystem_managed', defer_schema=False) -> dict  # Alteryx Union")
    output.append("  create_sort_recipe(client, pk, input_name, output_name, sort_columns, connection='filesystem_managed', defer_schema=False) -> dict")
    output.append("  create_distinct_recipe(client, pk, input_name, output_name, key_columns=None, connection='filesystem_managed', defer_schema=False) -> dict  # Alteryx Unique")
    output.append("  create_window_recipe(client, pk, input_name, output_name, aggregations, partition_by=None, order_by=None, connection='filesystem_managed', defer_schema=False) -> dict  # Alteryx RunningTotal")
    output.append("  create_sync_recipe(client, pk, input_name, output_name, connection='filesystem_managed', defer_schema=False) -> dict")
    output.append("  # Python fallback — LAST RESORT, only for GenerateRows / MultiRowFormula")
    output.append("  create_python_recipe(client, pk, connection, inputs, output_name, code, defer_schema=False) -> dict")

    return "\n".join(output)


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
