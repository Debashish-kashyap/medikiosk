"""Loads and indexes the clinical ontology (the deterministic dialogue graph).

The ontology is data, not code — add complaints by editing clinical_ontology.json,
not this file. Owned by the Backend Lead + AI-NLU lane.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

ONTOLOGY_PATH = Path(__file__).resolve().parent.parent / "data" / "clinical_ontology.json"


class Ontology:
    def __init__(self, raw: dict[str, Any]):
        self.raw = raw
        self.version: str = raw.get("version", "0")
        self.languages: list[str] = raw.get("meta", {}).get("languages", ["en"])
        self.entry: str = raw["entry"]
        self.nodes: dict[str, dict] = raw["nodes"]
        self.red_flags: list[dict] = raw.get("red_flags", [])

    def get_node(self, node_id: str) -> dict | None:
        return self.nodes.get(node_id)

    def entry_node(self) -> dict:
        return self.nodes[self.entry]

    def option(self, node_id: str, value: str) -> dict | None:
        node = self.get_node(node_id)
        if not node:
            return None
        for opt in node.get("options", []):
            if opt["value"] == value:
                return opt
        return None

    def localize(self, obj: Any, lang: str) -> Any:
        """Return the localized string from a {'en':..,'hi':..} dict, falling back to en."""
        if isinstance(obj, dict):
            return obj.get(lang) or obj.get("en") or next(iter(obj.values()), "")
        return obj


@lru_cache(maxsize=1)
def load_ontology() -> Ontology:
    with open(ONTOLOGY_PATH, encoding="utf-8") as fh:
        return Ontology(json.load(fh))
