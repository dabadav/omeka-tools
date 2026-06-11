import os
import sys

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from omeka_tools.omeka_ingest import format_item, iter_items, omeka_to_documents

# An Omeka-Classic-shaped item (matches the live Westerbork /api/items structure).
ITEM = {
    "id": 1448,
    "url": "https://westerbork.futurememoryfoundation.org/api/items/1448",
    "item_type": {"name": "Still Image"},
    "tags": [
        {"name": "Forced Labor"},
        {"name": "work detail"},
        {"name": "somber (tone)"},
        {"name": "ARLocationBarrack75"},   # app marker -> dropped
        {"name": "deported to: Auschwitz-Birkenau"},
    ],
    "element_texts": [
        {"element_set": {"name": "Dublin Core"}, "element": {"name": "Title"}, "text": "Werk aan de spoorlijn"},
        {"element_set": {"name": "Dublin Core"}, "element": {"name": "Creator"}, "text": "Rudolf Breslauer"},
        {"element_set": {"name": "Item Type Metadata"},
         "element": {"name": "Full Text Fragment (Original Language)"}, "text": "Prisoners building the line."},
        {"element_set": {"name": "Item Type Metadata"},
         "element": {"name": "Viewpoint Latitude"}, "text": "52.9320"},
        {"element_set": {"name": "Item Type Metadata"},
         "element": {"name": "Viewpoint Longitude"}, "text": "6.6075"},
        {"element_set": {"name": "Item Type Metadata"},
         "element": {"name": "Dates of Creation"}, "text": "1944"},
    ],
}


def test_format_item_builds_contract():
    doc = format_item(ITEM, files_url=["http://x/a.jpg"], public_url="http://pub/1448")
    assert doc["id"] == "1448"
    assert doc["title"] == "Werk aan de spoorlijn"
    assert doc["text"] == "Prisoners building the line."
    assert doc["creator"] == "Rudolf Breslauer"
    assert doc["content_type"] == "image_item"
    assert doc["files_url"] == ["http://x/a.jpg"]
    assert doc["locations"] == [{"lat": 52.9320, "lon": 6.6075}]
    assert doc["time_metadata"] == {"Dates of Creation": "1944"}


def test_format_item_resolves_and_filters_tags():
    doc = format_item(ITEM)
    labels = [f"{t['facet']}:{t['label']}" for t in doc["tags"]]
    assert "theme_what:Forced Labor" in labels
    assert "theme_what:work detail" in labels
    assert "language_how.tone_of_text:Somber" in labels
    assert "place_where.transit_destinations:Deported to: Auschwitz-Birkenau" in labels
    assert not any("ARLocation" in l for l in labels)  # app marker dropped


def test_main_caption_used_as_text_for_object_items():
    # mirrors live item 2512: text lives in "Main Caption (English)", title in "Translated Title (English)"
    item = {
        "id": 2512,
        "item_type": {"name": "Physical Object"},
        "tags": [{"name": "Forced Labor"}, {"name": "Object"}, {"name": "descriptive (tone)"}],
        "element_texts": [
            {"element_set": {"name": "Dublin Core"}, "element": {"name": "Title"}, "text": "Ring"},
            {"element_set": {"name": "Dublin Core"}, "element": {"name": "Translated Title (English)"},
             "text": "Ring made of airplane glass"},
            {"element_set": {"name": "Item Type Metadata"}, "element": {"name": "Main Caption (English)"},
             "text": "This ring is made of glass from an airplane cockpit."},
        ],
    }
    doc = format_item(item)
    assert doc["title"] == "Ring made of airplane glass"          # English translation preferred
    assert doc["text"] == "This ring is made of glass from an airplane cockpit."
    labels = [f"{t['facet']}:{t['label']}" for t in doc["tags"]]
    assert "theme_what:Forced Labor" in labels
    assert "medium_what:object" in labels                      # canonical taxonomy casing
    assert "language_how.tone_of_text:descriptive" in labels


def test_strips_html_from_caption_text():
    item = {
        "id": 3, "item_type": {"name": "Still Image"}, "tags": [],
        "element_texts": [
            {"element_set": {"name": "x"}, "element": {"name": "Main Caption (English)"},
             "text": '<p class="p1"><span class="s1">Barrack 3.<br /><br /></span>Built in 1939.</p>'},
        ],
    }
    doc = format_item(item)
    assert "<" not in doc["text"] and "class" not in doc["text"]
    assert "Barrack 3." in doc["text"] and "Built in 1939." in doc["text"]


def test_iter_items_paginates_then_stops():
    class FakeClient:
        def __init__(self):
            self.pages = {1: [ITEM, ITEM], 2: [ITEM], 3: []}
        def _get(self, endpoint, params=None):
            return self.pages.get(params["page"], [])

    got = list(iter_items(FakeClient(), per_page=2))
    assert len(got) == 3


def test_iter_items_passes_collection_filter():
    seen = []

    class FakeClient:
        def _get(self, endpoint, params=None):
            seen.append(params)
            return [ITEM] if params["page"] == 1 else []

    list(iter_items(FakeClient(), collection=4))
    assert seen[0]["collection"] == 4


def test_omeka_to_documents_end_to_end():
    class FakeClient:
        def _get(self, endpoint, params=None):
            return [ITEM] if params["page"] == 1 else []

    docs = list(omeka_to_documents(FakeClient(), files_resolver=lambda i: [f"http://f/{i}.jpg"]))
    assert len(docs) == 1
    assert docs[0]["files_url"] == ["http://f/1448.jpg"]
    assert docs[0]["public_url"] == ITEM["url"]
