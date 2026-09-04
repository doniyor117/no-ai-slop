#!/usr/bin/env python3
"""Check the no-ai-slop package files. Standard library only."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL_PATH = ROOT / "SKILL.md"

# The only frontmatter fields the Agent Skills spec allows. Anything else is a
# hard error on claude.ai upload and through the Skills API, not a warning.
SPEC_FIELDS = {
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
}

NAME_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
DASHES = re.compile(r"[—–]")
# A line may carry a dash only where it demonstrates the dash pattern. Word
# boundaries keep "dashboard" from exempting a line by accident.
DASH_TOPIC = re.compile(r"\bdash(es)?\b", re.IGNORECASE)

errors: list[str] = []


def fail(message: str) -> None:
    errors.append(message)


skill = SKILL_PATH.read_text(encoding="utf-8")
readme = (ROOT / "README.md").read_text(encoding="utf-8")
plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
marketplace = json.loads(
    (ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
)

# --- frontmatter ------------------------------------------------------------

match = re.match(r"\A---\n(.*?)\n---\n", skill, re.DOTALL)
if match is None:
    print("SKILL.md must open with YAML frontmatter on line 1")
    raise SystemExit(1)
frontmatter = match.group(1)

fields = set(re.findall(r"(?m)^([A-Za-z][A-Za-z0-9_-]*):", frontmatter))
for unexpected in sorted(fields - SPEC_FIELDS):
    fail(f"frontmatter field not in the Agent Skills spec: {unexpected}")

name_match = re.search(r"(?m)^name:\s*(\S+)\s*$", frontmatter)
if name_match is None:
    fail("frontmatter needs a name")
else:
    name = name_match.group(1)
    if not NAME_PATTERN.match(name) or len(name) > 64:
        fail(f"name must be lowercase alphanumeric with single hyphens, max 64: {name}")
    if name != ROOT.name:
        fail(f"name '{name}' must match the directory name '{ROOT.name}'")

description_match = re.search(r'(?m)^description:\s*"(.*)"\s*$', frontmatter, re.DOTALL)
if description_match is None:
    fail("frontmatter needs a quoted description")
elif not 1 <= len(description_match.group(1)) <= 1024:
    fail(f"description must be 1 to 1024 characters, found {len(description_match.group(1))}")

# --- one version everywhere -------------------------------------------------

skill_version = re.search(r'(?m)^\s+version:\s*"([^"]+)"\s*$', frontmatter)
readme_version = re.search(r"(?m)^- \*\*([0-9]+\.[0-9]+\.[0-9]+)\*\*", readme)
if skill_version is None:
    fail("add metadata.version to SKILL.md")
if readme_version is None:
    fail("add a version entry to README.md")
if skill_version and readme_version:
    versions = {skill_version.group(1), readme_version.group(1), str(plugin.get("version"))}
    if len(versions) != 1:
        fail(f"use one version in every file, found {sorted(versions)}")

# --- packaging --------------------------------------------------------------

found = {path.relative_to(ROOT) for path in ROOT.rglob("SKILL.md")}
if SKILL_PATH.is_symlink() or found != {Path("SKILL.md")}:
    fail(f"keep exactly one regular SKILL.md at the repo root, found {sorted(map(str, found))}")
if plugin.get("skills") != ["./"]:
    fail('plugin.json must set "skills": ["./"] so the loader finds the root skill')
if [p.get("source") for p in marketplace.get("plugins", [])] != ["./"]:
    fail('marketplace.json must list one plugin with "source": "./"')

# --- the skill's own rules --------------------------------------------------

for path in (SKILL_PATH, ROOT / "README.md", ROOT / "AGENTS.md"):
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not DASHES.search(line):
            continue
        demonstrating = line.lstrip().startswith("- Slop:") or DASH_TOPIC.search(line)
        if not demonstrating:
            fail(f"{path.name}:{number} uses an em or en dash outside a dash example")

previous = ""
for number, line in enumerate(skill.splitlines(), 1):
    stripped = line.strip()
    if stripped.startswith("- Real:") and not previous.startswith("- Slop:"):
        fail(f"SKILL.md:{number} has a Real half with no Slop half above it")
    previous = stripped

# ----------------------------------------------------------------------------

if errors:
    for error in errors:
        print(f"error: {error}", file=sys.stderr)
    raise SystemExit(1)
print(f"{ROOT.name} package OK")
