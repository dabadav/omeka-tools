"""Turn raw Omeka items into recommender-ready document dicts.

``content-engine`` imports ``omeka_to_documents`` from here (see
``content_engine.sources.omeka``); it was referenced but never implemented, which
left the whole Omeka -> Qdrant path dead. Each yielded dict validates against
``content_engine.contract.ContentDocument``.

The tag mapping -- flat Omeka tag string -> ``{facet, label, weight}`` -- is the
part the recommender depends on and is delegated entirely to ``taxonomy.to_tag``.
"""
from __future__ import annotations

from typing import Callable, Iterator, Optional

from .taxonomy import to_tags
from .utils import filter_json, get_public_url

# Omeka item_type name -> ContentDocument.content_type value.
_TYPE_MAP = {
    "still image": "image_item",
    "landscape item": "image_item",
    "moving image": "video_item",
    "sound": "audio_item",
    "oral history": "audio_item",
    "document": "text_item",
    "text": "text_item",
    "person": "text_item",
}


def _elements(item: dict) -> dict[str, list[str]]:
    """element name (lowercased) -> list of text values."""
    out: dict[str, list[str]] = {}
    for et in item.get("element_texts") or []:
        name = (et.get("element") or {}).get("name", "").strip().lower()
        text = (et.get("text") or "").strip()
        if name and text:
            out.setdefault(name, []).append(text)
    return out


def _content_type(item: dict) -> str:
    name = (item.get("item_type") or {}).get("name", "").strip().lower()
    return _TYPE_MAP.get(name, "text_item")


def _iter_items(
    client, *, collection_id: Optional[int], max_items: Optional[int], per_page: int
) -> Iterator[dict]:
    fetched = 0
    page = 1
    while True:
        params = {"per_page": per_page, "page": page}
        if collection_id is not None:
            params["collection"] = collection_id
        batch = client._get("items", params=params)
        if not batch:
            return
        for item in batch:
            yield item
            fetched += 1
            if max_items is not None and fetched >= max_items:
                return
        page += 1


def omeka_to_documents(
    client,
    *,
    collection_id: Optional[int] = None,
    max_items: Optional[int] = None,
    files_resolver: Optional[Callable[[int], list]] = None,
    per_page: int = 50,
    **_ignored,
) -> Iterator[dict]:
    """Yield ContentDocument-shaped dicts for items in an Omeka collection."""
    for raw in _iter_items(
        client, collection_id=collection_id, max_items=max_items, per_page=per_page
    ):
        item_id = raw["id"]
        el = _elements(raw)
        title = (el.get("title") or [""])[0]
        text = "\n\n".join(el.get("description", []) + el.get("text", [])).strip()
        creator = (el.get("creator") or [None])[0]

        flat = filter_json(raw).get("tags") or []
        # to_tags yields the granular tag plus a main-theme rollup for subtags;
        # ContentDocument dedups by canonical key so repeats collapse cleanly.
        tags = [tag for t in flat if t.get("name") for tag in to_tags(t["name"])]

        files_url = files_resolver(item_id) if files_resolver else []

        yield {
            "id": str(item_id),
            "title": title,
            "text": text,
            "content_type": _content_type(raw),
            "creator": creator,
            "tags": tags,
            "files_url": files_url,
            "image_url": files_url[0] if files_url else None,
            "public_url": get_public_url(item_id),
            "extra": {"omeka_item_type": (raw.get("item_type") or {}).get("name")},
        }
