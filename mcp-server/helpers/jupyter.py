"""Jupyter .ipynb notebook parsing utilities.

Parses notebooks into structured per-cell data with light visual-recipe
hints so Claude can reason about the flow without re-reading JSON.

Design: parser surfaces structure, Claude decides. No planner here —
the migration decisions (consolidation, naming, splitting) are made by
Claude using the RULES in the dataiku MCP server instructions.
"""

import ast
import json


# ── Pandas I/O detection ───────────────────────────────────────────────

PANDAS_READ_FUNCS = {
    "read_csv", "read_excel", "read_parquet", "read_json",
    "read_table", "read_feather", "read_orc",
    "read_sql", "read_sql_query", "read_sql_table",
}

PANDAS_WRITE_METHODS = {
    "to_csv", "to_excel", "to_parquet", "to_json",
    "to_feather", "to_orc", "to_sql",
}

# ── Pandas op → Dataiku visual recipe ──────────────────────────────────
# Only ops with a clean visual equivalent. Anything not listed is
# treated as non-mappable (push cell toward Python recipe fallback).

OP_TO_RECIPE = {
    # grouping
    "groupby": "grouping",
    "agg": "grouping",
    "aggregate": "grouping",
    # join
    "merge": "join",
    # stack / union
    "concat": "vstack",
    "append": "vstack",
    # sort
    "sort_values": "sort",
    # distinct
    "drop_duplicates": "distinct",
    "unique": "distinct",
    # pivot / unpivot
    "pivot_table": "pivot",
    "pivot": "pivot",
    "melt": "prepare",
    # prepare-mappable column ops
    "query": "prepare",
    "assign": "prepare",
    "rename": "prepare",
    "astype": "prepare",
    "fillna": "prepare",
    "dropna": "prepare",
    "replace": "prepare",
    "drop": "prepare",
    "filter": "prepare",
    "where": "prepare",
    "mask": "prepare",
}

# Priority when multiple ops are detected in one cell. The top-priority
# op becomes the cell's primary hint; the full list stays in pandas_ops
# so Claude can decide whether to split the cell into multiple recipes.
RECIPE_PRIORITY = ["sql", "grouping", "join", "vstack", "pivot", "sort", "distinct", "prepare", "python"]


# ── Public API ─────────────────────────────────────────────────────────

def parse_notebook(filepath: str) -> dict:
    """Parse a .ipynb file into structured per-cell data.

    Returns a dict with:
      num_cells: int
      cells: list of cell dicts, each with:
          index, cell_type, source, line_count
        markdown cells also have:
          heading: first markdown heading text or None
        code cells also have:
          imports: list of imported module names
          sql_cell: bool (True if %%sql magic)
          magic: str or None (other cell magic)
          inputs: list of {kind, arg} — detected pd.read_*/open calls
          outputs: list of {kind, arg} — detected df.to_* calls
          pandas_ops: list of {op} — detected ops matching OP_TO_RECIPE
          visual_recipe_hint: primary Dataiku recipe type suggestion
          parse_error: True if AST parsing failed
      inputs_summary: flat list of all detected inputs across cells
      outputs_summary: flat list of all detected outputs across cells

    The `visual_recipe_hint` is a hint only. If pandas_ops contains
    multiple breaking ops, Claude should split the cell across recipes.
    """
    with open(filepath) as f:
        nb = json.load(f)

    cells = []
    for i, c in enumerate(nb.get("cells", [])):
        src = _get_source(c)
        entry = {
            "index": i,
            "cell_type": c.get("cell_type"),
            "source": src,
            "line_count": len(src.splitlines()) if src else 0,
        }
        if c.get("cell_type") == "markdown":
            entry["heading"] = _first_heading(src)
        elif c.get("cell_type") == "code":
            entry.update(_analyze_code_cell(src))
        cells.append(entry)

    inputs_summary = [
        {**inp, "cell_index": c["index"]}
        for c in cells if c.get("cell_type") == "code"
        for inp in c.get("inputs", [])
    ]
    outputs_summary = [
        {**out, "cell_index": c["index"]}
        for c in cells if c.get("cell_type") == "code"
        for out in c.get("outputs", [])
    ]

    return {
        "num_cells": len(cells),
        "cells": cells,
        "inputs_summary": inputs_summary,
        "outputs_summary": outputs_summary,
    }


# ── Internals ──────────────────────────────────────────────────────────

def _get_source(cell: dict) -> str:
    src = cell.get("source", "")
    return "".join(src) if isinstance(src, list) else (src or "")


def _first_heading(src: str):
    for line in src.splitlines():
        s = line.strip()
        if s.startswith("#"):
            return s.lstrip("#").strip() or None
    return None


def _strip_magics(src: str) -> str:
    """Remove line magics and shell escapes so ast can parse the cell."""
    out = []
    for line in src.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("%") or stripped.startswith("!"):
            continue
        out.append(line)
    return "\n".join(out)


def _first_str_arg(call: ast.Call):
    """Return the first string-valued positional or keyword argument."""
    for a in call.args:
        if isinstance(a, ast.Constant) and isinstance(a.value, str):
            return a.value
    for kw in call.keywords:
        if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
            return kw.value.value
    return None


def _analyze_code_cell(src: str) -> dict:
    result = {
        "sql_cell": False,
        "magic": None,
        "imports": [],
        "inputs": [],
        "outputs": [],
        "pandas_ops": [],
        "visual_recipe_hint": None,
    }

    stripped = src.lstrip()
    if stripped.startswith("%%sql"):
        result["sql_cell"] = True
        result["magic"] = "sql"
        result["visual_recipe_hint"] = "sql"
        return result
    if stripped.startswith("%%"):
        first_line = stripped.split("\n", 1)[0]
        result["magic"] = first_line.lstrip("%").split()[0] if first_line.lstrip("%").strip() else None

    clean = _strip_magics(src)
    if not clean.strip():
        result["visual_recipe_hint"] = "python"
        return result

    try:
        tree = ast.parse(clean)
    except SyntaxError:
        result["parse_error"] = True
        result["visual_recipe_hint"] = "python"
        return result

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                result["imports"].append(n.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                result["imports"].append(node.module)
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                name = func.attr
                if name in PANDAS_READ_FUNCS:
                    result["inputs"].append({"kind": name, "arg": _first_str_arg(node)})
                elif name in PANDAS_WRITE_METHODS:
                    result["outputs"].append({"kind": name, "arg": _first_str_arg(node)})
                elif name in OP_TO_RECIPE:
                    result["pandas_ops"].append({"op": name})
            elif isinstance(func, ast.Name) and func.id == "open":
                arg = _first_str_arg(node)
                if arg:
                    result["inputs"].append({"kind": "open", "arg": arg})

    result["visual_recipe_hint"] = _classify(result)
    return result


def _classify(r: dict) -> str:
    if r.get("sql_cell"):
        return "sql"
    ops = [o["op"] for o in r.get("pandas_ops", [])]
    if not ops:
        return "python"
    recipes = {OP_TO_RECIPE.get(op) for op in ops}
    for candidate in RECIPE_PRIORITY:
        if candidate in recipes:
            return candidate
    return "python"
