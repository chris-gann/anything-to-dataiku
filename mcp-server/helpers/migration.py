"""Alteryx-to-Dataiku migration compound helpers.

Provides:
  - Visual recipe builders: create_prepare_recipe, create_group_recipe,
    create_join_recipe, create_stack_recipe, create_sort_recipe,
    create_distinct_recipe, create_sync_recipe, create_window_recipe
  - create_python_recipe (last resort)
  - plan_migration(parsed_workflow): Alteryx→Dataiku mapping that pre-
    builds complete processor payloads, aggregation dicts, join
    conditions, sort columns — and derives semantic dataset names.
  - run_migration_plan(client, pk, plan): creates every recipe in order
    skipping mid-chain schema compute, then does ONE recursive build
    on terminal outputs at the end.
  - Setup: upload_embedded_data, create_project_for_migration, migrate_workflow

Design rules:
  1. Visual recipes over Python.
  2. Consecutive column-ops consolidate into one prepare recipe.
  3. Consolidate across macro tools that reduce to prepare processors
     (Cleanse, DynamicRename, etc.).
"""

import io
import re
import time

from . import alteryx


# =============================================================================
# Alteryx → Dataiku recipe-type mapping
# =============================================================================

# Alteryx tools that reduce to PREPARE processors (no topology change).
# Consecutive runs of these collapse into one prepare recipe.
PREPARE_TOOLS = {
    "Select", "Filter", "Formula", "MultiFieldFormula",
    "DateTime", "RegEx", "FindReplace", "TextToColumns",
    "DynamicRename", "RecordID",
    "Transpose",   # → FoldMultipleColumns processor
    "Cleanse",     # Alteryx macro → equivalent prepare processors
}

RECIPE_TYPE_MAP = {
    "Sort":         "sort",
    "Unique":       "distinct",
    "Sample":       "sampling",
    "Summarize":    "grouping",
    "Join":         "join",
    "JoinMultiple": "join",
    "AppendFields": "join",   # cross-join on a constant key
    "Union":        "vstack",
    "CrossTab":     "pivot",
    "RunningTotal": "window",
}

PYTHON_FALLBACK_TOOLS = {
    "GenerateRows",
    "MultiRowFormula",  # lookbacks — keep as python unless simple
}

IO_TOOLS = {"TextInput", "FileInput", "FileOutput", "Browse"}


# =============================================================================
# Setup helpers
# =============================================================================

def upload_embedded_data(client, project_key, filepath, tool_id, dataset_name):
    """Extract embedded data from an Alteryx TextInput and upload to Dataiku."""
    data = alteryx.extract_embedded_data(filepath, tool_id)
    csv_string = alteryx.data_to_csv(data["columns"], data["rows"])

    project = client.get_project(project_key)
    dataset = project.create_upload_dataset(dataset_name)
    dataset.uploaded_add_file(io.BytesIO(csv_string.encode("utf-8")), "data.csv")
    dataset.autodetect_settings().save()

    return {
        "success": True,
        "dataset_name": dataset_name,
        "num_rows": data["num_rows"],
        "columns": data["columns"],
    }


def create_project_for_migration(client, project_key, project_name,
                                 description="", owner="admin"):
    created_new = True
    if project_key in client.list_project_keys():
        client.get_project(project_key).delete()
        time.sleep(2)
        created_new = False

    client.create_project(project_key, project_name, owner, description=description)
    return {
        "success": True,
        "project_key": project_key,
        "created_new": created_new,
        "url": f"{client.host}/projects/{project_key}/",
    }


# =============================================================================
# Visual recipe builders
# =============================================================================

def _apply_schema(recipe, best_effort=True):
    """Compute+apply schema updates. Swallow errors when upstream isn't built."""
    try:
        updates = recipe.compute_schema_updates()
        if updates.any_action_required():
            updates.apply()
    except Exception:
        if not best_effort:
            raise


def create_prepare_recipe(client, project_key, input_name, output_name, processors,
                          connection="filesystem_managed", recipe_name=None,
                          defer_schema=False):
    """Create a Prepare recipe with a list of processor steps.

    processors: list of {"type": ProcessorType, "params": {...}}
    defer_schema: if True, skip compute_schema_updates (use when upstream
        input dataset hasn't been built yet — run_migration_plan does this).
    """
    project = client.get_project(project_key)
    recipe_name = recipe_name or f"compute_{output_name}"

    builder = project.new_recipe("prepare", recipe_name)
    builder.with_input(input_name)
    builder.with_new_output(output_name, connection)
    recipe = builder.create()

    settings = recipe.get_settings()
    for step in processors:
        settings.add_processor_step(step["type"], step.get("params", {}))
    settings.save()

    if not defer_schema:
        _apply_schema(recipe)

    return {"success": True, "recipe_name": recipe_name,
            "output_dataset": output_name, "step_count": len(processors)}


def create_group_recipe(client, project_key, input_name, output_name, group_keys,
                        aggregations, connection="filesystem_managed",
                        global_count=False, recipe_name=None, defer_schema=False):
    """Create a Grouping recipe.

    group_keys: list of column names.
    aggregations: list of dicts. Each dict supports:
      - column (required)
      - type: "double" | "string" | "bigint" | ...
      - flags: sum, avg, min, max, count, count_distinct, concat, stddev
      - rename_to: optional output column rename

    By default, global_count is False AND per-column count flags are False
    (Dataiku auto-enables both — we strip them so output matches Alteryx
    Summarize behavior).
    """
    project = client.get_project(project_key)
    recipe_name = recipe_name or f"compute_{output_name}"

    builder = project.new_recipe("grouping", recipe_name)
    builder.with_input(input_name)
    builder.with_new_output(output_name, connection)
    if group_keys:
        builder.with_group_key(group_keys[0])
    recipe = builder.create()

    settings = recipe.get_settings()

    rename_map = {}
    for agg in aggregations:
        agg = dict(agg)
        col = agg.pop("column")
        rn = agg.pop("rename_to", None)
        settings.set_column_aggregations(col, **agg)
        if rn:
            for flag in ("sum", "avg", "min", "max", "count", "count_distinct",
                         "stddev", "concat"):
                if agg.get(flag):
                    suffix = {"count_distinct": "distinct", "stddev": "std"}.get(flag, flag)
                    rename_map[f"{col}_{suffix}"] = rn
                    break

    payload = settings.get_json_payload()
    if len(group_keys) > 1:
        payload["keys"] = [{"column": k} for k in group_keys]
    payload["globalCount"] = bool(global_count)
    for v in payload.get("values", []):
        v["count"] = False
    settings.set_json_payload(payload)
    settings.save()

    if not defer_schema:
        _apply_schema(recipe)

    if rename_map and not defer_schema:
        # Append a micro-prepare to rename aggregate outputs to Alteryx names.
        rename_recipe = f"{recipe_name}__rename"
        rename_ds = f"{output_name}__renamed"
        create_prepare_recipe(
            client, project_key, output_name, rename_ds,
            processors=[{"type": "ColumnRenamer",
                         "params": {"renamings": [{"from": k, "to": v}
                                                   for k, v in rename_map.items()]}}],
            connection=connection, recipe_name=rename_recipe,
            defer_schema=defer_schema,
        )
        return {"success": True, "recipe_name": recipe_name,
                "output_dataset": rename_ds, "raw_grouping_output": output_name}

    return {"success": True, "recipe_name": recipe_name,
            "output_dataset": output_name, "pending_renames": rename_map}


def create_join_recipe(client, project_key, inputs, join_conditions, output_name,
                       join_type="LEFT", connection="filesystem_managed",
                       column_selections=None, recipe_name=None, defer_schema=False):
    """Create a Join recipe.

    join_conditions: list of {"left_input", "right_input", "left_column",
        "right_column"}. For cross-joins (AppendFields), pass
        [{"left_input": 0, "right_input": 1, "cross": True}].
    """
    project = client.get_project(project_key)
    recipe_name = recipe_name or f"compute_{output_name}"

    builder = project.new_recipe("join", recipe_name)
    for inp in inputs:
        builder.with_input(inp)
    builder.with_new_output(output_name, connection)
    recipe = builder.create()

    settings = recipe.get_settings()
    settings.raw_joins.clear()

    if column_selections:
        vis = settings.raw_virtual_inputs
        for idx, sel in column_selections.items():
            vi = vis[idx]
            if "mode" in sel:
                vi["columnsSelection"] = {"mode": sel["mode"],
                                          "list": sel.get("list", [])}
            if "prefix" in sel:
                vi["prefix"] = sel["prefix"]

    for cond in join_conditions:
        jt = "CROSS" if cond.get("cross") else join_type
        j = settings.add_join(join_type=jt,
                              input1=cond["left_input"],
                              input2=cond["right_input"])
        if not cond.get("cross"):
            settings.add_condition_to_join(j, type="EQ",
                                           column1=cond["left_column"],
                                           column2=cond["right_column"])

    settings.save()
    if not defer_schema:
        _apply_schema(recipe)

    return {"success": True, "recipe_name": recipe_name, "output_dataset": output_name}


def create_stack_recipe(client, project_key, inputs, output_name,
                        connection="filesystem_managed", recipe_name=None,
                        defer_schema=False):
    project = client.get_project(project_key)
    recipe_name = recipe_name or f"compute_{output_name}"

    builder = project.new_recipe("vstack", recipe_name)
    for inp in inputs:
        builder.with_input(inp)
    builder.with_new_output(output_name, connection)
    recipe = builder.create()
    recipe.get_settings().save()

    if not defer_schema:
        _apply_schema(recipe)
    return {"success": True, "recipe_name": recipe_name, "output_dataset": output_name}


def create_sort_recipe(client, project_key, input_name, output_name, sort_columns,
                       connection="filesystem_managed", recipe_name=None,
                       defer_schema=False):
    project = client.get_project(project_key)
    recipe_name = recipe_name or f"compute_{output_name}"

    builder = project.new_recipe("sort", recipe_name)
    builder.with_input(input_name)
    builder.with_new_output(output_name, connection)
    recipe = builder.create()

    settings = recipe.get_settings()
    payload = settings.get_json_payload() or {}
    payload["sortColumns"] = [
        {"column": s["column"], "ascending": s.get("ascending", True)}
        for s in sort_columns
    ]
    settings.set_json_payload(payload)
    settings.save()

    if not defer_schema:
        _apply_schema(recipe)
    return {"success": True, "recipe_name": recipe_name, "output_dataset": output_name}


def create_distinct_recipe(client, project_key, input_name, output_name,
                           key_columns=None, connection="filesystem_managed",
                           recipe_name=None, defer_schema=False):
    project = client.get_project(project_key)
    recipe_name = recipe_name or f"compute_{output_name}"

    builder = project.new_recipe("distinct", recipe_name)
    builder.with_input(input_name)
    builder.with_new_output(output_name, connection)
    recipe = builder.create()

    settings = recipe.get_settings()
    if key_columns:
        payload = settings.get_json_payload() or {}
        payload["keys"] = list(key_columns)
        settings.set_json_payload(payload)
    settings.save()

    if not defer_schema:
        _apply_schema(recipe)
    return {"success": True, "recipe_name": recipe_name, "output_dataset": output_name}


def create_sync_recipe(client, project_key, input_name, output_name,
                       connection="filesystem_managed", recipe_name=None,
                       defer_schema=False):
    project = client.get_project(project_key)
    recipe_name = recipe_name or f"compute_{output_name}"

    builder = project.new_recipe("sync", recipe_name)
    builder.with_input(input_name)
    builder.with_new_output(output_name, connection)
    recipe = builder.create()
    recipe.get_settings().save()

    if not defer_schema:
        _apply_schema(recipe)
    return {"success": True, "recipe_name": recipe_name, "output_dataset": output_name}


def create_window_recipe(client, project_key, input_name, output_name,
                         aggregations, partition_by=None, order_by=None,
                         connection="filesystem_managed", recipe_name=None,
                         defer_schema=False):
    """Create a Window recipe (for RunningTotal etc).

    aggregations: list of {"column": X, "cumulativeSum": True, "output_name": Y}
    partition_by: list of column names (the Alteryx "group by" on running totals)
    order_by: list of {"column": X, "ascending": True}
    """
    project = client.get_project(project_key)
    recipe_name = recipe_name or f"compute_{output_name}"

    builder = project.new_recipe("window", recipe_name)
    builder.with_input(input_name)
    builder.with_new_output(output_name, connection)
    recipe = builder.create()

    settings = recipe.get_settings()
    payload = settings.get_json_payload() or {}
    window = payload.setdefault("windows", [{}])[0]
    if partition_by:
        window["partitionCols"] = list(partition_by)
    if order_by:
        window["orders"] = [{"column": o["column"],
                             "ascending": o.get("ascending", True)}
                             for o in order_by]
    window["aggregations"] = []
    for agg in aggregations:
        entry = {"column": agg["column"]}
        if agg.get("cumulativeSum"):
            entry["cumulativeSum"] = True
        if agg.get("sum"):
            entry["sum"] = True
        if agg.get("rank"):
            entry["rank"] = True
        if agg.get("rowNumber"):
            entry["rowNumber"] = True
        window["aggregations"].append(entry)
    settings.set_json_payload(payload)
    settings.save()

    if not defer_schema:
        _apply_schema(recipe)
    return {"success": True, "recipe_name": recipe_name, "output_dataset": output_name}


def create_python_recipe(client, project_key, connection, inputs, output_name,
                         code, recipe_name=None):
    """LAST RESORT — prefer visual recipes."""
    project = client.get_project(project_key)
    recipe_name = recipe_name or f"compute_{output_name}"

    mb = project.new_managed_dataset(output_name)
    mb.with_store_into(connection)
    mb.create()

    rb = project.new_recipe("python", recipe_name)
    for inp in inputs:
        rb.with_input(inp)
    rb.with_output(output_name)
    recipe = rb.create()

    settings = recipe.get_settings()
    settings.set_code(code)
    settings.save()

    return {"success": True, "recipe_name": recipe_name, "output_dataset": output_name}


# =============================================================================
# Semantic naming
# =============================================================================

def _slugify(text, max_len=40):
    if not text:
        return ""
    s = re.sub(r"[^a-zA-Z0-9_]+", "_", text.strip().lower())
    s = re.sub(r"_+", "_", s).strip("_")
    return s[:max_len]


def _name_for_source(di):
    """Semantic name for a TextInput/FileInput source."""
    cols = di.get("columns", [])
    hint = cols[0] if cols else None
    if hint:
        return _slugify(hint) + "_input"
    return f"input_tool_{di['tool_id']}"


def _name_for_step(kind, tool_types, tool_ids, hints, annotation=None, used_names=None):
    """Derive a semantic dataset name for a plan step."""
    used_names = used_names or set()
    parts = []

    if annotation:
        ann = annotation.splitlines()[0]
        ann = re.sub(r"[\(\)\[\]\"\']", "", ann)
        slug = _slugify(ann, max_len=32)
        if slug and slug not in used_names:
            return slug

    if kind == "grouping" and hints.get("group_keys"):
        parts.append("by_" + _slugify("_".join(hints["group_keys"][:2]), 24))
        aggs = hints.get("aggregations_materialized") or hints.get("aggregations_raw") or []
        if aggs:
            a0 = aggs[0]
            op = next((k for k in ("sum","avg","min","max","count","count_distinct")
                       if a0.get(k)), a0.get("action", "agg"))
            parts.insert(0, f"{op}_" + _slugify(a0.get("column") or a0.get("field") or "", 20))
    elif kind == "join":
        parts.append("joined")
    elif kind == "vstack":
        parts.append("unioned")
    elif kind == "sort":
        parts.append("sorted")
    elif kind == "distinct":
        parts.append("distinct")
    elif kind == "window":
        parts.append("window")
    elif kind == "pivot":
        parts.append("pivoted")
    elif kind == "prepare":
        primary = tool_types[-1] if tool_types else "prepared"
        parts.append(_slugify(primary))

    base = "_".join(p for p in parts if p) or f"t{tool_ids[0]}"
    candidate = base
    i = 2
    while candidate in used_names:
        candidate = f"{base}_{i}"
        i += 1
    return candidate


# =============================================================================
# Payload materialization
# =============================================================================

_ALTERYX_AGG_TO_FLAG = {
    "Sum": "sum", "Avg": "avg", "Min": "min", "Max": "max",
    "Count": "count", "CountDistinct": "count_distinct",
    "Concat": "concat", "StdDev": "stddev",
    "Sum_Distinct": "sum",  # not perfect but acceptable
    "First": "first", "Last": "last",
    "GroupBy": None,  # handled separately
}


def _translate_ayx_expr(expr):
    """Best-effort Alteryx expression → Dataiku GREL.

    Alteryx uses [Column Name], IIF, IsNull, Trim. GREL uses val("Column Name"),
    if/else, isBlank. Not exhaustive — Claude should verify before running.
    """
    if expr is None:
        return ""
    s = expr
    s = re.sub(r"\[([^\]]+)\]", r'val("\1")', s)
    s = re.sub(r"\bIIF\s*\(", "if(", s, flags=re.IGNORECASE)
    s = re.sub(r"\bIsNull\s*\(", "isBlank(", s, flags=re.IGNORECASE)
    s = s.replace(" = ", " == ")
    return s


def _materialize_prepare(chain, nodes):
    """Build a complete processors list for a consolidated prepare chain."""
    processors = []
    warnings = []

    for tid in chain:
        node = nodes[tid]
        t = node["type"]
        cfg = node.get("config", {})

        if t == "Select":
            renamings = []
            keep_cols = []
            drop_cols = []
            has_unknown_keep = False
            for f in cfg.get("fields", []):
                field = f.get("field")
                if field == "*Unknown":
                    has_unknown_keep = f.get("selected") == "True"
                    continue
                selected = f.get("selected") == "True"
                rename = f.get("rename")
                if rename and rename != field:
                    renamings.append({"from": field, "to": rename})
                if not selected:
                    drop_cols.append(rename or field)
                else:
                    keep_cols.append(rename or field)
            if renamings:
                processors.append({"type": "ColumnRenamer",
                                   "params": {"renamings": renamings}})
            if drop_cols and not has_unknown_keep:
                processors.append({"type": "ColumnsSelector",
                                   "params": {"keep": False, "appliesTo": "COLUMNS",
                                              "columns": drop_cols}})
            elif drop_cols and has_unknown_keep:
                processors.append({"type": "ColumnsSelector",
                                   "params": {"keep": False, "appliesTo": "COLUMNS",
                                              "columns": drop_cols}})

        elif t == "Filter":
            simple = cfg.get("simple") or {}
            expr = cfg.get("expression")
            if expr:
                grel = _translate_ayx_expr(expr)
            elif simple.get("field"):
                op = simple.get("operator", "==")
                val_txt = simple.get("operand", "")
                grel = f'val("{simple["field"]}") {op} "{val_txt}"'
            else:
                grel = None
                warnings.append(f"Filter tool {tid}: could not materialize expression")
            if grel:
                processors.append({"type": "FilterOnCustomFormula",
                                   "params": {"expression": grel, "action": "KEEP"}})

        elif t == "Formula":
            for f in cfg.get("formulas", []):
                field = f.get("field")
                expression = _translate_ayx_expr(f.get("expression", ""))
                processors.append({"type": "CreateColumnWithGREL",
                                   "params": {"column": field,
                                              "expression": expression}})

        elif t == "MultiFieldFormula":
            # Apply the same expression to each selected column — emit one
            # CreateColumnWithGREL per field, overwriting via column name.
            expr = _translate_ayx_expr(cfg.get("expression", ""))
            for field in cfg.get("fields", []):
                processors.append({"type": "CreateColumnWithGREL",
                                   "params": {"column": field,
                                              "expression": expr.replace('val("_CurrentField_")',
                                                                         f'val("{field}")')}})

        elif t == "TextToColumns":
            processors.append({"type": "ColumnSplitter",
                               "params": {"inCol": cfg.get("field"),
                                          "outColPrefix": cfg.get("root_name") or "Part",
                                          "separator": cfg.get("delimiter") or ",",
                                          "limit": int(cfg.get("num_fields") or 2),
                                          "keepEmptyColumns": True}})

        elif t == "DynamicRename":
            warnings.append(f"DynamicRename tool {tid}: manual ColumnRenamer required")

        elif t == "RecordID":
            field = cfg.get("field_name") or "RecordID"
            processors.append({"type": "CreateColumnWithGREL",
                               "params": {"column": field,
                                          "expression": "row_number()"}})

        elif t == "Transpose":
            keys = cfg.get("key_fields", [])
            data_fields = cfg.get("data_fields", [])
            processors.append({"type": "FoldMultipleColumns",
                               "params": {"columns": data_fields,
                                          "nameColumn": "Name",
                                          "valueColumn": "Value"}})
            _ = keys  # kept as identifier columns automatically

        elif t == "Cleanse":
            # Heuristic — actual macro XML varies. Claude should inspect config.
            warnings.append(f"Cleanse macro {tid}: review config manually")

        elif t == "RegEx":
            warnings.append(f"RegEx tool {tid}: inspect config and add ExtractRegex manually")

        elif t == "FindReplace":
            warnings.append(f"FindReplace tool {tid}: inspect config and add FindReplace manually")

        elif t == "DateTime":
            warnings.append(f"DateTime tool {tid}: use ParseDate/FormatDate processors")

    return processors, warnings


def _materialize_grouping(node):
    cfg = node.get("config", {})
    fields = cfg.get("fields", [])
    group_keys = [f["field"] for f in fields if f.get("action") == "GroupBy"]
    aggs = []
    for f in fields:
        action = f.get("action")
        if action in (None, "GroupBy"):
            continue
        flag = _ALTERYX_AGG_TO_FLAG.get(action)
        if not flag:
            continue
        agg = {"column": f["field"], "type": "double", flag: True}
        if f.get("rename") and f.get("rename") != f["field"]:
            agg["rename_to"] = f["rename"]
        aggs.append(agg)
    return group_keys, aggs


def _materialize_sort(node):
    fields = node.get("config", {}).get("sort_fields", [])
    return [{"column": f["field"],
             "ascending": (f.get("order", "Ascending") == "Ascending")}
             for f in fields]


def _materialize_join_conditions(node):
    """Map Alteryx Join fields to Dataiku join_conditions list."""
    join_fields = node.get("config", {}).get("join_fields", [])
    lefts = [j["field"] for j in join_fields if j.get("connection") == "Left"]
    rights = [j["field"] for j in join_fields if j.get("connection") == "Right"]
    pairs = []
    for lc, rc in zip(lefts, rights):
        pairs.append({"left_input": 0, "right_input": 1,
                      "left_column": lc, "right_column": rc})
    return pairs


def _materialize_window(node):
    cfg = node.get("config", {})
    partition = cfg.get("group_by") or []
    aggs = [{"column": f, "cumulativeSum": True} for f in cfg.get("running_fields", [])]
    return partition, aggs


# =============================================================================
# Planning
# =============================================================================

def _classify_tool(tool_type):
    if tool_type in IO_TOOLS:
        return "io"
    if tool_type in PREPARE_TOOLS:
        return "prepare"
    if tool_type in RECIPE_TYPE_MAP:
        return RECIPE_TYPE_MAP[tool_type]
    if tool_type in PYTHON_FALLBACK_TOOLS:
        return "python"
    return "python"


def plan_migration(parsed_workflow):
    """Produce a consolidated recipe plan with materialized payloads.

    Each step carries everything needed to call a create_*_recipe helper —
    no further XML reading required in the common case.

    Returns:
      {
        "steps": [...],
        "name_map": {tool_id → semantic dataset name},
        "terminals": [dataset names of terminal outputs],
        "warnings": [...],
        "summary": "..."
      }
    """
    nodes = {n["id"]: n for n in parsed_workflow["nodes"]}
    flow_order = parsed_workflow["flow_order"]
    connections = parsed_workflow["connections"]

    preds = {nid: [] for nid in nodes}
    succs = {nid: [] for nid in nodes}
    for c in connections:
        if c["from_id"] in nodes and c["to_id"] in nodes:
            preds[c["to_id"]].append(c["from_id"])
            succs[c["from_id"]].append(c["to_id"])

    steps = []
    warnings = []
    consumed = set()
    name_map = {}   # tool_id (last in chain) → output dataset name
    used_names = set()

    def assign_name(step, fallback_id):
        name = _name_for_step(
            kind=step["kind"],
            tool_types=step.get("tool_types", []),
            tool_ids=step.get("tool_ids", [fallback_id]),
            hints=step.get("hints", {}),
            annotation=step.get("annotation"),
            used_names=used_names,
        )
        used_names.add(name)
        return name

    for nid in flow_order:
        if nid in consumed:
            continue
        node = nodes[nid]
        tool_type = node["type"]
        kind = _classify_tool(tool_type)
        annotation = node.get("annotation", "")

        if kind == "io":
            if tool_type in ("TextInput", "FileInput"):
                # Source datasets are uploaded separately — record the name.
                continue
            if tool_type in ("FileOutput", "Browse"):
                up = preds[nid][0] if preds[nid] else None
                steps.append({
                    "kind": "output", "tool_ids": [nid],
                    "tool_types": [tool_type],
                    "inputs": preds[nid],
                    "upstream_tool_id": up,
                    "description": f"Terminal output after tool {up}",
                    "hints": {},
                })
            continue

        if kind == "prepare":
            chain = [nid]
            cursor = nid
            while True:
                children = [s for s in succs[cursor] if s in nodes and s not in consumed]
                if len(children) != 1:
                    break
                child = children[0]
                if _classify_tool(nodes[child]["type"]) != "prepare":
                    break
                if len(preds[child]) != 1:
                    break
                chain.append(child)
                cursor = child
            for tid in chain[1:]:
                consumed.add(tid)

            tool_types = [nodes[t]["type"] for t in chain]
            processors, prep_warnings = _materialize_prepare(chain, nodes)
            warnings.extend(prep_warnings)

            step = {
                "kind": "prepare",
                "tool_ids": chain,
                "tool_types": tool_types,
                "inputs": preds[chain[0]],
                "annotation": annotation,
                "description": f"Prepare: {' → '.join(tool_types)}",
                "processors": processors,
                "hints": {},
            }
            step["output_name"] = assign_name(step, chain[-1])
            name_map[chain[-1]] = step["output_name"]
            steps.append(step)
            continue

        if kind == "grouping":
            group_keys, aggs = _materialize_grouping(node)
            step = {
                "kind": "grouping", "tool_ids": [nid],
                "tool_types": [tool_type], "inputs": preds[nid],
                "annotation": annotation,
                "description": f"Group by {group_keys or '<none>'}",
                "group_keys": group_keys,
                "aggregations": aggs,
                "hints": {"group_keys": group_keys,
                          "aggregations_materialized": aggs},
            }
            step["output_name"] = assign_name(step, nid)
            name_map[nid] = step["output_name"]
            steps.append(step)
            continue

        if kind == "join":
            if tool_type == "AppendFields":
                step_inputs = preds[nid]
                step = {
                    "kind": "join", "tool_ids": [nid],
                    "tool_types": [tool_type], "inputs": step_inputs,
                    "annotation": annotation,
                    "description": "AppendFields → cross join",
                    "join_conditions": [{"left_input": 0, "right_input": 1,
                                          "cross": True}],
                    "join_type": "LEFT",
                    "hints": {},
                }
            else:
                step = {
                    "kind": "join", "tool_ids": [nid],
                    "tool_types": [tool_type], "inputs": preds[nid],
                    "annotation": annotation,
                    "description": "Join",
                    "join_conditions": _materialize_join_conditions(node),
                    "join_type": "LEFT",
                    "hints": {"join_fields": node.get("config", {}).get("join_fields", [])},
                }
            step["output_name"] = assign_name(step, nid)
            name_map[nid] = step["output_name"]
            steps.append(step)
            continue

        if kind == "sort":
            step = {
                "kind": "sort", "tool_ids": [nid],
                "tool_types": [tool_type], "inputs": preds[nid],
                "annotation": annotation,
                "description": "Sort",
                "sort_columns": _materialize_sort(node),
                "hints": {},
            }
            step["output_name"] = assign_name(step, nid)
            name_map[nid] = step["output_name"]
            steps.append(step)
            continue

        if kind == "distinct":
            step = {
                "kind": "distinct", "tool_ids": [nid],
                "tool_types": [tool_type], "inputs": preds[nid],
                "annotation": annotation,
                "description": "Distinct", "hints": {},
            }
            step["output_name"] = assign_name(step, nid)
            name_map[nid] = step["output_name"]
            steps.append(step)
            continue

        if kind == "vstack":
            step = {
                "kind": "vstack", "tool_ids": [nid],
                "tool_types": [tool_type], "inputs": preds[nid],
                "annotation": annotation,
                "description": f"Union of {len(preds[nid])} inputs", "hints": {},
            }
            step["output_name"] = assign_name(step, nid)
            name_map[nid] = step["output_name"]
            steps.append(step)
            continue

        if kind == "window":
            partition, aggs = _materialize_window(node)
            step = {
                "kind": "window", "tool_ids": [nid],
                "tool_types": [tool_type], "inputs": preds[nid],
                "annotation": annotation,
                "description": "Window (RunningTotal)",
                "partition_by": partition,
                "aggregations": aggs,
                "hints": {"config": node.get("config", {})},
            }
            step["output_name"] = assign_name(step, nid)
            name_map[nid] = step["output_name"]
            steps.append(step)
            continue

        if kind in ("sampling", "pivot"):
            step = {
                "kind": kind, "tool_ids": [nid],
                "tool_types": [tool_type], "inputs": preds[nid],
                "annotation": annotation,
                "description": f"{kind} from {tool_type}",
                "hints": {"config": node.get("config", {})},
            }
            step["output_name"] = assign_name(step, nid)
            name_map[nid] = step["output_name"]
            steps.append(step)
            continue

        # python fallback
        warnings.append(f"Tool {nid} ({tool_type}) → Python recipe required.")
        step = {
            "kind": "python", "tool_ids": [nid],
            "tool_types": [tool_type], "inputs": preds[nid],
            "annotation": annotation,
            "description": f"Python for {tool_type}",
            "hints": {"config": node.get("config", {})},
        }
        step["output_name"] = assign_name(step, nid)
        name_map[nid] = step["output_name"]
        steps.append(step)

    # Resolve inputs: tool_ids → dataset names (from name_map + sources)
    terminals = []
    for step in steps:
        resolved = []
        for tid in step["inputs"]:
            if tid in name_map:
                resolved.append(name_map[tid])
            else:
                resolved.append(f"input_tool_{tid}")
        step["input_datasets"] = resolved

    # Identify terminal outputs: datasets that are nobody's input (except for
    # explicit "output" kind steps which point at their upstream).
    produced = {s.get("output_name") for s in steps if s.get("output_name")}
    consumed_ds = set()
    for s in steps:
        for inp in s.get("input_datasets", []):
            consumed_ds.add(inp)
    terminals = sorted(p for p in produced if p and p not in consumed_ds)

    counts = {}
    for s in steps:
        counts[s["kind"]] = counts.get(s["kind"], 0) + 1

    return {
        "steps": steps,
        "name_map": name_map,
        "terminals": terminals,
        "warnings": warnings,
        "summary": ", ".join(f"{k}: {v}" for k, v in sorted(counts.items())),
    }


# =============================================================================
# Execution
# =============================================================================

def run_migration_plan(client, project_key, plan,
                       connection="filesystem_managed", build=True, timeout=900):
    """Create every recipe in the plan (deferring schema compute), then do
    ONE recursive build on the terminal outputs.

    Returns: {created: [...], skipped: [...], build_result: {...}, warnings: [...]}
    """
    created = []
    skipped = []
    warnings = list(plan.get("warnings", []))

    for step in plan["steps"]:
        kind = step["kind"]
        if kind == "output":
            continue  # no recipe; handled by terminal build

        out = step["output_name"]
        inputs = step["input_datasets"]

        try:
            if kind == "prepare":
                r = create_prepare_recipe(client, project_key, inputs[0], out,
                                          step["processors"], connection=connection,
                                          defer_schema=True)
            elif kind == "grouping":
                r = create_group_recipe(client, project_key, inputs[0], out,
                                        step["group_keys"], step["aggregations"],
                                        connection=connection, defer_schema=True)
            elif kind == "join":
                r = create_join_recipe(client, project_key, inputs,
                                       step["join_conditions"], out,
                                       join_type=step.get("join_type", "LEFT"),
                                       connection=connection, defer_schema=True)
            elif kind == "vstack":
                r = create_stack_recipe(client, project_key, inputs, out,
                                        connection=connection, defer_schema=True)
            elif kind == "sort":
                r = create_sort_recipe(client, project_key, inputs[0], out,
                                       step["sort_columns"], connection=connection,
                                       defer_schema=True)
            elif kind == "distinct":
                r = create_distinct_recipe(client, project_key, inputs[0], out,
                                           connection=connection, defer_schema=True)
            elif kind == "window":
                r = create_window_recipe(client, project_key, inputs[0], out,
                                         step["aggregations"],
                                         partition_by=step.get("partition_by"),
                                         connection=connection, defer_schema=True)
            elif kind == "python":
                skipped.append({
                    "step": step,
                    "reason": "Python recipe — Claude must provide the code manually",
                })
                continue
            else:
                skipped.append({"step": step, "reason": f"Unsupported kind: {kind}"})
                continue
            created.append({"step_kind": kind, "output": out, "recipe": r})
        except Exception as e:
            warnings.append(f"Failed to create {kind} for {out}: {e}")
            skipped.append({"step": step, "reason": str(e)})

    build_result = None
    if build and plan.get("terminals"):
        from . import jobs
        build_result = jobs.build_and_wait(client, project_key,
                                           plan["terminals"], timeout=timeout)

    return {
        "created": created,
        "skipped": skipped,
        "warnings": warnings,
        "terminals": plan.get("terminals", []),
        "build_result": build_result,
    }


# =============================================================================
# High-level
# =============================================================================

def migrate_workflow(client, project_key, project_name, filepath,
                     connection="filesystem_managed", owner="admin"):
    """Parse workflow, create project, upload data, and produce a materialized plan.

    After this returns, call run_migration_plan(client, project_key,
    result["plan"]) to create all recipes and build. Python steps are
    returned in `skipped` and need manual code.
    """
    wf = alteryx.parse_workflow(filepath)

    proj = create_project_for_migration(
        client, project_key, project_name,
        description=wf.get("description", f"Migrated from Alteryx: {wf.get('name', '')}"),
        owner=owner,
    )

    uploaded = []
    input_name_map = {}
    for di in wf["data_inputs"]:
        ds_name = _name_for_source(di)
        result = upload_embedded_data(client, project_key, filepath,
                                      di["tool_id"], ds_name)
        uploaded.append(result)
        input_name_map[di["tool_id"]] = ds_name

    plan = plan_migration(wf)

    # Rewrite input_datasets that point at input_tool_{id} to the real names.
    for step in plan["steps"]:
        step["input_datasets"] = [
            input_name_map.get(
                tid if (tid := _parse_tool_id_ds(inp)) else "",
                inp,
            )
            for inp in step["input_datasets"]
        ]

    plan["input_name_map"] = input_name_map

    return {
        "success": True,
        "project": proj,
        "workflow_summary": {
            "name": wf.get("name"),
            "node_count": wf["node_count"],
            "connection_count": wf["connection_count"],
        },
        "uploaded_datasets": uploaded,
        "plan": plan,
    }


def _parse_tool_id_ds(name):
    m = re.match(r"^input_tool_(\d+)$", name or "")
    return m.group(1) if m else None
