"""
Reproduce text_lengths.csv from a live Omeka Classic API.

Per-item text length (chars + words), where "text" =
concatenation of all `Content Description (English)` element_texts
joined with ".\n ", matching notebook 3 (Link_Items_KG).

Usage:
    pip install requests python-dotenv pyyaml
    OMEKA_API_URL=https://bb-g.futurememoryfoundation.org/api \\
    OMEKA_API_KEY=<key> \\
    python reproduce.py

Output: text_lengths.csv (id, item_type, title, chars, words)
"""
import csv
import os
import sys
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv


HERE = Path(__file__).parent
CATEGORIES_YAML = HERE / "metadata_categories.yaml"
OUTPUT_CSV = HERE / "text_lengths.csv"
TARGET_CATEGORY = "Content Description (English)"
TITLE_ELEMENT = "Title"


def fetch_all_items(api_url, api_key):
    items = []
    page = 1
    while True:
        r = requests.get(
            f"{api_url.rstrip('/')}/items",
            params={"key": api_key, "page": page, "per_page": 50},
            timeout=60,
        )
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        items.extend(batch)
        page += 1
    return items


def load_target_elements():
    with open(CATEGORIES_YAML, encoding="utf-8") as f:
        cats = yaml.safe_load(f)
    return set(cats[TARGET_CATEGORY])


def english_text(item, target_elements):
    parts = []
    for et in item.get("element_texts", []):
        name = ((et.get("element") or {}).get("name")) or ""
        if name in target_elements:
            parts.append(str(et.get("text", "")))
    return ".\n ".join(p for p in parts if p)


def item_title(item):
    for et in item.get("element_texts", []):
        name = ((et.get("element") or {}).get("name")) or ""
        if name == TITLE_ELEMENT:
            return et.get("text", "")
    return ""


def main():
    load_dotenv()
    api_url = os.getenv("OMEKA_API_URL")
    api_key = os.getenv("OMEKA_API_KEY")
    if not api_url or not api_key:
        print("ERROR: set OMEKA_API_URL and OMEKA_API_KEY (env or .env)", file=sys.stderr)
        sys.exit(1)

    target_elements = load_target_elements()
    print(f"target elements ({len(target_elements)}): {sorted(target_elements)}")

    items = fetch_all_items(api_url, api_key)
    print(f"fetched {len(items)} items from {api_url}")

    rows = []
    for it in items:
        text = english_text(it, target_elements)
        rows.append({
            "id": it["id"],
            "item_type": (it.get("item_type") or {}).get("name", ""),
            "title": item_title(it),
            "chars": len(text),
            "words": len(text.split()),
        })

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "item_type", "title", "chars", "words"])
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {OUTPUT_CSV} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
