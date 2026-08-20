#!/usr/bin/env python3
"""Check that every distribution manifest agrees with the skill it ships.

The repository publishes one skill through four manifests: the portable Agent
Plugins manifest, the Claude Code plugin and marketplace manifests, and the
OpenAI Codex plugin manifest. This script keeps their identity and version in
sync and validates SKILL.md against the Agent Skills specification limits.

Usage: python3 tools/check_manifests.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"

AGENT_PLUGINS_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
AGENT_PLUGINS_FIELDS = {
    "$schema",
    "name",
    "version",
    "description",
    "author",
    "homepage",
    "repository",
    "license",
    "keywords",
    "extensions",
}
SKILL_NAME_PATTERN = re.compile(r"^(?!.*--)[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")

errors: list[str] = []
warnings: list[str] = []


def fail(message: str) -> None:
    errors.append(message)


def warn(message: str) -> None:
    warnings.append(message)


def load_json(relative: str) -> dict:
    path = ROOT / relative
    if not path.is_file():
        fail(f"{relative}: missing")
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        fail(f"{relative}: invalid JSON ({error})")
        return {}


def parse_frontmatter(path: Path) -> dict[str, object]:
    """Parse the flat `key: value` frontmatter used by SKILL.md."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        fail(f"{path.relative_to(ROOT)}: missing YAML frontmatter")
        return {}
    end = text.find("\n---\n", 3)
    if end == -1:
        fail(f"{path.relative_to(ROOT)}: unterminated YAML frontmatter")
        return {}

    fields: dict[str, object] = {}
    nested: dict[str, str] | None = None
    for line in text[4:end].splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith((" ", "\t")):
            if nested is None:
                fail(f"{path.relative_to(ROOT)}: unexpected indented frontmatter line {line!r}")
                continue
            key, _, value = line.strip().partition(":")
            nested[key.strip()] = value.strip().strip('"')
            continue
        key, _, value = line.partition(":")
        value = value.strip()
        if value:
            fields[key.strip()] = value.strip('"')
            nested = None
        else:
            nested = {}
            fields[key.strip()] = nested
    return fields


def check_skill(skill_dir: Path) -> tuple[str, str]:
    rel = skill_dir.relative_to(ROOT)
    fields = parse_frontmatter(skill_dir / "SKILL.md")

    name = str(fields.get("name", ""))
    if not name:
        fail(f"{rel}/SKILL.md: `name` is required")
    else:
        if name != skill_dir.name:
            fail(f"{rel}/SKILL.md: `name` ({name}) must match the directory name ({skill_dir.name})")
        if len(name) > 64 or not SKILL_NAME_PATTERN.match(name):
            fail(f"{rel}/SKILL.md: `name` ({name}) violates the Agent Skills naming rules")

    description = str(fields.get("description", ""))
    if not description:
        fail(f"{rel}/SKILL.md: `description` is required")
    elif len(description) > 1024:
        fail(f"{rel}/SKILL.md: `description` is {len(description)} characters (max 1024)")

    compatibility = str(fields.get("compatibility", ""))
    if compatibility and len(compatibility) > 500:
        fail(f"{rel}/SKILL.md: `compatibility` is {len(compatibility)} characters (max 500)")

    metadata = fields.get("metadata")
    version = ""
    if isinstance(metadata, dict):
        version = metadata.get("version", "")
    if not version:
        fail(f"{rel}/SKILL.md: `metadata.version` is required so manifests can be kept in sync")

    body_lines = (skill_dir / "SKILL.md").read_text(encoding="utf-8").splitlines()
    if len(body_lines) > 500:
        warn(f"{rel}/SKILL.md: {len(body_lines)} lines; the specification recommends staying under 500")

    tracked = subprocess.run(
        ["git", "ls-files", "--", str(skill_dir)],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    for line in tracked.stdout.splitlines():
        if "__pycache__" in line or line.endswith((".pyc", ".pyo")):
            fail(f"{line}: build artifact committed inside the shipped skill")

    return name, str(version)


def main() -> int:
    skill_dirs = sorted(p.parent for p in SKILLS_DIR.glob("*/SKILL.md"))
    if len(skill_dirs) != 1:
        fail(f"skills/: expected exactly one skill directory, found {len(skill_dirs)}")
        return report()

    skill_name, skill_version = check_skill(skill_dirs[0])

    portable = load_json("plugin.json")
    claude = load_json(".claude-plugin/plugin.json")
    marketplace = load_json(".claude-plugin/marketplace.json")
    codex = load_json(".codex-plugin/plugin.json")

    if portable:
        if portable.get("$schema") != AGENT_PLUGINS_SCHEMA:
            fail(f"plugin.json: `$schema` must be {AGENT_PLUGINS_SCHEMA}")
        unknown = sorted(set(portable) - AGENT_PLUGINS_FIELDS)
        if unknown:
            fail(f"plugin.json: fields outside the closed Agent Plugins schema: {', '.join(unknown)}")

    entries = marketplace.get("plugins") or []
    entry = entries[0] if entries else {}
    if len(entries) != 1:
        fail(".claude-plugin/marketplace.json: expected exactly one plugin entry")
    source = entry.get("source")
    if isinstance(source, str) and not (ROOT / source).exists():
        fail(f".claude-plugin/marketplace.json: source {source!r} does not exist")

    named = {
        "plugin.json": portable.get("name"),
        ".claude-plugin/plugin.json": claude.get("name"),
        ".claude-plugin/marketplace.json (plugin entry)": entry.get("name"),
        ".codex-plugin/plugin.json": codex.get("name"),
    }
    for label, value in named.items():
        if value and value != skill_name:
            fail(f"{label}: name {value!r} does not match the skill name {skill_name!r}")

    versioned = {
        "plugin.json": portable.get("version"),
        ".claude-plugin/plugin.json": claude.get("version"),
        ".claude-plugin/marketplace.json (plugin entry)": entry.get("version"),
        ".codex-plugin/plugin.json": codex.get("version"),
    }
    for label, value in versioned.items():
        if value and value != skill_version:
            fail(f"{label}: version {value!r} does not match SKILL.md metadata.version {skill_version!r}")

    if codex.get("skills") != "./skills/":
        fail(".codex-plugin/plugin.json: `skills` must be \"./skills/\"")

    return report()


def report() -> int:
    for message in warnings:
        print(f"warning: {message}")
    for message in errors:
        print(f"error: {message}")
    if errors:
        print(f"\n{len(errors)} problem(s) found.")
        return 1
    print("manifests consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
