"""Validated per-project agent model configuration."""
from pathlib import Path

import yaml


def load_agent_config(path: Path) -> dict:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or not isinstance(document.get("agents"), dict):
        raise ValueError("Agent config must contain an agents mapping.")
    agents = document["agents"]
    for name in ("manager", "architect", "senior_developer"):
        entry = agents.get(name)
        if not isinstance(entry, dict):
            raise ValueError(f"Missing agent configuration: {name}")
        for key in ("role", "model_tier", "model"):
            if not isinstance(entry.get(key), str) or not entry[key].strip():
                raise ValueError(f"Missing {name}.{key} in agent config.")
        if "<" in entry["model"] or ">" in entry["model"]:
            raise ValueError(f"Replace the placeholder model for {name}.")
    return agents