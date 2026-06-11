"""Resolve flat Omeka tag names to the structured recommender taxonomy.

Westerbork stores the expert taxonomy as plain Omeka tags (e.g. "Forced Labor",
"age 35-44", "deported to: Auschwitz-Birkenau", "somber (tone)"), mixed with app/AR
navigation markers and free Dutch folksonomy. This module maps each tag name to a
canonical ``facet:label`` using the taxonomy in ``data/tags.json``.

The canonical ``facet:label`` string is the shared key between content ingestion
(Qdrant ``tag_labels``) and the recommender's ``tag_affinity`` matching.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

_TAGS_JSON = Path(__file__).parent / "taxonomy.json"


@dataclass(frozen=True)
class ResolvedTag:
    facet: str
    label: str
    weight: float = 1.0

    @property
    def key(self) -> str:
        return f"{self.facet}:{self.label}"

    def to_payload(self) -> dict:
        return {"facet": self.facet, "label": self.label, "weight": self.weight}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def _build_index(doc: dict) -> dict[str, tuple[str, str]]:
    """normalized tag name -> (facet, canonical label)."""
    index: dict[str, tuple[str, str]] = {}

    def add(facet: str, label: str) -> None:
        index.setdefault(_norm(label), (facet, label))

    for dim_key, dim in doc.get("dimensions", {}).items():
        # flat tags directly on the dimension
        for label in dim.get("tags", []):
            add(dim_key, label)
        # theme_what: main categories + their sub-tags
        for cat, subs in dim.get("categories", {}).items():
            add(dim_key, cat)
            for sub in subs:
                add(dim_key, sub)
        # subdimensions
        for sub_key, sub in dim.get("subdimensions", {}).items():
            facet = f"{dim_key}.{sub_key}"
            for label in sub.get("tags", []):
                add(facet, label)
            for label in sub.get("example_tags", []):
                add(facet, label)
            for cat in sub.get("categories", {}):
                add(facet, cat)
    return index


with _TAGS_JSON.open(encoding="utf-8") as _f:
    _INDEX = _build_index(json.load(_f))

# --- pre-rules applied before exact lookup ----------------------------------

_TONE_SUFFIX = re.compile(r"\s*\((?:visual\s+)?tone\)\s*$", re.IGNORECASE)
_DROP_PREFIXES = ("arlocation",)          # legacy app-location tags (being replaced by AiARLocation)
_LOCATION_PREFIX = "aiarlocation"          # new app-location grouping -> kept as facet 'location'
_DROP_EXACT = {"start", "start page", "kwbvr"}

# transit / origin prefixes -> (facet, canonical prefix)
_PREFIX_RULES = [
    ("deported to:", "place_where.transit_destinations", "Deported to:"),
    ("arrived from:", "place_where.transit_destinations", "Arrived from:"),
    ("born in:", "person_who.city_village_country", "Born in:"),
    ("lived in:", "person_who.city_village_country", "Lived in:"),
    ("from:", "person_who.city_village_country", "From:"),
]

_BARRACK = re.compile(r"^bar\w*\s+\d+(?:-\d+)?$", re.IGNORECASE)  # barrack 75, barracks 65-67, barak 3


def resolve_tag(name: str, *, keep_freeform: bool = True) -> Optional[ResolvedTag]:
    """Map one Omeka tag name to a ResolvedTag, or None if it should be dropped.

    keep_freeform=True returns facet='freeform' for non-taxonomy tags; False drops them.
    """
    if not name or not name.strip():
        return None
    raw = name.strip()
    low = _norm(raw)

    # new app-location grouping (AiARLocation*) -> keep as a 'location' facet (filterable)
    if low.startswith(_LOCATION_PREFIX):
        return ResolvedTag("location", raw)

    # legacy AR markers / nav -> drop
    if low in _DROP_EXACT or any(low.startswith(p) for p in _DROP_PREFIXES):
        return None

    # tone tags: "somber (tone)" / "dark (visual tone)"
    if _TONE_SUFFIX.search(raw):
        base = _TONE_SUFFIX.sub("", raw).strip()
        hit = _INDEX.get(_norm(base))
        if hit:
            return ResolvedTag(hit[0], hit[1])
        return ResolvedTag("language_how.tone_of_text", base.capitalize())

    # transit / origin prefixes
    for prefix, facet, canon in _PREFIX_RULES:
        if low.startswith(prefix):
            value = raw[len(prefix):].strip()
            return ResolvedTag(facet, f"{canon} {value}")

    # barrack numbers
    if _BARRACK.match(low):
        num = re.search(r"\d+(?:-\d+)?", low).group(0)
        return ResolvedTag("place_where.barrack_number", f"Barrack {num}")

    # exact taxonomy match (canonical label + facet)
    hit = _INDEX.get(low)
    if hit:
        return ResolvedTag(hit[0], hit[1])

    # unknown -> freeform or drop
    return ResolvedTag("freeform", raw) if keep_freeform else None


def resolve_tags(names, *, keep_freeform: bool = True) -> list[ResolvedTag]:
    out: list[ResolvedTag] = []
    seen: set[str] = set()
    for n in names or []:
        rt = resolve_tag(n, keep_freeform=keep_freeform)
        if rt and rt.key not in seen:
            seen.add(rt.key)
            out.append(rt)
    return out


def tag_payload(names, *, keep_freeform: bool = True) -> tuple[list[dict], list[str]]:
    """Return (tags[], tag_labels[]) ready for the Qdrant payload."""
    resolved = resolve_tags(names, keep_freeform=keep_freeform)
    return [t.to_payload() for t in resolved], [t.key for t in resolved]
