import yaml


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
