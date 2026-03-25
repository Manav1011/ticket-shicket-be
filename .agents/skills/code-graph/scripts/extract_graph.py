#!/usr/bin/env python3
"""
extract_graph.py — Static analysis script for code-graph skill.
Walks a directory, extracts functions/classes/imports and cross-file calls,
and outputs a node/edge JSON suitable for Mermaid rendering.

Usage:
    python extract_graph.py <directory> [--entry <file>] [--depth <n>] [--feature <name>]

Output (stdout): JSON with keys: nodes, edges, entry_points, warnings
"""

import ast
import os
import re
import sys
import json
import argparse
from pathlib import Path
from collections import defaultdict

# ─── Language Detection ────────────────────────────────────────────────────────

LANG_MAP = {
    ".py":   "python",
    ".js":   "javascript",
    ".ts":   "typescript",
    ".jsx":  "javascript",
    ".tsx":  "typescript",
    ".java": "java",
    ".go":   "go",
    ".rb":   "ruby",
    ".php":  "php",
    ".c":    "c",
    ".cpp":  "cpp",
    ".h":    "c",
    ".hpp":  "cpp",
    ".rs":   "rust",
}

IGNORE_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".next", "target"}

# ─── Python Parser ─────────────────────────────────────────────────────────────

def parse_python(filepath, rel_path):
    nodes, edges = [], []
    try:
        src = Path(filepath).read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(src)
    except SyntaxError:
        return nodes, edges, []

    file_id = rel_path.replace("/", ".").replace(".py", "")
    imports = []

    # Collect top-level definitions
    func_names = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fid = f"{file_id}.{node.name}"
            is_async = isinstance(node, ast.AsyncFunctionDef)
            nodes.append({"id": fid, "label": f"{'async ' if is_async else ''}{node.name}()", "type": "func", "file": rel_path})
            func_names.add(node.name)
        elif isinstance(node, ast.ClassDef):
            cid = f"{file_id}.{node.name}"
            nodes.append({"id": cid, "label": node.name, "type": "class", "file": rel_path})

    # Imports → edges to other modules
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)

    # Cross-file call detection: match call names to known functions in other files
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = None
            if isinstance(node.func, ast.Name):
                name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                name = node.func.attr
            if name:
                edges.append({"_unresolved_call": name, "_from_file": file_id})

    return nodes, edges, imports


# ─── Generic Regex Parser (JS/TS/Java/Go/Ruby/PHP/C/Rust) ─────────────────────

PATTERNS = {
    "javascript": {
        "func":    [r"(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s*)?\(|(\w+)\s*:\s*(?:async\s*)?\()"],
        "import":  [r"(?:import .+ from ['\"](.+?)['\"]|require\(['\"](.+?)['\"]\))"],
        "entry":   ["index.js", "main.js", "app.js", "server.js"],
    },
    "typescript": {
        "func":    [r"(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s*)?\(|(\w+)\s*:\s*(?:async\s*)?\()"],
        "import":  [r"import .+ from ['\"](.+?)['\"]"],
        "entry":   ["index.ts", "main.ts", "app.ts", "server.ts"],
    },
    "java": {
        "func":    [r"(?:public|private|protected|static)\s+\S+\s+(\w+)\s*\("],
        "import":  [r"import\s+([\w.]+);"],
        "entry":   [],  # detected by main() presence
    },
    "go": {
        "func":    [r"^func\s+(\w+)\s*\("],
        "import":  [r'"([\w./]+)"'],
        "entry":   ["main.go"],
    },
    "ruby": {
        "func":    [r"def\s+(\w+)"],
        "import":  [r"require(?:_relative)?\s+['\"](.+?)['\"]"],
        "entry":   ["app.rb", "main.rb", "config.ru"],
    },
    "php": {
        "func":    [r"function\s+(\w+)\s*\("],
        "import":  [r"(?:require|include)(?:_once)?\s+['\"](.+?)['\"]"],
        "entry":   ["index.php"],
    },
    "c": {
        "func":    [r"^[\w\s\*]+\s+(\w+)\s*\([^)]*\)\s*\{"],
        "import":  [r'#include\s+[<"](.+?)[>"]'],
        "entry":   [],
    },
    "cpp": {
        "func":    [r"^[\w\s\*:~]+\s+(\w+)\s*\([^)]*\)\s*(?:const\s*)?\{"],
        "import":  [r'#include\s+[<"](.+?)[>"]'],
        "entry":   [],
    },
    "rust": {
        "func":    [r"(?:pub\s+)?fn\s+(\w+)\s*\("],
        "import":  [r"use\s+([\w:]+)"],
        "entry":   ["main.rs"],
    },
}

def parse_generic(filepath, rel_path, lang):
    nodes, edges, imports = [], [], []
    pat = PATTERNS.get(lang, {})
    src = Path(filepath).read_text(encoding="utf-8", errors="ignore")
    file_id = re.sub(r"[/\\.]", "_", rel_path)

    for pattern in pat.get("func", []):
        for m in re.finditer(pattern, src, re.MULTILINE):
            name = next((g for g in m.groups() if g), None)
            if name and len(name) > 1:
                fid = f"{file_id}.{name}"
                nodes.append({"id": fid, "label": f"{name}()", "type": "func", "file": rel_path})

    for pattern in pat.get("import", []):
        for m in re.finditer(pattern, src, re.MULTILINE):
            mod = next((g for g in m.groups() if g), None)
            if mod:
                imports.append(mod)

    return nodes, edges, imports


# ─── Entry Point Detection ─────────────────────────────────────────────────────

ENTRY_SIGNALS = {
    "python":     [r'if __name__\s*==\s*["\']__main__["\']', r"def main\(", r"@app\.route", r"@router\.", r"app = FastAPI", r"app = Flask"],
    "javascript": [r"ReactDOM\.render\(", r"createRoot\(", r"app\.listen\(", r"\.get\(['\"/]", r"\.post\(['\"/]"],
    "typescript": [r"ReactDOM\.render\(", r"createRoot\(", r"app\.listen\("],
    "java":       [r"public static void main\(String"],
    "go":         [r"func main\(\)"],
    "ruby":       [r"Sinatra|Rails\.application", r"run Rack"],
    "rust":       [r"fn main\(\)"],
}

def is_entry_point(filepath, lang):
    src = Path(filepath).read_text(encoding="utf-8", errors="ignore")
    for pattern in ENTRY_SIGNALS.get(lang, []):
        if re.search(pattern, src):
            return True
    filename = Path(filepath).name
    for ep in PATTERNS.get(lang, {}).get("entry", []):
        if filename == ep:
            return True
    return False


# ─── Cross-file Call Resolution ────────────────────────────────────────────────

def resolve_cross_file_calls(all_nodes, raw_edges):
    """Match unresolved call names to actual function nodes in other files."""
    func_index = defaultdict(list)  # name → [node_id, ...]
    for n in all_nodes:
        if n["type"] in ("func", "class"):
            short = n["label"].replace("()", "").replace("async ", "").strip()
            func_index[short].append(n["id"])

    resolved = []
    for e in raw_edges:
        if "_unresolved_call" in e:
            name = e["_unresolved_call"]
            from_file = e["_from_file"]
            candidates = [nid for nid in func_index.get(name, []) if not nid.startswith(from_file)]
            for target in candidates[:1]:  # take first match
                resolved.append({"from": from_file, "to": target, "label": "calls", "cross_file": True})
        else:
            resolved.append(e)
    return resolved


# ─── Depth Limiting ────────────────────────────────────────────────────────────

def limit_depth(nodes, edges, entry_ids, max_depth):
    """BFS from entry points, keep only nodes within max_depth hops."""
    if not entry_ids or max_depth <= 0:
        return nodes, edges

    edge_map = defaultdict(list)
    for e in edges:
        edge_map[e["from"]].append(e["to"])

    visited = set()
    frontier = set(entry_ids)
    depth = 0
    while frontier and depth <= max_depth:
        visited |= frontier
        next_frontier = set()
        for nid in frontier:
            for target in edge_map.get(nid, []):
                if target not in visited:
                    next_frontier.add(target)
        frontier = next_frontier
        depth += 1

    kept_ids = visited
    nodes = [n for n in nodes if n["id"] in kept_ids]
    edges = [e for e in edges if e["from"] in kept_ids and e["to"] in kept_ids]
    return nodes, edges


# ─── Feature Scoping ───────────────────────────────────────────────────────────

def scope_to_feature(nodes, edges, feature_name):
    """Keep only nodes whose id or label contains the feature name (case-insensitive)."""
    pattern = feature_name.lower()
    seed_ids = {n["id"] for n in nodes if pattern in n["id"].lower() or pattern in n["label"].lower()}

    if not seed_ids:
        return nodes, edges, []  # no match, return all

    # Expand: include callers and callees 1 level out
    edge_map_fwd = defaultdict(set)
    edge_map_bwd = defaultdict(set)
    for e in edges:
        edge_map_fwd[e["from"]].add(e["to"])
        edge_map_bwd[e["to"]].add(e["from"])

    expanded = set(seed_ids)
    for sid in seed_ids:
        expanded |= edge_map_fwd.get(sid, set())
        expanded |= edge_map_bwd.get(sid, set())

    nodes = [n for n in nodes if n["id"] in expanded]
    edges = [e for e in edges if e["from"] in expanded and e["to"] in expanded]
    return nodes, edges, list(seed_ids)


# ─── Import Edges ──────────────────────────────────────────────────────────────

def build_import_edges(file_nodes, all_imports_by_file, all_file_ids):
    """Turn import strings into edges between file-level nodes."""
    edges = []
    for file_id, imports in all_imports_by_file.items():
        for imp in imports:
            # Try to match import to a known file
            imp_clean = imp.replace(".", "/").replace("-", "_")
            for target_fid in all_file_ids:
                if imp_clean in target_fid or target_fid.endswith(imp_clean):
                    if file_id != target_fid:
                        edges.append({"from": file_id, "to": target_fid, "label": "imports"})
                        break
    return edges


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Extract code graph from a directory.")
    parser.add_argument("directory", help="Root directory of the codebase")
    parser.add_argument("--entry", help="Explicit entry point file (relative path)", default=None)
    parser.add_argument("--depth", type=int, default=5, help="Max call depth from entry (default: 5)")
    parser.add_argument("--feature", help="Scope graph to a specific feature/function name", default=None)
    args = parser.parse_args()

    root = Path(args.directory).resolve()
    if not root.exists():
        print(json.dumps({"error": f"Directory not found: {root}"}))
        sys.exit(1)

    all_nodes = []
    all_edges = []
    all_imports_by_file = {}
    file_nodes = []  # module-level nodes
    entry_point_ids = []
    warnings = []

    # ── Walk files ──
    for filepath in sorted(root.rglob("*")):
        if not filepath.is_file():
            continue
        # Skip ignored dirs
        if any(p in IGNORE_DIRS for p in filepath.parts):
            continue
        ext = filepath.suffix.lower()
        lang = LANG_MAP.get(ext)
        if not lang:
            continue

        rel_path = str(filepath.relative_to(root))
        file_id = re.sub(r"[/\\]", ".", rel_path).rstrip(".")

        # Add file-level node
        file_node = {"id": file_id, "label": rel_path, "type": "module", "file": rel_path}
        file_nodes.append(file_node)
        all_nodes.append(file_node)

        # Detect entry point
        entry_match = (args.entry and rel_path == args.entry) or (not args.entry and is_entry_point(str(filepath), lang))
        if entry_match:
            file_node["type"] = "entrypoint"
            entry_point_ids.append(file_id)

        # Parse
        if lang == "python":
            nodes, edges, imports = parse_python(str(filepath), rel_path)
        else:
            nodes, edges, imports = parse_generic(str(filepath), rel_path, lang)

        all_nodes.extend(nodes)
        all_edges.extend(edges)
        all_imports_by_file[file_id] = imports

    # ── Build import edges ──
    all_file_ids = [n["id"] for n in file_nodes]
    import_edges = build_import_edges(file_nodes, all_imports_by_file, all_file_ids)
    all_edges.extend(import_edges)

    # ── Resolve cross-file calls ──
    all_edges = resolve_cross_file_calls(all_nodes, all_edges)

    # ── Feature scoping ──
    if args.feature:
        all_nodes, all_edges, seed_ids = scope_to_feature(all_nodes, all_edges, args.feature)
        if not seed_ids:
            warnings.append(f"Feature '{args.feature}' not found. Showing full graph.")

    # ── Depth limiting ──
    if entry_point_ids:
        all_nodes, all_edges = limit_depth(all_nodes, all_edges, entry_point_ids, args.depth)
    else:
        warnings.append("No entry point detected. Set --entry <file> for depth-limiting.")

    # ── Dedup edges ──
    seen = set()
    deduped_edges = []
    for e in all_edges:
        key = (e.get("from"), e.get("to"), e.get("label", ""))
        if key not in seen:
            seen.add(key)
            deduped_edges.append(e)

    output = {
        "nodes": all_nodes,
        "edges": deduped_edges,
        "entry_points": entry_point_ids,
        "warnings": warnings,
        "stats": {
            "total_files": len(file_nodes),
            "total_nodes": len(all_nodes),
            "total_edges": len(deduped_edges),
        }
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
