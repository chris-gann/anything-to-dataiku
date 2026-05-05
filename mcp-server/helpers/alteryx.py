"""Alteryx .yxmd workflow parsing utilities.

Parses Alteryx Designer XML workflows into structured data that Claude
can reason about without reading raw XML (saves thousands of tokens).
"""

import xml.etree.ElementTree as ET
from typing import Optional


# ── Alteryx plugin name → friendly tool type ────────────────────────────

PLUGIN_MAP = {
    "AlteryxBasePluginsGui.TextInput.TextInput": "TextInput",
    "AlteryxBasePluginsGui.DbFileInput.DbFileInput": "FileInput",
    "AlteryxBasePluginsGui.DbFileOutput.DbFileOutput": "FileOutput",
    "AlteryxBasePluginsGui.BrowseV2.BrowseV2": "Browse",
    "AlteryxBasePluginsGui.AlteryxSelect.AlteryxSelect": "Select",
    "AlteryxBasePluginsGui.Filter.Filter": "Filter",
    "AlteryxBasePluginsGui.Formula.Formula": "Formula",
    "AlteryxBasePluginsGui.Join.Join": "Join",
    "AlteryxBasePluginsGui.TextToColumns.TextToColumns": "TextToColumns",
    "AlteryxBasePluginsGui.GenerateRows.GenerateRows": "GenerateRows",
    "AlteryxBasePluginsGui.Sort.Sort": "Sort",
    "AlteryxBasePluginsGui.Sample.Sample": "Sample",
    "AlteryxBasePluginsGui.Unique.Unique": "Unique",
    "AlteryxBasePluginsGui.Transpose.Transpose": "Transpose",
    "AlteryxBasePluginsGui.CrossTab.CrossTab": "CrossTab",
    "AlteryxBasePluginsGui.RegEx.RegEx": "RegEx",
    "AlteryxBasePluginsGui.DateTime.DateTime": "DateTime",
    "AlteryxBasePluginsGui.MultiFieldFormula.MultiFieldFormula": "MultiFieldFormula",
    "AlteryxBasePluginsGui.MultiRowFormula.MultiRowFormula": "MultiRowFormula",
    "AlteryxBasePluginsGui.RecordID.RecordID": "RecordID",
    "AlteryxBasePluginsGui.RunningTotal.RunningTotal": "RunningTotal",
    "AlteryxBasePluginsGui.DynamicRename.DynamicRename": "DynamicRename",
    "AlteryxBasePluginsGui.AppendFields.AppendFields": "AppendFields",
    "AlteryxBasePluginsGui.JoinMultiple.JoinMultiple": "JoinMultiple",
    "AlteryxBasePluginsGui.FindReplace.FindReplace": "FindReplace",
    "AlteryxBasePluginsGui.Union.Union": "Union",
    "AlteryxSpatialPluginsGui.Summarize.Summarize": "Summarize",
    "AlteryxGuiToolkit.TextBox.TextBox": "TextBox",
    "AlteryxGuiToolkit.ToolContainer.ToolContainer": "ToolContainer",
}


def _get_tool_type(gui_settings) -> str:
    """Extract a clean tool type name from GuiSettings Plugin attribute."""
    plugin = gui_settings.get("Plugin", "")
    return PLUGIN_MAP.get(plugin, plugin.split(".")[-1] if "." in plugin else plugin)


def _parse_config_summary(tool_type: str, config_elem) -> dict:
    """Extract the key configuration details for a tool type.

    Returns a concise dict rather than the full XML structure.
    """
    summary = {}

    if config_elem is None:
        return summary

    if tool_type == "TextInput":
        num_rows = config_elem.findtext("NumRows") or config_elem.find("NumRows")
        if num_rows is not None:
            val = num_rows if isinstance(num_rows, str) else num_rows.get("value", "")
            summary["num_rows"] = val
        fields = config_elem.findall(".//Field")
        summary["columns"] = [f.get("name") for f in fields if f.get("name")]

    elif tool_type == "TextToColumns":
        summary["field"] = config_elem.findtext("Field")
        summary["num_fields"] = config_elem.findtext("NumFields")
        nr = config_elem.find("NumFields")
        if nr is not None:
            summary["num_fields"] = nr.get("value", config_elem.findtext("NumFields"))
        summary["delimiter"] = None
        delim = config_elem.find("Delimeters")
        if delim is not None:
            summary["delimiter"] = delim.get("value")
        summary["root_name"] = config_elem.findtext("RootName")

    elif tool_type == "Select":
        fields = config_elem.findall(".//SelectField")
        summary["fields"] = []
        for f in fields:
            entry = {
                "field": f.get("field"),
                "selected": f.get("selected"),
            }
            if f.get("rename"):
                entry["rename"] = f.get("rename")
            if f.get("type"):
                entry["type"] = f.get("type")
            summary["fields"].append(entry)

    elif tool_type == "GenerateRows":
        summary["create_field"] = config_elem.findtext("CreateField_Name")
        summary["field_type"] = config_elem.findtext("CreateField_Type")
        summary["init_expression"] = config_elem.findtext("Expression_Init")
        summary["condition"] = config_elem.findtext("Expression_Cond")
        summary["loop_expression"] = config_elem.findtext("Expression_Loop")

    elif tool_type == "Join":
        join_infos = config_elem.findall(".//JoinInfo")
        summary["join_fields"] = []
        for ji in join_infos:
            connection = ji.get("connection", "")
            field_elem = ji.find("Field")
            field_name = field_elem.get("field") if field_elem is not None else ""
            summary["join_fields"].append({
                "connection": connection,
                "field": field_name,
            })

    elif tool_type == "Summarize":
        fields = config_elem.findall(".//SummarizeField")
        summary["fields"] = []
        for f in fields:
            summary["fields"].append({
                "field": f.get("field"),
                "action": f.get("action"),
                "rename": f.get("rename"),
            })

    elif tool_type == "Formula":
        fields = config_elem.findall(".//FormulaField")
        summary["formulas"] = []
        for f in fields:
            summary["formulas"].append({
                "field": f.get("field"),
                "expression": f.get("expression"),
                "type": f.get("type"),
                "size": f.get("size"),
            })

    elif tool_type == "Filter":
        summary["mode"] = config_elem.findtext("Mode")
        summary["expression"] = config_elem.findtext("Expression")
        # Simple-mode filters store config in <Simple>
        simple = config_elem.find("Simple")
        if simple is not None:
            summary["simple"] = {
                "field": simple.findtext("Field"),
                "operator": simple.findtext("Operator"),
                "operand": simple.findtext("Operands/Operand"),
            }

    elif tool_type == "Sort":
        fields = config_elem.findall(".//Field")
        summary["sort_fields"] = []
        for f in fields:
            summary["sort_fields"].append({
                "field": f.get("field"),
                "order": f.get("order"),
            })

    elif tool_type == "Union":
        summary["mode"] = config_elem.findtext("Mode")

    elif tool_type == "Transpose":
        key_fields = config_elem.findall(".//KeyFields/Field")
        data_fields = config_elem.findall(".//DataFields/Field")
        summary["key_fields"] = [f.get("field") for f in key_fields]
        summary["data_fields"] = [
            f.get("field") for f in data_fields
            if f.get("selected") == "True"
        ]

    elif tool_type == "RunningTotal":
        group_fields = config_elem.findall(".//GroupByFields/Field")
        running_fields = config_elem.findall(".//RunningTotalFields/Field")
        summary["group_by"] = [f.get("field") for f in group_fields]
        summary["running_fields"] = [f.get("field") for f in running_fields]

    elif tool_type == "RecordID":
        summary["field_name"] = config_elem.findtext("FieldName") or "RecordID"
        summary["start_value"] = config_elem.findtext("StartValue") or "1"

    elif tool_type == "CrossTab":
        group_fields = config_elem.findall(".//GroupFields/Field")
        summary["group_fields"] = [f.get("field") for f in group_fields]
        summary["header_field"] = config_elem.findtext("HeaderField")
        summary["data_field"] = config_elem.findtext("DataField")
        summary["method"] = config_elem.findtext("Methods/Method")

    elif tool_type == "MultiFieldFormula":
        fields = config_elem.findall(".//Fields/Field")
        summary["fields"] = [f.get("name") for f in fields if f.get("selected") == "True"]
        summary["expression"] = config_elem.findtext("Expression")

    elif tool_type in ("FileInput", "FileOutput"):
        summary["file"] = config_elem.findtext("File")

    return summary


def parse_workflow(filepath: str) -> dict:
    """Parse an Alteryx .yxmd workflow into a structured summary.

    Returns a dict with:
      - name: workflow name
      - description: workflow description text (from TextBox annotations)
      - nodes: list of tool nodes with id, type, config summary, annotation
      - connections: list of {from_id, from_anchor, to_id, to_anchor}
      - data_inputs: list of TextInput node IDs with their column info
      - flow_order: topologically sorted node IDs (data flow order)

    This replaces reading raw XML, saving thousands of tokens.
    """
    tree = ET.parse(filepath)
    root = tree.getroot()

    # ── Parse nodes ──────────────────────────────────────────────────
    nodes = []
    data_inputs = []
    description_texts = []

    for node_elem in root.findall(".//Nodes/Node"):
        tool_id = node_elem.get("ToolID")
        gui = node_elem.find("GuiSettings")
        tool_type = _get_tool_type(gui.attrib) if gui is not None else "Unknown"

        # Get annotation text
        annotation = ""
        ann_elem = node_elem.find(".//Annotation/AnnotationText")
        if ann_elem is not None and ann_elem.text:
            annotation = ann_elem.text.strip()

        # Get config
        config_elem = node_elem.find(".//Configuration")
        config_summary = _parse_config_summary(tool_type, config_elem)

        # Skip pure UI elements (TextBox, ToolContainer) from the flow nodes
        if tool_type == "TextBox":
            # But capture description text from TextBoxes
            text_elem = config_elem.find("Text") if config_elem is not None else None
            if text_elem is not None and text_elem.text and len(text_elem.text) > 20:
                description_texts.append(text_elem.text.strip())
            continue
        if tool_type == "ToolContainer":
            continue

        node_info = {
            "id": tool_id,
            "type": tool_type,
            "config": config_summary,
        }
        if annotation:
            node_info["annotation"] = annotation

        nodes.append(node_info)

        # Track data inputs
        if tool_type == "TextInput":
            data_inputs.append({
                "tool_id": tool_id,
                "columns": config_summary.get("columns", []),
                "num_rows": config_summary.get("num_rows", "unknown"),
            })

    # ── Parse connections ────────────────────────────────────────────
    connections = []
    for conn_elem in root.findall(".//Connections/Connection"):
        origin = conn_elem.find("Origin")
        dest = conn_elem.find("Destination")
        if origin is not None and dest is not None:
            connections.append({
                "from_id": origin.get("ToolID"),
                "from_anchor": origin.get("Connection"),
                "to_id": dest.get("ToolID"),
                "to_anchor": dest.get("Connection"),
            })

    # ── Topological sort for flow order ──────────────────────────────
    node_ids = {n["id"] for n in nodes}
    adjacency = {nid: [] for nid in node_ids}
    in_degree = {nid: 0 for nid in node_ids}

    for c in connections:
        if c["from_id"] in node_ids and c["to_id"] in node_ids:
            adjacency[c["from_id"]].append(c["to_id"])
            in_degree[c["to_id"]] += 1

    # Kahn's algorithm
    queue = [nid for nid in node_ids if in_degree[nid] == 0]
    flow_order = []
    while queue:
        queue.sort()  # Deterministic order
        nid = queue.pop(0)
        flow_order.append(nid)
        for neighbor in adjacency[nid]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    # ── Workflow metadata ────────────────────────────────────────────
    meta_name = root.findtext(".//MetaInfo/Name") or ""
    description = "\n".join(description_texts) if description_texts else ""

    return {
        "name": meta_name,
        "description": description,
        "nodes": nodes,
        "connections": connections,
        "data_inputs": data_inputs,
        "flow_order": flow_order,
        "node_count": len(nodes),
        "connection_count": len(connections),
    }


def extract_embedded_data(filepath: str, tool_id: str) -> dict:
    """Extract embedded data from a TextInput node.

    Returns a dict with:
      - columns: list of column names
      - rows: list of row dicts (column_name -> value)
      - num_rows: count of rows

    Use this to pull data out of .yxmd files for upload to Dataiku.
    """
    tree = ET.parse(filepath)
    root = tree.getroot()

    for node_elem in root.findall(".//Nodes/Node"):
        if node_elem.get("ToolID") == str(tool_id):
            config = node_elem.find(".//Configuration")
            if config is None:
                raise ValueError(f"No Configuration found for ToolID={tool_id}")

            fields = config.findall(".//Field")
            col_names = [f.get("name") for f in fields]

            rows = []
            for r in config.findall(".//Data/r"):
                cells = r.findall("c")
                row = {}
                for i, c in enumerate(cells):
                    if i < len(col_names):
                        row[col_names[i]] = c.text if c.text else ""
                rows.append(row)

            return {
                "columns": col_names,
                "rows": rows,
                "num_rows": len(rows),
            }

    raise ValueError(f"Could not find TextInput node with ToolID={tool_id}")


def get_workflow_summary(filepath: str) -> str:
    """Get a human-readable summary of an Alteryx workflow.

    Returns a formatted string describing the workflow's data flow,
    suitable for including in a prompt or printing.
    """
    wf = parse_workflow(filepath)

    lines = []
    lines.append(f"Workflow: {wf['name'] or 'Unnamed'}")
    if wf["description"]:
        lines.append(f"Description: {wf['description'][:500]}")
    lines.append(f"Nodes: {wf['node_count']}, Connections: {wf['connection_count']}")
    lines.append("")

    # Data inputs
    if wf["data_inputs"]:
        lines.append("Data Inputs:")
        for di in wf["data_inputs"]:
            lines.append(f"  Tool {di['tool_id']}: {di['num_rows']} rows, "
                         f"columns: {', '.join(di['columns'])}")
        lines.append("")

    # Build node lookup
    node_map = {n["id"]: n for n in wf["nodes"]}

    # Flow order with descriptions
    lines.append("Data Flow:")
    for nid in wf["flow_order"]:
        node = node_map.get(nid)
        if not node:
            continue
        desc = node.get("annotation", "")
        config_hint = ""

        # Add key config details inline
        cfg = node.get("config", {})
        if node["type"] == "TextToColumns" and cfg.get("delimiter"):
            config_hint = f" (split '{cfg['field']}' on '{cfg['delimiter']}')"
        elif node["type"] == "Select" and cfg.get("fields"):
            renames = [f"{f['field']}→{f['rename']}" for f in cfg["fields"]
                       if f.get("rename") and f.get("rename") != f.get("field")]
            if renames:
                config_hint = f" (rename: {', '.join(renames)})"
        elif node["type"] == "GenerateRows" and cfg.get("create_field"):
            config_hint = (f" (create '{cfg['create_field']}': "
                           f"init={cfg.get('init_expression')}, "
                           f"while={cfg.get('condition')}, "
                           f"loop={cfg.get('loop_expression')})")
        elif node["type"] == "Join" and cfg.get("join_fields"):
            pairs = [f"{jf['connection']}:{jf['field']}" for jf in cfg["join_fields"]]
            config_hint = f" (on {', '.join(pairs)})"
        elif node["type"] == "Summarize" and cfg.get("fields"):
            groups = [f["field"] for f in cfg["fields"] if f.get("action") == "GroupBy"]
            aggs = [f"{f['action']}({f['field']})" for f in cfg["fields"]
                    if f.get("action") != "GroupBy"]
            config_hint = f" (group by {', '.join(groups)}; {', '.join(aggs)})"

        annotation_text = f" — {desc}" if desc else ""
        lines.append(f"  [{nid}] {node['type']}{config_hint}{annotation_text}")

    # Connections as arrows
    lines.append("")
    lines.append("Connections:")
    for c in wf["connections"]:
        anchor = f"[{c['from_anchor']}→{c['to_anchor']}]" if c["from_anchor"] != "Output" or c["to_anchor"] != "Input" else ""
        lines.append(f"  {c['from_id']} → {c['to_id']} {anchor}")

    return "\n".join(lines)


def data_to_csv(columns: list, rows: list) -> str:
    """Convert extracted embedded data to a CSV string.

    Args:
        columns: list of column names
        rows: list of row dicts (as returned by extract_embedded_data)

    Returns:
        CSV formatted string
    """
    import csv
    from io import StringIO

    buf = StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def get_slim_xml(filepath: str, sample_rows: int = 3) -> str:
    """Return workflow XML stripped of noise, keeping all logic.

    Removes: embedded data rows (beyond sample_rows), GUI positions,
    EngineSettings, MetaInfo, document-level Properties.

    Keeps: all tool Configurations, Annotations, Connections — everything
    Claude needs to understand and migrate the workflow.

    Args:
        filepath: Path to .yxmd file
        sample_rows: Number of embedded data rows to keep per TextInput (default 3)

    Returns:
        Cleaned XML string (~15-25K tokens for a typical workflow)
    """
    import copy
    tree = ET.parse(filepath)
    root = copy.deepcopy(tree.getroot())

    for node in root.findall('.//Node'):
        config = node.find('.//Configuration')
        if config is not None:
            data = config.find('Data')
            if data is not None:
                rows = data.findall('r')
                num_rows_elem = config.find('NumRows')
                total = int(num_rows_elem.get('value', '0')) if num_rows_elem is not None else len(rows)
                for row in rows[sample_rows:]:
                    data.remove(row)
                if total > sample_rows:
                    data.append(ET.Comment(f" {total} total rows, showing first {sample_rows} "))

        for parent in node.iter():
            for child in list(parent):
                if child.tag == 'MetaInfo':
                    parent.remove(child)

        es = node.find('EngineSettings')
        if es is not None:
            node.remove(es)

        gs = node.find('GuiSettings')
        if gs is not None:
            pos = gs.find('Position')
            if pos is not None:
                gs.remove(pos)

    props = root.find('Properties')
    if props is not None:
        root.remove(props)

    return ET.tostring(root, encoding='unicode', xml_declaration=True)
