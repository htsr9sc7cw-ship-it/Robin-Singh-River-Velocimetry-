"""make_code_guide.py

Thesis section: Appendix A.2
Inputs: the headers of all scripts of this package, REPRODUCE.md, ../environment/*, run.py
Outputs: CODE_GUIDE.md (one entry per script: purpose, thesis section, inputs, outputs, command, environment)
         and a check that every file named in REPRODUCE.md and in the guide exists

Builds the guide directly from the script headers, so that the documentation cannot drift from the code.

    python make_code_guide.py            # writes CODE_GUIDE.md next to this file
    python make_code_guide.py --check    # only reports names in REPRODUCE.md that do not exist

Requires: Python 3.9 or later, standard library only.
"""

import ast
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
THIRD_PARTY = ("nets", "utils", "datasets", "flowvelo_src", "tapvid_davis", "__pycache__")
SKIP_PARTS = ("ckpt", "/out", "frames_pngonly", "Vectors_and_Images")

GROUPS = [
    ("rerender", "Data: fluid simulation, rendering, ground truth, tracers"),
    ("ptv", "PTV: parameters, driver, filter cascade, Lucas-Kanade sweep"),
    ("v2_project", "Evaluation: PIPs++ drivers, scoring, statistics, tables"),
    ("finetune", "Retraining: strategies, TAP-Vid-DAVIS test"),
    ("v2_project/figure_scripts", "Diagrams: one script per picture"),
    ("thesis", "Thesis build and checks"),
    (".", "Entry points and helpers"),
]


def is_third_party(rel):
    parts = rel.split(os.sep)
    return any(p in THIRD_PARTY for p in parts) or any(s in rel for s in SKIP_PARTS)


def header_of(path):
    """Docstring (py) or leading comment block (sh) as text."""
    try:
        src = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return ""
    if path.endswith(".py"):
        try:
            return ast.get_docstring(ast.parse(src)) or ""
        except SyntaxError:
            return ""
    lines = []
    for ln in src.splitlines()[:12]:
        if ln.startswith("#!"):
            continue
        if ln.startswith("#"):
            lines.append(ln.lstrip("# ").rstrip())
        elif ln.strip():
            break
    return "\n".join(lines)


def field(text, name):
    m = re.search(r"^%s:\s*(.+)$" % name, text, re.M)
    return m.group(1).strip() if m else ""


def commands_of(text):
    cmds = []
    for ln in text.splitlines():
        s = ln.strip()
        if re.match(r"^(/opt/anaconda3[\w/.-]*/python3?|python3?|bash|sh|\./)\s", s):
            cmds.append(s)
    return cmds


def purpose_of(text, rel):
    first = text.strip().splitlines()[0].strip() if text.strip() else ""
    if first.endswith(".py") or first.endswith(".sh") or not first:
        body = [ln.strip() for ln in text.splitlines()[1:] if ln.strip()]
        body = [b for b in body if not re.match(r"^(Thesis section|Inputs|Outputs|Requires)\b", b)]
        first = body[0] if body else "(see header of the script)"
    return first


def interpreter(text, rel):
    t = text + open(os.path.join(HERE, rel), encoding="utf-8", errors="replace").read()[:3000]
    if "pips2" in t:
        return "pips2 environment (PyTorch, OpenEXR)"
    if "flowvelo" in t.lower() and "python" in t.lower():
        return "flowvelo environment"
    if rel.startswith("rerender") and (".sh" not in rel):
        return "Blender 5.2 (bpy), or base Python for the helpers"
    return "base Python (numpy, pandas, matplotlib)"


def collect():
    items = []
    for root, dirs, files in os.walk(HERE):
        rel_root = os.path.relpath(root, HERE)
        if is_third_party(rel_root + os.sep):
            dirs[:] = []
            continue
        for f in sorted(files):
            if f.endswith((".py", ".sh")):
                rel = os.path.normpath(os.path.join(rel_root, f))
                if not is_third_party(rel):
                    items.append(rel)
    return items


def group_of(rel):
    best = None
    for g, title in GROUPS:
        gp = g.replace("/", os.sep)
        if gp == ".":
            continue
        if rel == gp or rel.startswith(gp + os.sep):
            if best is None or len(gp) > len(best[0]):
                best = (gp, title)
    return best[1] if best else dict(GROUPS)["."]


def figure_info(rel):
    src = open(os.path.join(HERE, rel), encoding="utf-8", errors="replace").read()
    outs = re.findall(r"save\(\s*\w+\s*,\s*['\"]([^'\"]+\.png)", src)
    reads = bool(re.search(r"read_csv|results\(\)|\.csv|json\.load|np\.load|imread|\.exr|\.npz", src))
    return (outs[0] if outs else ""), ("computes from result files" if reads else "schematic")


def check_names():
    """Every script/file name mentioned in REPRODUCE.md that does not exist."""
    text = open(os.path.join(HERE, "REPRODUCE.md"), encoding="utf-8").read()
    names = set(re.findall(r"[\w./-]+\.(?:py|sh|csv|md|txt|json)", text))
    missing = []
    for n in sorted(names):
        base = os.path.basename(n)
        found = any(base in files for _, _, files in os.walk(HERE)) or any(
            base in files for _, _, files in os.walk(KIT)
        )
        if not found and "<" not in n and "*" not in n:
            missing.append(n)
    return missing


def main():
    if "--check" in sys.argv:
        miss = check_names()
        print("names in REPRODUCE.md that are not in the package (they are outputs or on the project drive):")
        print("\n".join("  " + m for m in miss) or "  none")
        return
    items = collect()
    out = ["# Code guide\n"]
    out.append(
        "One entry per script: what it does, which thesis section, table or figure it belongs to, its inputs and outputs, "
        "the command that runs it and the environment it needs. The entries are generated from the script headers by "
        "`make_code_guide.py`, so they equal the code. The commands behind every table are in `REPRODUCE.md`.\n"
    )
    out.append("## Quick start\n")
    out.append("```bash\ncd thesis_kit\npython run.py setup      # once per computer\npython run.py list       # names of all runnable scripts\npython run.py demo       # one scene, numbers compared with the thesis (6 to 8 minutes)\npython run.py <name>     # any single script\n```\n")
    out.append("## Requirements\n")
    env = os.path.join(KIT, "environment")
    out.append("- **Operating system and hardware:** developed and tested on macOS with an Apple M-series GPU (8 GB unified memory); without a GPU the scripts run on the CPU, more slowly.\n")
    out.append("- **Python environments** (files in `environment/`): `pips2.yml` for PIPs++ and the evaluation (PyTorch, OpenEXR), `flowvelo.yml` for FlowVeloTool, `base.txt` for tables, statistics and figures (numpy, pandas, matplotlib).\n")
    for name in ("base.txt", "pips2.yml", "flowvelo.yml"):
        p = os.path.join(env, name)
        if os.path.exists(p):
            lines = [ln.rstrip() for ln in open(p, encoding="utf-8").read().splitlines() if ln.strip()]
            keep = [ln for ln in lines if re.search(r"python|torch|numpy|pandas|matplotlib|opencv|openexr|scipy|pillow|imageio|tensorboard", ln, re.I)]
            out.append("\n`%s` (key packages, full list in the file):\n```\n%s\n```\n" % (name, "\n".join(keep[:14])))
    out.append("- **Blender 5.2** (`bpy`, `mathutils`): only for the scripts in `rerender/` (re-rendering). Not needed to reproduce the tables and figures from the stored results.\n")
    out.append("- **Third-party code** (not modified except for the changes listed in Appendix A.3): PIPs++ (`nets`, `utils`, `datasets`, `saverloader.py`), FlowVeloTool, DeepMind `tapvid_metrics.py` and `tapnet_viz.py`.\n")
    out.append("- **Paths in shell scripts:** 3 of the shell scripts (the long run_*.sh drivers of the study) contain the absolute path of the project drive in their first line (cd \"/Volumes/...\"). They document exactly how the study was run; to run them elsewhere, change that first line to the folder of this package (the Python scripts and run.py find each other relative to their own location and need no change).\n")
    out.append("- **Data not in the package** (too large): the other scenes of the final dataset, the Blender fluid caches (about 40 GB) and the TAP-Vid-DAVIS benchmark (2.5 GB, DeepMind). Scripts that need them say so when started.\n")
    out.append("\n## Scripts by group\n")
    by = {}
    for rel in items:
        by.setdefault(group_of(rel), []).append(rel)
    order = [t for _, t in GROUPS]
    for title in order:
        if title not in by:
            continue
        out.append("\n### %s\n" % title)
        for rel in by[title]:
            h = header_of(os.path.join(HERE, rel))
            out.append("**`%s`**  " % rel.replace(os.sep, "/"))
            out.append("- *Purpose:* %s" % purpose_of(h, rel))
            sec = field(h, "Thesis section")
            if sec:
                out.append("- *Thesis section:* %s" % sec)
            if field(h, "Inputs"):
                out.append("- *Inputs:* %s" % field(h, "Inputs"))
            if field(h, "Outputs"):
                out.append("- *Outputs:* %s" % field(h, "Outputs"))
            if rel.startswith("v2_project" + os.sep + "figure_scripts") and os.path.basename(rel).startswith("fig_"):
                png, kind = figure_info(rel)
                out.append("- *Picture:* %s (%s)" % (png or "see script", kind))
            cmds = commands_of(h)
            if cmds:
                out.append("- *Command:* `%s`" % cmds[0])
            else:
                py = "python" if rel.endswith(".py") else "bash"
                out.append("- *Command:* `cd %s && %s %s`" % (os.path.dirname(rel).replace(os.sep, "/") or ".", py, os.path.basename(rel)))
            out.append("- *Environment:* %s" % interpreter(h, rel))
            req = re.search(r"^Requires:\s*(.+)$", h, re.M)
            if req:
                out.append("- *Requires:* %s" % req.group(1).strip())
            out.append("")
    out.append("\n## Commands behind every table and figure of the thesis\n")
    out.append(open(os.path.join(HERE, "REPRODUCE.md"), encoding="utf-8").read())
    open(os.path.join(HERE, "CODE_GUIDE.md"), "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("CODE_GUIDE.md written:", len(items), "scripts")


if __name__ == "__main__":
    main()
