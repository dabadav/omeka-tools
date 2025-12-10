# client.py

import os
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

load_dotenv()


class OmekaClient:
    def __init__(self, base_url=None, api_key=None):
        self.base_url = base_url or os.getenv("OMEKA_API_URL").rstrip("/")
        self.api_key = api_key or os.getenv("OMEKA_API_KEY")
        self.headers = {}

    def _get(self, endpoint, params=None):
        if params is None:
            params = {}
        params["key"] = self.api_key
        params["pretty_print"] = ""

        if endpoint.startswith("http"):
            url = endpoint
        else:
            url = f"{self.base_url}/{endpoint.lstrip('/')}"

        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(
                f"GET {url} failed: {response.status_code} - {response.text}"
            )

    # -------- Core endpoint methods -------- #
    def get_item(self, item_id):
        return self._get(f"items/{item_id}")

    def get_collection(self, collection_id):
        return self._get(f"collections/{collection_id}")

    def get_exhibit(self, exhibit_id):
        return self._get(f"exhibits/{exhibit_id}")

    def get_user(self, user_id):
        return self._get(f"users/{user_id}")

    def get_files_by_item(self, item_id):
        return self._get("files", params={"item": item_id})

    def get_tag(self, tag_id):
        return self._get(f"tags/{tag_id}")

    def get_element_set(self, set_id):
        return self._get(f"element_sets/{set_id}")

    def get_element(self, element_id):
        return self._get(f"elements/{element_id}")

    def get_exhibit_pages(self, exhibit_id):
        return self._get("exhibit_pages", params={"exhibit": exhibit_id})

    def get_exhibit_pages_by_item(self, item_id):
        return self._get("exhibit_pages", params={"item": item_id})

    # -------- Universal URL resolver -------- #
    def resolve_url(self, full_url):
        """Fetch Omeka API resource by full URL."""
        parsed = urlparse(full_url)
        if self.base_url in full_url:
            relative_path = full_url.split(self.base_url)[-1].lstrip("/")
        else:
            relative_path = parsed.path.lstrip("/")
        if parsed.query:
            relative_path += f"?{parsed.query}"
        return self._get(relative_path)
