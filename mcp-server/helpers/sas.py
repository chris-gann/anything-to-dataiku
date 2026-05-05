"""SAS .sas program parsing utilities.

Parses SAS programs into structured "steps" (DATA / PROC / MACRO def /
MACRO call / LIBNAME / %INCLUDE) with detected inputs/outputs and
visual-recipe hints. Also walks a SAS project directory to find the
.xpt / .sas7bdat data files and build the cross-file dataflow graph.

Design: parser surfaces structure, Claude decides. NO macro expansion —
the parser flags macro definitions and calls; Claude reads the macro
body and decides per-call how to translate (often as parameterized
visual recipes, sometimes as a single Python recipe).

SAS is not a regular language, but its top-level step structure
(data ... run; / proc X ... run|quit; / %macro ... %mend) is regular
enough for line-level scanning. We do not attempt full parsing.
"""

import re
from pathlib import Path


# ── PROC name → recipe hint ────────────────────────────────────────────
# Hints only — Claude makes final decisions based on step content.
PROC_RECIPE_HINT = {
    "sort": "sort",
    "sql": "sql",                # often decomposable into group/join — Claude decides
    "freq": "grouping",          # counts/frequencies; with `exact` → python
    "means": "grouping",
    "summary": "grouping",
    "univariate": "grouping",
    "tabulate": "pivot",
    "transpose": "pivot",
    "format": "prepare",         # FORMAT defs become value-mapping processors
    "datasets": "sync",          # mostly metadata ops; often skip
    "append": "vstack",
    "import": "sync",
    "export": "sync",
    "print": "skip",             # output only
    "contents": "skip",          # metadata only
    "report": "skip",            # output only
    "ttest": "python",
    "anova": "python",
    "glm": "python",
    "reg": "python",
    "logistic": "python",
    "lifetest": "python",
    "phreg": "python",
    "mixed": "python",
    "genmod": "python",
}

# DATA-step features → contribution to recipe hint
DATA_FEATURE_HINT = {
    "merge": "join",
    "by_first_last": "window",       # uses first./last. — stateful row logic
    "retain": "window",              # stateful across rows
    "do_loop": "python",             # explicit row loop
    "array": "python",               # arrays usually mean python
    "set_only": "sync",              # data X; set Y; run; with no transforms
    "if_then": "prepare",
    "formula": "prepare",
    "format_label": "prepare",
    "keep_drop": "prepare",
}


# ── Top-level step regexes ─────────────────────────────────────────────
RE_DATA_START = re.compile(r"^\s*data\s+([^;/(]+)", re.IGNORECASE)
RE_PROC_START = re.compile(r"^\s*proc\s+(\w+)", re.IGNORECASE)
RE_MACRO_DEF = re.compile(r"^\s*%macro\s+(\w+)\s*(?:\((.*?)\))?\s*;?", re.IGNORECASE)
RE_MEND = re.compile(r"^\s*%mend\b", re.IGNORECASE)
RE_RUN_QUIT = re.compile(r"\b(run|quit)\s*;", re.IGNORECASE)
RE_ENDSAS = re.compile(r"^\s*endsas\s*;", re.IGNORECASE)
RE_LIBNAME = re.compile(r"^\s*libname\s+(\w+)\s+(.+?);", re.IGNORECASE)
RE_INCLUDE = re.compile(r'^\s*%include\s+["\']([^"\']+)["\']', re.IGNORECASE)
RE_MACRO_CALL = re.compile(r"^\s*%(\w+)\s*(?:\((.*?)\))?\s*;", re.IGNORECASE)
# %words that are NOT user macro calls
MACRO_CONTROL_WORDS = {
    "macro", "mend", "let", "include", "if", "else", "do", "end", "then",
    "global", "local", "put", "abort", "return", "goto", "syscall",
    "sysexec", "window", "display", "input",
}

# Inside-step extractors (inputs / outputs)
RE_SET = re.compile(r"\bset\s+([A-Za-z0-9_.\s]+?)(?:\(|;|by\s|where\s|keep\s|drop\s|rename\s)", re.IGNORECASE)
RE_MERGE = re.compile(r"\bmerge\s+([A-Za-z0-9_.\s()=,'\"]+?);", re.IGNORECASE)
RE_DATA_OUT = re.compile(r"^\s*data\s+([A-Za-z0-9_.]+(?:\s*\([^)]*\))?(?:\s+[A-Za-z0-9_.]+(?:\s*\([^)]*\))?)*)\s*;", re.IGNORECASE | re.MULTILINE)
RE_OUT_OPT = re.compile(r"\bout\s*=\s*([A-Za-z0-9_.]+)", re.IGNORECASE)
RE_DATA_OPT = re.compile(r"\bdata\s*=\s*([A-Za-z0-9_.]+)", re.IGNORECASE)
RE_CREATE_TABLE = re.compile(r"\bcreate\s+table\s+([A-Za-z0-9_.]+)", re.IGNORECASE)
RE_FROM = re.compile(r"\bfrom\s+([A-Za-z0-9_.]+)", re.IGNORECASE)
RE_SQL_JOIN = re.compile(r"\bjoin\s+([A-Za-z0-9_.]+)", re.IGNORECASE)
# DATA step features
RE_FIRST_LAST = re.compile(r"\b(first|last)\.[A-Za-z_]\w*", re.IGNORECASE)
RE_RETAIN = re.compile(r"^\s*retain\b", re.IGNORECASE | re.MULTILINE)
RE_DO_LOOP = re.compile(r"^\s*do\b(?!\s+[a-z]+\s*=\s*\d)", re.IGNORECASE | re.MULTILINE)
RE_ARRAY = re.compile(r"^\s*array\b", re.IGNORECASE | re.MULTILINE)
RE_IF_THEN = re.compile(r"\bif\b.+\bthen\b", re.IGNORECASE)
RE_FORMAT = re.compile(r"^\s*format\b", re.IGNORECASE | re.MULTILINE)
RE_LABEL = re.compile(r"^\s*label\b", re.IGNORECASE | re.MULTILINE)
RE_KEEP_DROP = re.compile(r"^\s*(keep|drop)\b", re.IGNORECASE | re.MULTILINE)
RE_BY = re.compile(r"^\s*by\b", re.IGNORECASE | re.MULTILINE)


# ── Public API ─────────────────────────────────────────────────────────

def parse_program(filepath: str) -> dict:
    """Parse a single .sas file into a list of steps with dataflow.

    Returns:
      filepath, filename, num_lines
      steps: list of step dicts; each has:
          type: data | proc | macro_def | macro_call | libname | include | endsas
          line_start, line_end
          source: full source of the step
          name: dataset name (data) | proc name (proc) | macro name (macro_*)
              | libname | included file
          inputs: list of dataset references (set/merge/from/data=)
          outputs: list of dataset references (data <name>, out=, create table)
          features: dict of detected DATA-step features (merge, retain,
              first_last, do_loop, array, if_then, format, label, keep_drop)
              or PROC-level options
          recipe_hint: visual-recipe suggestion (sort/grouping/join/
              prepare/window/pivot/sync/sql/python/skip/template)
          macro_params: list (macro_def only)
          macro_args: dict or string (macro_call only)
      datasets_in, datasets_out: aggregated across all steps
      libnames: [{name, path}]
      includes: list of included file paths
      macros_defined: list of {name, params, line_start, line_end}
      macros_called: list of {name, args, line_start}
    """
    src = Path(filepath).read_text(errors="replace")
    lines = src.splitlines()
    cleaned = _strip_comments(src).splitlines()

    steps = []
    libnames = []
    includes = []
    macros_defined = []
    macros_called = []

    i = 0
    n = len(cleaned)
    while i < n:
        line = cleaned[i]
        raw = lines[i] if i < len(lines) else ""
        stripped = line.strip()
        if not stripped:
            i += 1
            continue

        # %include
        m = RE_INCLUDE.match(line)
        if m:
            inc_path = m.group(1)
            includes.append(inc_path)
            steps.append({
                "type": "include", "line_start": i + 1, "line_end": i + 1,
                "name": inc_path, "source": raw, "inputs": [], "outputs": [],
                "features": {}, "recipe_hint": "skip",
            })
            i += 1
            continue

        # libname
        m = RE_LIBNAME.match(line)
        if m:
            name = m.group(1)
            value = m.group(2).strip().strip('"').strip("'")
            libnames.append({"name": name, "path": value})
            steps.append({
                "type": "libname", "line_start": i + 1, "line_end": i + 1,
                "name": name, "source": raw, "inputs": [], "outputs": [],
                "features": {"path": value}, "recipe_hint": "skip",
            })
            i += 1
            continue

        # endsas
        if RE_ENDSAS.match(line):
            steps.append({
                "type": "endsas", "line_start": i + 1, "line_end": i + 1,
                "name": "endsas", "source": raw, "inputs": [], "outputs": [],
                "features": {}, "recipe_hint": "skip",
            })
            i += 1
            continue

        # %macro definition (multi-line, ends with %mend)
        m = RE_MACRO_DEF.match(line)
        if m:
            mac_name = m.group(1)
            mac_params = _parse_macro_params(m.group(2) or "")
            j = i + 1
            while j < n and not RE_MEND.match(cleaned[j]):
                j += 1
            j = min(j, n - 1)
            body = "\n".join(lines[i:j + 1])
            macros_defined.append({
                "name": mac_name, "params": mac_params,
                "line_start": i + 1, "line_end": j + 1,
            })
            steps.append({
                "type": "macro_def", "line_start": i + 1, "line_end": j + 1,
                "name": mac_name, "source": body,
                "inputs": [], "outputs": [], "features": {},
                "macro_params": mac_params, "recipe_hint": "template",
            })
            i = j + 1
            continue

        # %macro call (single-line; skip control words)
        m = RE_MACRO_CALL.match(line)
        if m and m.group(1).lower() not in MACRO_CONTROL_WORDS:
            call_name = m.group(1)
            call_args = _parse_macro_args(m.group(2) or "")
            macros_called.append({
                "name": call_name, "args": call_args, "line_start": i + 1,
            })
            steps.append({
                "type": "macro_call", "line_start": i + 1, "line_end": i + 1,
                "name": call_name, "source": raw,
                "inputs": [], "outputs": [], "features": {},
                "macro_args": call_args, "recipe_hint": "template",
            })
            i += 1
            continue

        # data step
        m = RE_DATA_START.match(line)
        if m:
            j = _find_step_end(cleaned, i)
            body = "\n".join(lines[i:j + 1])
            step = _analyze_data_step(body, i + 1, j + 1)
            steps.append(step)
            i = j + 1
            continue

        # proc step
        m = RE_PROC_START.match(line)
        if m:
            proc_name = m.group(1).lower()
            j = _find_step_end(cleaned, i, prefer_quit=(proc_name == "sql"))
            body = "\n".join(lines[i:j + 1])
            step = _analyze_proc_step(proc_name, body, i + 1, j + 1)
            steps.append(step)
            i = j + 1
            continue

        i += 1

    datasets_in = sorted({d for s in steps for d in s["inputs"]})
    datasets_out = sorted({d for s in steps for d in s["outputs"]})

    return {
        "filepath": filepath,
        "filename": Path(filepath).name,
        "num_lines": len(lines),
        "steps": steps,
        "datasets_in": datasets_in,
        "datasets_out": datasets_out,
        "libnames": libnames,
        "includes": includes,
        "macros_defined": macros_defined,
        "macros_called": macros_called,
    }


def parse_project(directory: str) -> dict:
    """Walk a SAS project directory; parse every .sas, locate data files.

    Returns:
      directory
      programs: [parse_program result, ...]
      data_files: [{path, name, format, size_bytes}] for .xpt/.sas7bdat/.sas7bcat
      metadata_files: [{path, format}] for .json/.xml/.html define files
      include_graph: {program_filename: [included_paths]}
      macros_registry: {macro_name: filename_where_defined}
      dataset_graph: {dataset_name: {producers: [filename:line_start],
                                     consumers: [filename:line_start]}}
    """
    root = Path(directory)
    programs = []
    for sas in sorted(root.rglob("*.sas")):
        try:
            programs.append(parse_program(str(sas)))
        except Exception as e:
            programs.append({
                "filepath": str(sas), "filename": sas.name,
                "parse_error": str(e), "steps": [],
                "datasets_in": [], "datasets_out": [],
                "libnames": [], "includes": [],
                "macros_defined": [], "macros_called": [],
            })

    data_files = []
    for ext in ("xpt", "sas7bdat", "sas7bcat"):
        for f in sorted(root.rglob(f"*.{ext}")):
            data_files.append({
                "path": str(f),
                "name": f.stem,
                "format": ext,
                "size_bytes": f.stat().st_size,
            })

    metadata_files = []
    for f in sorted(root.rglob("define.*")):
        if f.suffix.lower() in (".xml", ".html", ".pdf"):
            metadata_files.append({"path": str(f), "format": f.suffix.lstrip(".")})

    include_graph = {p["filename"]: p["includes"] for p in programs if p.get("includes")}

    macros_registry = {}
    for p in programs:
        for m in p.get("macros_defined", []):
            macros_registry[m["name"]] = p["filename"]

    dataset_graph = {}
    for p in programs:
        fn = p["filename"]
        for s in p["steps"]:
            for ds in s["outputs"]:
                key = _normalize_ds(ds)
                dataset_graph.setdefault(key, {"producers": [], "consumers": []})
                dataset_graph[key]["producers"].append(f"{fn}:{s['line_start']}")
            for ds in s["inputs"]:
                key = _normalize_ds(ds)
                dataset_graph.setdefault(key, {"producers": [], "consumers": []})
                dataset_graph[key]["consumers"].append(f"{fn}:{s['line_start']}")

    return {
        "directory": str(root),
        "programs": programs,
        "data_files": data_files,
        "metadata_files": metadata_files,
        "include_graph": include_graph,
        "macros_registry": macros_registry,
        "dataset_graph": dataset_graph,
    }


# ── Step analyzers ─────────────────────────────────────────────────────

def _analyze_data_step(body: str, ln_start: int, ln_end: int) -> dict:
    name_m = RE_DATA_OUT.search(body)
    output_clause = name_m.group(1) if name_m else ""
    outputs = _split_dataset_clause(output_clause)
    name = outputs[0] if outputs else "?"

    inputs = []
    for m in RE_SET.finditer(body):
        inputs.extend(_split_dataset_list(m.group(1)))
    for m in RE_MERGE.finditer(body):
        inputs.extend(_split_dataset_list(m.group(1)))
    inputs = sorted(set(inputs))

    features = {}
    if RE_MERGE.search(body):
        features["merge"] = True
    if RE_FIRST_LAST.search(body):
        features["by_first_last"] = True
    if RE_RETAIN.search(body):
        features["retain"] = True
    if RE_DO_LOOP.search(body):
        features["do_loop"] = True
    if RE_ARRAY.search(body):
        features["array"] = True
    if RE_IF_THEN.search(body):
        features["if_then"] = True
    if RE_FORMAT.search(body):
        features["format"] = True
    if RE_LABEL.search(body):
        features["label"] = True
    if RE_KEEP_DROP.search(body):
        features["keep_drop"] = True
    if RE_BY.search(body):
        features["by"] = True

    # Pure copy: no features beyond set/by
    body_no_data = re.sub(r"^\s*data\b.*?;\s*", "", body, count=1, flags=re.IGNORECASE | re.DOTALL)
    body_no_data = re.sub(r"\brun\s*;.*$", "", body_no_data, flags=re.IGNORECASE | re.DOTALL)
    non_io = re.sub(r"\bset\s+[^;]+;", "", body_no_data, flags=re.IGNORECASE)
    non_io = re.sub(r"^\s*by\s+[^;]+;", "", non_io, flags=re.IGNORECASE | re.MULTILINE).strip()
    if not non_io and "merge" not in features:
        features["set_only"] = True

    return {
        "type": "data",
        "line_start": ln_start, "line_end": ln_end,
        "name": name, "source": body,
        "inputs": inputs, "outputs": outputs,
        "features": features,
        "recipe_hint": _hint_for_data(features),
    }


def _analyze_proc_step(proc_name: str, body: str, ln_start: int, ln_end: int) -> dict:
    inputs = []
    outputs = []

    m = RE_DATA_OPT.search(body.split("\n", 1)[0] if "\n" in body else body)
    # data= can appear in many places; scan whole body
    for m in RE_DATA_OPT.finditer(body):
        inputs.append(m.group(1))
    for m in RE_OUT_OPT.finditer(body):
        outputs.append(m.group(1))

    features = {}
    sub_statements = []

    if proc_name == "sql":
        for m in RE_CREATE_TABLE.finditer(body):
            outputs.append(m.group(1))
        for m in RE_FROM.finditer(body):
            inputs.append(m.group(1))
        for m in RE_SQL_JOIN.finditer(body):
            inputs.append(m.group(1))
        # Count CREATE TABLE statements as a complexity signal
        n_creates = len(RE_CREATE_TABLE.findall(body))
        features["n_create_table"] = n_creates
        if "group by" in body.lower():
            features["group_by"] = True
        if re.search(r"\bjoin\b", body, re.IGNORECASE):
            features["sql_join"] = True
        if re.search(r"\bcase\b.*\bwhen\b", body, re.IGNORECASE | re.DOTALL):
            features["case_when"] = True

    if proc_name == "freq" and re.search(r"/\s*\bexact\b", body, re.IGNORECASE):
        features["statistical_test"] = True

    # PROC SORT without OUT= modifies the input in place. Surface the
    # input as the output too so Claude sees the dataset is reproduced.
    if proc_name == "sort" and inputs and not outputs:
        outputs = list(inputs)

    inputs = sorted(set(inputs))
    outputs = sorted(set(outputs))

    return {
        "type": "proc",
        "line_start": ln_start, "line_end": ln_end,
        "name": proc_name, "source": body,
        "inputs": inputs, "outputs": outputs,
        "features": features,
        "recipe_hint": _hint_for_proc(proc_name, features),
    }


def _hint_for_data(features: dict) -> str:
    if features.get("array") or features.get("do_loop"):
        return "python"
    if features.get("by_first_last") or features.get("retain"):
        return "window"
    if features.get("merge"):
        return "join"
    if features.get("set_only") and not features.get("if_then") and not features.get("format"):
        return "sync"
    if features.get("if_then") or features.get("format") or features.get("label") or features.get("keep_drop"):
        return "prepare"
    return "prepare"


def _hint_for_proc(proc_name: str, features: dict) -> str:
    if proc_name == "sql":
        # Multiple CREATE TABLE = multi-step; Claude must split. Hint sql.
        if features.get("n_create_table", 0) > 1:
            return "sql"
        if features.get("sql_join") and features.get("group_by"):
            return "sql"  # complex — Claude likely uses a SQL recipe
        if features.get("sql_join"):
            return "join"
        if features.get("group_by"):
            return "grouping"
        return "sql"
    if proc_name == "freq" and features.get("statistical_test"):
        return "python"
    return PROC_RECIPE_HINT.get(proc_name, "python")


# ── Helpers ────────────────────────────────────────────────────────────

def _strip_comments(src: str) -> str:
    """Remove /* ... */ block comments and `* ...;` and `** ...;` line comments.

    SAS is forgiving; we only need this clean enough that step regexes
    don't false-match comment text.
    """
    # Block comments — preserve newlines so line numbers stay aligned
    src = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), src, flags=re.DOTALL)
    # Star-prefixed comment statements; can span multiple lines when only
    # the final line carries `;`. Preserve newlines as above.
    src = re.sub(r"^\s*\*+[^;]*;", lambda m: "\n" * m.group(0).count("\n"), src, flags=re.MULTILINE)
    return src


def _find_step_end(lines: list, start: int, prefer_quit: bool = False) -> int:
    """Walk forward until `run;` (or `quit;` for proc sql) terminates the step."""
    target = re.compile(r"\bquit\s*;", re.IGNORECASE) if prefer_quit else RE_RUN_QUIT
    for j in range(start, len(lines)):
        if target.search(lines[j]):
            return j
    return len(lines) - 1


def _split_dataset_list(text: str) -> list:
    """Split a SAS dataset list ('AE TEMP B(in=inB)') into clean names."""
    out = []
    for tok in re.split(r"\s+", text.strip()):
        if not tok:
            continue
        # Strip data set options: NAME(in=foo keep=...)
        tok = re.sub(r"\(.*$", "", tok).strip(",")
        if tok and not tok.startswith("(") and tok.lower() not in ("by", "where", "keep", "drop", "rename"):
            out.append(tok)
    return out


def _split_dataset_clause(clause: str) -> list:
    """Split 'X Y(label='Adverse Events') Z' → ['X', 'Y', 'Z'].

    Strips parenthesized dataset options first so embedded whitespace
    inside string literals doesn't fragment the names.
    """
    stripped = re.sub(r"\([^)]*\)", "", clause)
    out = []
    for piece in re.split(r"\s+", stripped.strip()):
        piece = piece.strip(",")
        if piece:
            out.append(piece)
    return out


def _normalize_ds(name: str) -> str:
    """Strip libref prefix for graph keys (WORK.AE → AE), uppercase."""
    return name.split(".")[-1].upper()


def _parse_macro_params(params_str: str) -> list:
    if not params_str.strip():
        return []
    out = []
    for p in params_str.split(","):
        p = p.strip()
        if "=" in p:
            name, default = p.split("=", 1)
            out.append({"name": name.strip(), "default": default.strip()})
        elif p:
            out.append({"name": p, "default": None})
    return out


def _parse_macro_args(args_str: str) -> dict:
    if not args_str.strip():
        return {}
    out = {}
    pos = 0
    for a in args_str.split(","):
        a = a.strip()
        if "=" in a:
            k, v = a.split("=", 1)
            out[k.strip()] = v.strip()
        elif a:
            out[f"_pos{pos}"] = a
            pos += 1
    return out
