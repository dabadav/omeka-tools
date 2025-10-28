import os

import pandas as pd
import requests
from dotenv import load_dotenv

# Load .env variables
load_dotenv()
API_KEY = os.getenv("OMEKA_API_KEY")
API_URL = os.getenv("OMEKA_API_URL")
HEADERS = {}  # Omeka Classic doesn't use headers for auth


def fetch_all_items():
    endpoint = f"/items?key={API_KEY}&pretty_print"
    response = requests.get(f"{API_URL}{endpoint}")
    if response.status_code == 200:
        data = response.json()
        print(f"Retrieved {len(data)} items.")
        return data
    else:
        raise Exception(
            f"Failed to fetch data: {response.status_code} - {response.text}"
        )


def filter_json(item):
    return {
        "id": item["id"],
        "item_type__id": item.get("item_type", {}).get("id"),
        "item_type__name": item.get("item_type", {}).get("name"),
        "files__count": item.get("files", {}).get("count"),
        "tags": item.get("tags"),
        "element_texts": item.get("element_texts"),
    }


def extract_tags(filtered_json):
    tags_columns = [
        "id",
        "item_type__id",
        "item_type__name",
        "files__count",
        "tags__id",
        "tags__name",
    ]
    df_tags = pd.json_normalize(
        filtered_json,
        record_path="tags",
        meta=["id", "item_type__id", "item_type__name", "files__count"],
        sep="__",
        record_prefix="tags__",
    )
    return df_tags[tags_columns]


def extract_metadata(filtered_json):
    element_columns = [
        "id",
        "item_type__id",
        "item_type__name",
        "files__count",
        "element_set__id",
        "element_set__name",
        "element__id",
        "element__name",
        "text",
    ]
    df_elements = pd.json_normalize(
        filtered_json,
        record_path="element_texts",
        meta=["id", "item_type__id", "item_type__name", "files__count"],
        sep="__",
    )
    return df_elements[element_columns]


def get_default_item(exhibit_pages):
    # Specific function to get the first item id of an exhibition
    return exhibit_pages[1]['page_blocks'][0]['attachments'][0]['item']['id']