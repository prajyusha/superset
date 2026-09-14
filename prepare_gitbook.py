#!/usr/bin/env python3
import json
import re
import shutil
from pathlib import Path

REPO = Path(".")
OUT = Path("gitbook")

INCLUDE_ROOT_FILES = [
    "README.md",
    "CONTRIBUTING.md",
    "INSTALL.md",
    "UPDATING.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
    "AGENTS.md",
]

INCLUDE_DIRS = [
    "docs/docs",
    "docs/admin_docs",
    "docs/developer_docs",
    "docs/sip",
    "RELEASING",
    "helm",
    "superset-websocket",
    "superset-embedded-sdk",
    "superset-extensions-cli",
    "superset-core",
]

EXCLUDE_PATTERNS = [
    "versioned_docs",
    "node_modules",
    "/components/",
    "/.claude/",
    "CHANGELOG/",
    "/tests/",
]

SECTION_TITLES = {
    "docs/docs": "User Documentation",
    "docs/admin_docs": "Administration",
    "docs/developer_docs": "Developer Documentation",
    "docs/sip": "Improvement Proposals",
    "RELEASING": "Release Process",
    "helm": "Helm Chart",
    "superset-websocket": "Websocket Service",
    "superset-embedded-sdk": "Embedded SDK",
    "superset-extensions-cli": "Extensions CLI",
    "superset-core": "Superset Core",
}

DROP_FRONTMATTER_KEYS = {"hide_title", "sidebar_position", "sidebar_label", "version", "slug", "id"}


def excluded(path):
    s = str(path)
    return any(p in s for p in EXCLUDE_PATTERNS)


def split_frontmatter(text):
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return {}, text
    body = text[match.end():]
    meta = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip().strip("'\"")
    return meta, body


def derive_title(meta, body, path):
    if meta.get("title"):
        return meta["title"]
    heading = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    if heading:
        return heading.group(1).strip()
    stem = path.stem
    if stem.lower() in ("index", "readme"):
        stem = path.parent.name
    return stem.replace("-", " ").replace("_", " ").title()


def convert(src, dest):
    text = src.read_text(encoding="utf-8", errors="replace")
    meta, body = split_frontmatter(text)
    title = derive_title(meta, body, src)
    kept = {k: v for k, v in meta.items() if k not in DROP_FRONTMATTER_KEYS and k != "title"}
    header = ["---", f"title: {json.dumps(title, ensure_ascii=False)}"]
    for key, value in kept.items():
        header.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
    header.append("---")
    header.append("")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(header) + "\n" + body.lstrip("\n"), encoding="utf-8")
    return title


def collect():
    entries = []
    for name in INCLUDE_ROOT_FILES:
        src = REPO / name
        if src.exists():
            entries.append(("", src, Path(name)))
    for directory in INCLUDE_DIRS:
        base = REPO / directory
        if not base.exists():
            continue
        for src in sorted(base.rglob("*")):
            if src.suffix not in (".md", ".mdx") or excluded(src):
                continue
            rel = src.relative_to(REPO).with_suffix(".md")
            entries.append((directory, src, rel))
    return entries


def summary_sort_key(rel):
    parts = rel.parts
    leading = 0 if rel.stem.lower() in ("index", "readme") else 1
    return (len(parts), tuple(parts[:-1]), leading, rel.stem.lower())


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    entries = collect()
    grouped = {}
    for section, src, rel in entries:
        title = convert(src, OUT / rel)
        grouped.setdefault(section, []).append((rel, title))

    lines = ["# Table of contents", ""]
    root_pages = grouped.pop("", [])
    for rel, title in root_pages:
        label = "Overview" if rel.name == "README.md" else title
        lines.append(f"* [{label}]({rel.as_posix()})")
    for section in INCLUDE_DIRS:
        pages = grouped.get(section)
        if not pages:
            continue
        lines.append("")
        lines.append(f"## {SECTION_TITLES.get(section, section)}")
        lines.append("")
        for rel, title in sorted(pages, key=lambda item: summary_sort_key(item[0])):
            lines.append(f"* [{title}]({rel.as_posix()})")
    (OUT / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"pages: {len(entries)}")


if __name__ == "__main__":
    main()
