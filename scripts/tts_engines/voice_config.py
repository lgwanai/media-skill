"""Voice configuration file loader utility.

Loads voice configuration from markdown files with YAML frontmatter.
"""

import os
import re

import yaml


def load_voice_config(voice_name: str) -> dict | None:
    """Load voice configuration from markdown file.

    Looks for config file at data/voices/{voice_name}/config.md

    Args:
        voice_name: Name of the voice to load configuration for.

    Returns:
        Dictionary with keys: name, engine, instruct, created, notes
        Returns None if config file doesn't exist.
    """
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "data", "voices", voice_name, "config.md",
    )

    if not os.path.exists(config_path):
        return None

    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Parse YAML frontmatter
    frontmatter: dict = {}
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                frontmatter = yaml.safe_load(parts[1]) or {}
            except Exception:
                pass

    # Extract instruct section
    instruct: str | None = None
    instruct_match = re.search(
        r"^## Instruct\s*\n(.+?)(?=^##|\Z)", content, re.MULTILINE | re.DOTALL,
    )
    if instruct_match:
        instruct = instruct_match.group(1).strip()

    # Extract notes section
    notes: str | None = None
    notes_match = re.search(
        r"^## Notes\s*\n(.+?)(?=^##|\Z)", content, re.MULTILINE | re.DOTALL,
    )
    if notes_match:
        notes = notes_match.group(1).strip()

    return {
        "name": frontmatter.get("name", voice_name),
        "engine": frontmatter.get("engine"),
        "created": frontmatter.get("created"),
        "instruct": instruct,
        "notes": notes,
    }
