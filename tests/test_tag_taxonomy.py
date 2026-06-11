"""Resolver tests using REAL Westerbork tag names (from the public /api/tags)."""
import os
import sys

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from omeka_tools.tag_taxonomy import resolve_tag, resolve_tags, tag_payload


def _facet(name):
    rt = resolve_tag(name)
    return rt.facet if rt else None


def test_theme_main_and_sub():
    assert _facet("Forced Labor") == "theme_what"
    assert _facet("work detail") == "theme_what"
    assert _facet("Adaptation and Survival") == "theme_what"


def test_medium_person_time():
    assert _facet("photograph") == "medium_what"
    assert _facet("age 35-44") == "person_who.age_group"
    assert _facet("Male") == "person_who.gender_and_age"
    assert _facet("Roma and Sinti") == "person_who.reason_for_imprisonment"
    assert _facet("Transit camp") == "time_when.time_period"


def test_content_category():
    assert _facet("Daily Life & Camp Experience") == "theme_how.content_category"
    assert _facet("Reflections & Encounters") == "theme_how.content_category"


def test_tone_suffix_canonicalizes_to_taxonomy_label():
    rt = resolve_tag("somber (tone)")
    assert rt.facet == "language_how.tone_of_text"
    assert rt.label == "Somber"           # canonical label, not lowercase input
    # visual-tone variant still routed to tone facet
    assert resolve_tag("dark (visual tone)").facet == "language_how.tone_of_text"


def test_transit_and_origin_prefixes():
    assert _facet("deported to: Auschwitz-Birkenau") == "place_where.transit_destinations"
    assert resolve_tag("born in: Haren").facet == "person_who.city_village_country"
    assert resolve_tag("born in: Haren").label == "Born in: Haren"
    assert _facet("Arrived from: Kamp Ameersfoort") == "place_where.transit_destinations"


def test_barrack_numbers():
    assert _facet("barrack 75") == "place_where.barrack_number"
    assert resolve_tag("barracks 65-67").label == "Barrack 65-67"


def test_aiarlocation_kept_as_location_facet():
    rt = resolve_tag("AiARLocationBarracks65-67")
    assert rt.facet == "location" and rt.label == "AiARLocationBarracks65-67"


def test_app_markers_dropped():
    assert resolve_tag("ARLocationBarrack75") is None          # legacy AR* still dropped
    assert resolve_tag("start page") is None
    assert resolve_tag("KWBVR") is None


def test_freeform_kept_or_dropped():
    assert resolve_tag("prikkeldraad").facet == "freeform"
    assert resolve_tag("prikkeldraad", keep_freeform=False) is None


def test_tag_payload_shape_and_dedup():
    names = ["Forced Labor", "Forced Labor", "ARLocationBarrack75", "photograph"]
    tags, labels = tag_payload(names)
    assert "theme_what:Forced Labor" in labels
    assert "medium_what:Photograph" in labels   # canonical taxonomy casing
    assert len(tags) == len(labels) == 2          # dedup + AR dropped
    assert all(set(t) == {"facet", "label", "weight"} for t in tags)
