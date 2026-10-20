#!/usr/bin/env python3
"""Keep values.schema.json and the README values tables in sync.

values.schema.json is the source of descriptions and validation, values.yaml
the source of defaults. This script copies each default into the schema and
regenerates the README tables between the values markers.

    scripts/gen-docs.py           update both files
    scripts/gen-docs.py --check   fail if either is out of date (CI)

It also fails when a value in values.yaml has no described schema property.
Needs python3 and yq (mikefarah, v4).
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHART = ROOT / "charts" / "workload"
SCHEMA = CHART / "values.schema.json"
README = ROOT / "README.md"
START, END = "<!-- values:start -->", "<!-- values:end -->"

# README sections, by top-level key. Every top-level key must be listed.
GROUPS = [
    ("Image and replicas", ["image", "global", "imagePullSecrets", "replicaCount",
                            "revisionHistoryLimit", "strategy", "nameOverride", "fullnameOverride"]),
    ("Container", ["command", "args", "env", "configMapRefs", "secretRefs", "containerPort",
                   "resources", "securityContext", "probes", "startupProbe", "livenessProbe",
                   "readinessProbe", "lifecycle", "volumeMounts", "initContainers", "extraContainers"]),
    ("Pod", ["podAnnotations", "podLabels", "commonAnnotations", "podSecurityContext",
             "priorityClassName", "terminationGracePeriodSeconds", "volumes", "nodeSelector",
             "tolerations", "affinity", "topologySpreadConstraints"]),
    ("Service account", ["serviceAccount"]),
    ("Networking", ["service", "ingress", "httpRoute"]),
    ("Scaling and availability", ["autoscaling", "pdb"]),
    ("Metrics", ["metrics"]),
    ("Extra manifests", ["extraObjects"]),
]

MISSING = object()


def load_values():
    out = subprocess.run(["yq", "-o=json", ".", str(CHART / "values.yaml")],
                         check=True, capture_output=True, text=True).stdout
    return json.loads(out)


def described_children(node):
    props = node.get("properties", {})
    return {k: v for k, v in props.items() if "description" in v}


def rows(node, values, path):
    """Yield (path, schema node, default) for each documented value."""
    children = described_children(node)
    if path and not children:
        yield path, node, values
        return
    for key, child in children.items():
        sub = values.get(key, MISSING) if isinstance(values, dict) else MISSING
        yield from rows(child, sub, f"{path}.{key}" if path else key)


def set_defaults(node, values):
    for key, child in node.get("properties", {}).items():
        if not isinstance(values, dict) or key not in values:
            child.pop("default", None)
            continue
        if described_children(child):
            child.pop("default", None)
            set_defaults(child, values[key])
        else:
            child["default"] = values[key]


def leaf_paths(values, path=""):
    if isinstance(values, dict) and values:
        for k, v in values.items():
            yield from leaf_paths(v, f"{path}.{k}" if path else k)
    else:
        yield path


def fmt_default(value):
    if value is MISSING:
        return "unset"
    return "`" + json.dumps(value, separators=(", ", ": "), ensure_ascii=False) + "`"


def cell(text):
    return text.replace("|", "\\|").replace("\n", " ")


def main():
    check = "--check" in sys.argv[1:]
    values = load_values()
    schema = json.loads(SCHEMA.read_text())
    errors = []

    top = set(schema["properties"])
    grouped = [k for _, keys in GROUPS for k in keys]
    for k in sorted(top - set(grouped)):
        errors.append(f"top-level key {k!r} is not in a README group (scripts/gen-docs.py GROUPS)")
    for k in sorted(set(grouped) - top):
        errors.append(f"README group lists {k!r}, which is not in the schema")

    documented = []
    tables = []
    for title, keys in GROUPS:
        lines = [f"### {title}", "", "| Key | Default | Description |", "|---|---|---|"]
        for key in keys:
            if key not in schema["properties"]:
                continue
            for path, node, default in rows(schema["properties"][key], values.get(key, MISSING), key):
                documented.append(path)
                lines.append(f"| `{path}` | {cell(fmt_default(default))} | {cell(node['description'])} |")
        tables.append("\n".join(lines))

    for leaf in leaf_paths(values):
        if not any(leaf == d or leaf.startswith(d + ".") for d in documented):
            errors.append(f"values.yaml key {leaf!r} has no described property in values.schema.json")

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1

    set_defaults(schema, values)
    new_schema = json.dumps(schema, indent=2, ensure_ascii=False) + "\n"

    readme = README.read_text()
    head, rest = readme.split(START, 1)
    _, tail = rest.split(END, 1)
    new_readme = f"{head}{START}\n\n" + "\n\n".join(tables) + f"\n\n{END}{tail}"

    stale = [p.name for p, new in ((SCHEMA, new_schema), (README, new_readme)) if p.read_text() != new]
    if check:
        if stale:
            print(f"out of date: {', '.join(stale)}. Run scripts/gen-docs.py", file=sys.stderr)
            return 1
        print("schema and README values tables are up to date")
        return 0
    SCHEMA.write_text(new_schema)
    README.write_text(new_readme)
    print(f"updated: {', '.join(stale) or 'nothing'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
