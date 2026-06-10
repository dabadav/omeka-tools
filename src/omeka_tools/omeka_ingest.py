"""Step 1 (Omeka formatter): Omeka item -> recommender ContentDocument contract.

Emits plain dicts matching the ai-engine ContentDocument contract (so omeka-tools
stays decoupled from ai-engine). Feed the output to ai-engine's ContentIngestor.

    from omeka_tools.client import OmekaClient
    from omeka_tools.omeka_ingest import omeka_to_documents
    docs = list(omeka_to_documents(OmekaClient()))   # -> contract dicts

`format_item` is pure (one item dict -> contract dict) and unit-testable; `iter_items`
does the paginated IO. Element field names default to Westerbork's schema and are
overridable per instance.
"""
from __future__ import annotations
from typing import Callable, Iterable, Iterator, Optional

from .tag_taxonomy import tag_payload

# Westerbork element-name defaults (override if the instance differs).
TITLE_FIELDS = ["Title", "Translated Titles (multiple languages)", "DisplayLabel"]
TEXT_FIELDS = [
    "Full Text Fragment (Original Language)",
    "Translated Full Text Fragments and Snippets (multiple languages)",
    "Captions (various languages)",
    "Historical Caption",
    "Transcription from depicted text",
    "Description",
]
CREATOR_FIELDS = ["Creator"]

_TYPE_MAP = {
    "still image": "image_item",
    "text item": "text_item",
    "oral history": "audio_item",
    "sound": "audio_item",
    "moving image": "video_item",
    "physical object": "image_item",
}


def _flatten(item: dict) -> dict[str, list[str]]:
    flat: dict[str, list[str]] = {}
    for et in item.get("element_texts", []) or []:
        name = (et.get("element") or {}).get("name")
        if name is not None:
            flat.setdefault(name, []).append(et.get("text", ""))
    return flat


def _first(flat: dict[str, list[str]], fields: list[str]) -> Optional[str]:
    for f in fields:
        if flat.get(f):
            return flat[f][0]
    return None


def _concat(flat: dict[str, list[str]], fields: list[str]) -> str:
    parts: list[str] = []
    for f in fields:
        parts.extend(flat.get(f, []))
    return "\n\n".join(p for p in parts if p)


def _isnum(s) -> bool:
    try:
        float(s)
        return True
    except (TypeError, ValueError):
        return False


def _map_type(item_type: dict) -> str:
    name = (item_type or {}).get("name") or ""
    return _TYPE_MAP.get(name.strip().lower(), "text_item")


def format_item(
    item: dict,
    *,
    files_url: Optional[list[str]] = None,
    public_url: Optional[str] = None,
    title_fields: list[str] = TITLE_FIELDS,
    text_fields: list[str] = TEXT_FIELDS,
    creator_fields: list[str] = CREATOR_FIELDS,
    keep_freeform: bool = True,
) -> dict:
    """Pure: one Omeka item dict -> a ContentDocument-shaped dict."""
    flat = _flatten(item)

    tag_names = [t.get("name") for t in item.get("tags", []) or [] if t.get("name")]
    tags, _labels = tag_payload(tag_names, keep_freeform=keep_freeform)

    lats = [v for n in flat for v in flat[n] if "latitude" in n.lower()]
    lons = [v for n in flat for v in flat[n] if "longitude" in n.lower()]
    locations = [
        {"lat": float(a), "lon": float(b)}
        for a, b in zip(lats, lons) if _isnum(a) and _isnum(b)
    ]
    geo_keys = ("latitude", "longitude", "altitude", "elevation", "viewpoint", "coordinates")
    geo_meta = {n: flat[n][0] for n in flat if any(k in n.lower() for k in geo_keys)} or None
    time_meta = {n: flat[n][0] for n in flat if "date" in n.lower()} or None

    return {
        "id": str(item["id"]),
        "title": _first(flat, title_fields) or "",
        "text": _concat(flat, text_fields),
        "content_type": _map_type(item.get("item_type") or {}),
        "tags": tags,
        "creator": _first(flat, creator_fields),
        "locations": locations,
        "geo_metadata": geo_meta,
        "time_metadata": time_meta,
        "files_url": files_url or [],
        "public_url": public_url,
    }


def iter_items(client, *, per_page: int = 50, max_items: Optional[int] = None) -> Iterator[dict]:
    """Paginate the Omeka /items endpoint."""
    page, seen = 1, 0
    while True:
        items = client._get("items", params={"page": page, "per_page": per_page})
        if not items:
            return
        for it in items:
            yield it
            seen += 1
            if max_items and seen >= max_items:
                return
        page += 1


def omeka_to_documents(
    client,
    *,
    per_page: int = 50,
    max_items: Optional[int] = None,
    files_resolver: Optional[Callable[[int], list[str]]] = None,
    public_url_resolver: Optional[Callable[[int], str]] = None,
    **fmt_kwargs,
) -> Iterator[dict]:
    """Fetch + format every item into contract dicts ready for ContentIngestor."""
    for item in iter_items(client, per_page=per_page, max_items=max_items):
        item_id = item["id"]
        files_url = files_resolver(item_id) if files_resolver else None
        public_url = public_url_resolver(item_id) if public_url_resolver else item.get("url")
        yield format_item(item, files_url=files_url, public_url=public_url, **fmt_kwargs)
