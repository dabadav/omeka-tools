from enum import Enum

import pandas as pd
import yaml


class FileUrlType(str, Enum):
    ORIGINAL = "original"
    FULLSIZE = "fullsize"
    THUMBNAIL = "thumbnail"
    SQUARE_THUMBNAIL = "square_thumbnail"


def extract_file_urls(files: list, url_type: str = FileUrlType.ORIGINAL.value) -> list:
    """Validate against FileUrlType and extract corresponding URLs."""
    try:
        url_type_enum = FileUrlType(url_type)
    except ValueError:
        allowed = [e.value for e in FileUrlType]
        raise ValueError(
            f"Invalid file URL type '{url_type}'. Must be one of: {allowed}"
        )

    return [
        file.get("file_urls", {}).get(url_type_enum.value)
        for file in files
        if file.get("file_urls", {}).get(url_type_enum.value)
    ]


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


def get_public_url(item_id):
    return f"https://bb-g.futurememoryfoundation.org/items/show/{item_id}"


def load_yaml(yaml_path):
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data


def reverse_yaml(category_to_fields):
    field_to_category = {
        field: category
        for category, fields in category_to_fields.items()
        for field in fields
    }
    return field_to_category
