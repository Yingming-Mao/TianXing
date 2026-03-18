"""Experiment map: auto-discover and maintain bidirectional mappings between paper, code, tests, and results."""

import argparse
import json
import re
from pathlib import Path
from typing import Optional

from .utils import get_project_root, iso_now, json_result, load_config


# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------

def _empty_map() -> dict:
    return {
        "version": "1",
        "generated_at": iso_now(),
        "paper_sections": [],
        "code_entries": [],
        "test_entries": [],
        "result_entries": [],
        "links": [],
    }


def _make_id(prefix: str, name: str) -> str:
    """Create a namespaced ID like 'code:train' from a file stem or label."""
    clean = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
    return f"{prefix}:{clean}"


# ---------------------------------------------------------------------------
# LaTeX scanning
# ---------------------------------------------------------------------------

_LABEL_RE = re.compile(r"\\label\{([^}]+)\}")
_SECTION_RE = re.compile(r"\\(section|subsection|subsubsection)\*?\{([^}]+)\}")
_TABLE_BEGIN = re.compile(r"\\begin\{table\}")
_TABLE_END = re.compile(r"\\end\{table\}")
_FIGURE_BEGIN = re.compile(r"\\begin\{figure\}")
_FIGURE_END = re.compile(r"\\end\{figure\}")
_CAPTION_RE = re.compile(r"\\caption\{([^}]+)\}")
_INCLUDEGRAPHICS_RE = re.compile(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}")
_INPUT_RE = re.compile(r"\\(?:input|include)\{([^}]+)\}")
_REF_RE = re.compile(r"\\(?:ref|cref|autoref|eqref)\{([^}]+)\}")


def _scan_tex_file(tex_path: Path, rel_base: Path) -> tuple[list[dict], list[tuple[str, str]]]:
    """Parse a single .tex file, return (entities, raw_links)."""
    entities: list[dict] = []
    raw_links: list[tuple[str, str]] = []  # (from_id, to_label)
    rel = str(tex_path.relative_to(rel_base))

    try:
        lines = tex_path.read_text(errors="replace").splitlines()
    except Exception:
        return entities, raw_links

    # Track current environment for table/figure detection
    in_env: Optional[str] = None  # "table" or "figure"
    env_start = 0
    env_labels: list[str] = []
    env_caption = ""
    env_graphics: list[str] = []

    for i, line in enumerate(lines, 1):
        # Sections
        m = _SECTION_RE.search(line)
        if m:
            sec_type, title = m.group(1), m.group(2)
            # Look for \label on same or next few lines
            label = None
            for j in range(max(0, i - 1), min(len(lines), i + 3)):
                lm = _LABEL_RE.search(lines[j])
                if lm:
                    label = lm.group(1)
                    break
            eid = label if label else _make_id("sec", title)
            entities.append({
                "id": eid,
                "file": rel,
                "title": title,
                "type": "section",
                "line_range": [i, i],
            })

        # \ref links from this file
        for rm in _REF_RE.finditer(line):
            # We'll resolve these after collecting all entities
            raw_links.append((rel, rm.group(1)))

        # Table/figure environments
        if _TABLE_BEGIN.search(line):
            in_env, env_start = "table", i
            env_labels, env_caption, env_graphics = [], "", []
        elif _FIGURE_BEGIN.search(line):
            in_env, env_start = "figure", i
            env_labels, env_caption, env_graphics = [], "", []

        if in_env:
            for lm in _LABEL_RE.finditer(line):
                env_labels.append(lm.group(1))
            cm = _CAPTION_RE.search(line)
            if cm:
                env_caption = cm.group(1)
            for gm in _INCLUDEGRAPHICS_RE.finditer(line):
                env_graphics.append(gm.group(1))

        if in_env == "table" and _TABLE_END.search(line):
            label = env_labels[0] if env_labels else _make_id("tab", env_caption or f"table_L{env_start}")
            entities.append({
                "id": label,
                "file": rel,
                "title": env_caption or f"Table at line {env_start}",
                "type": "table",
                "line_range": [env_start, i],
            })
            in_env = None
        elif in_env == "figure" and _FIGURE_END.search(line):
            label = env_labels[0] if env_labels else _make_id("fig", env_caption or f"figure_L{env_start}")
            entities.append({
                "id": label,
                "file": rel,
                "title": env_caption or f"Figure at line {env_start}",
                "type": "figure",
                "line_range": [env_start, i],
                "graphics": env_graphics,
            })
            in_env = None

    return entities, raw_links


def _scan_paper(paper_dir: Path, project_root: Path) -> tuple[list[dict], list[tuple[str, str]]]:
    """Scan all .tex files under paper_dir."""
    all_entities: list[dict] = []
    all_links: list[tuple[str, str]] = []
    if not paper_dir.exists():
        return all_entities, all_links
    for tex in sorted(paper_dir.rglob("*.tex")):
        ents, links = _scan_tex_file(tex, project_root)
        all_entities.extend(ents)
        all_links.extend(links)
    return all_entities, all_links


# ---------------------------------------------------------------------------
# Code / test / result scanning
# ---------------------------------------------------------------------------

_CODE_EXTS = {".py", ".r", ".R", ".sh", ".jl", ".m", ".ipynb"}
_TEST_PATTERNS = [re.compile(r"^test_"), re.compile(r"_test\.")]
_RESULT_EXTS = {".json", ".csv", ".tsv", ".pkl", ".npy", ".npz", ".h5", ".hdf5",
                ".png", ".pdf", ".svg", ".eps", ".jpg", ".jpeg", ".gif"}


def _scan_code(code_dir: Path, project_root: Path) -> tuple[list[dict], list[dict]]:
    """Return (code_entries, test_entries)."""
    code_entries: list[dict] = []
    test_entries: list[dict] = []
    if not code_dir.exists():
        return code_entries, test_entries

    for f in sorted(code_dir.rglob("*")):
        if not f.is_file() or f.suffix not in _CODE_EXTS:
            continue
        rel = str(f.relative_to(project_root))
        is_test = any(p.search(f.stem) for p in _TEST_PATTERNS)
        if is_test:
            test_entries.append({
                "id": _make_id("test", f.stem),
                "path": rel,
                "command": f"pytest {rel} -x" if f.suffix == ".py" else f"python {rel}",
                "description": f"Tests in {rel}",
            })
        else:
            code_entries.append({
                "id": _make_id("code", f.stem),
                "path": rel,
                "description": f"Code file {rel}",
            })
    return code_entries, test_entries


def _scan_results(results_dir: Path, project_root: Path) -> list[dict]:
    """Return result_entries."""
    entries: list[dict] = []
    if not results_dir.exists():
        return entries
    for f in sorted(results_dir.rglob("*")):
        if not f.is_file() or f.suffix not in _RESULT_EXTS:
            continue
        rel = str(f.relative_to(project_root))
        rtype = "figure" if f.suffix in {".png", ".pdf", ".svg", ".eps", ".jpg", ".jpeg", ".gif"} else "data"
        entries.append({
            "id": _make_id("result", f.stem),
            "path": rel,
            "type": rtype,
            "description": f"{'Figure' if rtype == 'figure' else 'Data'} file {rel}",
        })
    return entries


# ---------------------------------------------------------------------------
# Link inference
# ---------------------------------------------------------------------------

def _infer_links(paper_sections: list, code_entries: list, test_entries: list,
                 result_entries: list, raw_ref_links: list) -> list[dict]:
    """Heuristically infer relationships between entities."""
    links: list[dict] = []
    seen = set()

    def _add(frm: str, to: str, rel: str):
        key = (frm, to, rel)
        if key not in seen:
            seen.add(key)
            links.append({"from": frm, "to": to, "relation": rel})

    # Build lookup indices
    all_ids = set()
    for e in paper_sections + code_entries + test_entries + result_entries:
        all_ids.add(e["id"])

    code_by_stem = {}
    for c in code_entries:
        stem = Path(c["path"]).stem
        code_by_stem[stem] = c["id"]
        # Also index by parent directory name for experiment-level matching
        parent = Path(c["path"]).parent.name
        if parent:
            code_by_stem.setdefault(f"_dir_{parent}", [])
            if isinstance(code_by_stem[f"_dir_{parent}"], list):
                code_by_stem[f"_dir_{parent}"].append(c["id"])

    result_by_stem = {}
    for r in result_entries:
        result_by_stem[Path(r["path"]).stem] = r["id"]

    # 1. \ref links: paper section → table/figure
    label_set = {e["id"] for e in paper_sections}
    for (src_file, ref_label) in raw_ref_links:
        if ref_label in label_set:
            # Find which section this file belongs to
            for sec in paper_sections:
                if sec["file"] == src_file and sec["type"] == "section":
                    _add(sec["id"], ref_label, "references")

    # 2. test → code: match test_foo → foo
    for t in test_entries:
        test_stem = Path(t["path"]).stem
        # test_foo → foo
        for prefix in ("test_", ""):
            target_stem = test_stem
            if target_stem.startswith("test_"):
                target_stem = target_stem[len("test_"):]
            if target_stem.endswith("_test"):
                target_stem = target_stem[:-len("_test")]
            if target_stem in code_by_stem:
                _add(code_by_stem[target_stem], t["id"], "tested_by")
                break
        # Same directory matching
        test_parent = Path(t["path"]).parent.name
        dir_key = f"_dir_{test_parent}"
        if dir_key in code_by_stem and isinstance(code_by_stem[dir_key], list):
            for cid in code_by_stem[dir_key]:
                _add(cid, t["id"], "tested_by")

    # 3. code → result: same directory name or stem overlap
    for c in code_entries:
        code_parent = Path(c["path"]).parent.name
        for r in result_entries:
            result_parent = Path(r["path"]).parent.name
            if code_parent and code_parent == result_parent:
                _add(c["id"], r["id"], "produces")

    # 4. figure entity → result file: match \includegraphics path
    for sec in paper_sections:
        if sec["type"] == "figure":
            for gpath in sec.get("graphics", []):
                gstem = Path(gpath).stem
                if gstem in result_by_stem:
                    _add(sec["id"], result_by_stem[gstem], "displays")
                else:
                    # Try partial match
                    for rstem, rid in result_by_stem.items():
                        if gstem in rstem or rstem in gstem:
                            _add(sec["id"], rid, "displays")

    return links


# ---------------------------------------------------------------------------
# Core API
# ---------------------------------------------------------------------------

def discover_map(project_root: Optional[Path] = None, config: Optional[dict] = None) -> dict:
    """Scan project and generate an experiment map."""
    root = project_root or get_project_root()
    cfg = config or load_config()
    proj = cfg.get("project", {})

    paper_dir = root / proj.get("paper_dir", "paper")
    code_dir = root / proj.get("code_dir", "code")
    results_dir = root / proj.get("results_dir", "results")

    paper_sections, raw_refs = _scan_paper(paper_dir, root)
    code_entries, test_entries = _scan_code(code_dir, root)
    result_entries = _scan_results(results_dir, root)
    links = _infer_links(paper_sections, code_entries, test_entries, result_entries, raw_refs)

    emap = _empty_map()
    emap["paper_sections"] = paper_sections
    emap["code_entries"] = code_entries
    emap["test_entries"] = test_entries
    emap["result_entries"] = result_entries
    emap["links"] = links
    return emap


def load_map(project_root: Optional[Path] = None) -> Optional[dict]:
    """Load experiment_map.json from project root."""
    root = project_root or get_project_root()
    cfg = load_config()
    map_file = root / cfg.get("experiment_map", {}).get("file", "experiment_map.json")
    if map_file.exists():
        try:
            return json.loads(map_file.read_text())
        except (json.JSONDecodeError, OSError):
            return None
    return None


def save_map(emap: dict, project_root: Optional[Path] = None) -> Path:
    """Write experiment_map.json to project root."""
    root = project_root or get_project_root()
    cfg = load_config()
    map_file = root / cfg.get("experiment_map", {}).get("file", "experiment_map.json")
    emap["generated_at"] = iso_now()
    map_file.write_text(json.dumps(emap, ensure_ascii=False, indent=2) + "\n")
    return map_file


def merge_maps(existing: dict, discovered: dict) -> dict:
    """Merge discovered entries into existing map without removing user-added entries."""
    merged = json.loads(json.dumps(existing))  # deep copy

    for key in ("paper_sections", "code_entries", "test_entries", "result_entries"):
        existing_ids = {e["id"] for e in merged.get(key, [])}
        for entry in discovered.get(key, []):
            if entry["id"] not in existing_ids:
                merged.setdefault(key, []).append(entry)
            else:
                # Update existing entry (preserve user modifications by only updating auto fields)
                for i, e in enumerate(merged[key]):
                    if e["id"] == entry["id"]:
                        # Update line_range and graphics (auto-discovered fields)
                        if "line_range" in entry:
                            merged[key][i]["line_range"] = entry["line_range"]
                        if "graphics" in entry:
                            merged[key][i]["graphics"] = entry["graphics"]
                        break

    # Add new links that don't exist yet
    existing_links = {(l["from"], l["to"], l["relation"]) for l in merged.get("links", [])}
    for link in discovered.get("links", []):
        key = (link["from"], link["to"], link["relation"])
        if key not in existing_links:
            merged.setdefault("links", []).append(link)

    return merged


# ---------------------------------------------------------------------------
# Query API
# ---------------------------------------------------------------------------

def _all_entities(emap: dict) -> dict[str, dict]:
    """Build id → entity lookup."""
    idx = {}
    for key in ("paper_sections", "code_entries", "test_entries", "result_entries"):
        for e in emap.get(key, []):
            idx[e["id"]] = e
    return idx


def query_related(emap: dict, entity_id: str) -> dict:
    """Find all entities related to the given ID, in both directions."""
    idx = _all_entities(emap)
    outgoing = []  # links where entity_id is the 'from'
    incoming = []  # links where entity_id is the 'to'

    for link in emap.get("links", []):
        if link["from"] == entity_id and link["to"] in idx:
            outgoing.append({**idx[link["to"]], "relation": link["relation"]})
        if link["to"] == entity_id and link["from"] in idx:
            incoming.append({**idx[link["from"]], "relation": link["relation"]})

    return {"entity": idx.get(entity_id), "outgoing": outgoing, "incoming": incoming}


def find_by_path(emap: dict, file_path: str) -> list[dict]:
    """Find all entities that reference a given file path."""
    results = []
    for key in ("paper_sections", "code_entries", "test_entries", "result_entries"):
        for e in emap.get(key, []):
            path_field = e.get("path") or e.get("file")
            if path_field and (path_field == file_path or file_path.endswith(path_field) or path_field.endswith(file_path)):
                results.append(e)
    return results


def find_tests_for_code(emap: dict, code_path: str) -> list[dict]:
    """Given a code file path, find all test commands that should be run."""
    code_entities = find_by_path(emap, code_path)
    tests = []
    seen = set()
    for ce in code_entities:
        related = query_related(emap, ce["id"])
        for r in related["outgoing"]:
            if r["relation"] == "tested_by" and r["id"] not in seen:
                seen.add(r["id"])
                tests.append(r)
    return tests


def find_paper_sections_for_code(emap: dict, code_path: str) -> list[dict]:
    """Given a code file, find paper sections that display its results."""
    code_entities = find_by_path(emap, code_path)
    sections = []
    seen = set()

    for ce in code_entities:
        # code → produces → result
        related = query_related(emap, ce["id"])
        for r in related["outgoing"]:
            if r["relation"] == "produces":
                # result → displayed_by → paper section
                result_related = query_related(emap, r["id"])
                for s in result_related["incoming"]:
                    if s["relation"] == "displays" and s["id"] not in seen:
                        seen.add(s["id"])
                        sections.append(s)
    return sections


def find_code_for_section(emap: dict, section_id: str) -> list[dict]:
    """Given a paper section/table/figure, find the code that produces it."""
    related = query_related(emap, section_id)
    code = []
    seen = set()

    # Direct: section displays result, result produced_by code
    for r in related["outgoing"]:
        if r["relation"] == "displays":
            result_related = query_related(emap, r["id"])
            for c in result_related["incoming"]:
                if c["relation"] == "produces" and c["id"] not in seen:
                    seen.add(c["id"])
                    code.append(c)

    # Also check references (section references table/figure)
    for r in related["outgoing"]:
        if r["relation"] == "references":
            sub_code = find_code_for_section(emap, r["id"])
            for c in sub_code:
                if c["id"] not in seen:
                    seen.add(c["id"])
                    code.append(c)

    return code


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Experiment map: discover, query, and manage")
    parser.add_argument("--action", required=True, choices=["discover", "query", "validate"],
                        help="Action to perform")
    parser.add_argument("--id", type=str, default=None, help="Entity ID to query")
    parser.add_argument("--path", type=str, default=None, help="File path to query")
    parser.add_argument("--config", type=str, default=None)
    args = parser.parse_args()

    cfg = load_config(args.config)
    root = get_project_root()

    if args.action == "discover":
        discovered = discover_map(root, cfg)
        existing = load_map(root)
        if existing:
            emap = merge_maps(existing, discovered)
        else:
            emap = discovered
        out_path = save_map(emap, root)
        json_result(True,
                    map_file=str(out_path),
                    paper_sections=len(emap["paper_sections"]),
                    code_entries=len(emap["code_entries"]),
                    test_entries=len(emap["test_entries"]),
                    result_entries=len(emap["result_entries"]),
                    links=len(emap["links"]))

    elif args.action == "query":
        emap = load_map(root)
        if not emap:
            json_result(False, error="No experiment_map.json found. Run --action discover first.")
            return
        if args.id:
            result = query_related(emap, args.id)
            json_result(True, **result)
        elif args.path:
            entities = find_by_path(emap, args.path)
            tests = []
            paper_sections = []
            for e in entities:
                tests.extend(find_tests_for_code(emap, args.path))
                paper_sections.extend(find_paper_sections_for_code(emap, args.path))
            json_result(True, entities=entities, related_tests=tests, related_sections=paper_sections)
        else:
            json_result(False, error="Provide --id or --path for query")

    elif args.action == "validate":
        emap = load_map(root)
        if not emap:
            json_result(False, error="No experiment_map.json found.")
            return
        missing = []
        for key in ("code_entries", "test_entries", "result_entries"):
            for e in emap.get(key, []):
                p = e.get("path")
                if p and not (root / p).exists():
                    missing.append({"id": e["id"], "path": p})
        for e in emap.get("paper_sections", []):
            p = e.get("file")
            if p and not (root / p).exists():
                missing.append({"id": e["id"], "path": p})
        json_result(len(missing) == 0, missing_files=missing, total_checked=sum(
            len(emap.get(k, [])) for k in ("paper_sections", "code_entries", "test_entries", "result_entries")
        ))


if __name__ == "__main__":
    main()
