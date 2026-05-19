# omeka-tools

Python toolkit to query the **Omeka Classic** REST API, flatten item metadata into tabular form, normalize fields (dates, geo, file URLs), and prepare data for downstream KG / vector-search pipelines.

Built around the [Bergen-Belsen collection](https://bb-g.futurememoryfoundation.org/) but generic over any Omeka Classic instance.

---

## Capabilities

| Capability | Module / Notebook | Status |
|---|---|---|
| Read items, collections, exhibits, files, tags, element sets | `OmekaClient` | ✅ |
| Resolve any Omeka API URL | `OmekaClient.resolve_url` | ✅ |
| Flatten `element_texts` → wide DataFrame | `omeka_extractor`, `utils` | ✅ |
| Extract file URLs (original / fullsize / thumbnail / square) | `utils.extract_file_urls` | ✅ |
| Group metadata fields into semantic categories | `metadata_categories*.yaml` + `utils.reverse_yaml` | ✅ |
| Normalize fuzzy dates → RFC3339 | `standarize.dates` | ✅ |
| Embed items + index into Qdrant (semantic + geo + time filter) | notebook `B.Omeka2Qdrant` | ✅ (notebook only) |
| Knowledge graph linking / prep | notebooks `3`, `A`, `C` | ✅ (notebook only) |
| Swap Omeka instance / credentials | `.env` (`OMEKA_API_URL`, `OMEKA_API_KEY`) | ✅ (one blocker: `get_public_url` hardcoded — see Customization) |
| Write back to Omeka (POST/PUT/DELETE) | — | ❌ not in scope |

---

## Install

```bash
poetry install
# or
pip install requests pandas python-dotenv pyyaml dateparser qdrant-client sentence-transformers
```

> Note: `pyproject.toml` currently does **not** declare runtime deps explicitly. Install manually until that is fixed.

Create `.env` at repo root:

```dotenv
OMEKA_API_URL=https://bb-g.futurememoryfoundation.org/api
OMEKA_API_KEY=<your-key>
```

---

## Repo layout

```
omeka-tools/
├── src/omeka_tools/           # installable package
│   ├── client.py              # OmekaClient — REST wrapper (GET only)
│   ├── omeka_extractor.py     # fetch_all_items + DataFrame extractors
│   ├── utils.py               # file URLs, public URL builder, yaml helpers
│   └── standarize/
│       ├── dates.py           # find_date_patterns, normalize_date, extract_and_standardize_dates
│       └── text.py            # (empty)
├── notebooks/                 # end-to-end pipeline (see below)
│   └── data/                  # extracted CSVs / JSON / HTML reports
├── metadata_categories.yaml         # per-language field grouping
├── metadata_categories_global.yaml  # cross-language field grouping (11 categories)
├── client.py                  # ⚠ legacy duplicate of src/omeka_tools/client.py
├── omeka_extractor.py         # ⚠ legacy duplicate of src/omeka_tools/omeka_extractor.py
└── pyproject.toml
```

Root-level `client.py` and `omeka_extractor.py` are kept for notebook back-compat (`sys.path.append("..")`). Prefer `from omeka_tools import OmekaClient` in new code.

---

## Quick start

### Fetch one item

```python
from omeka_tools import OmekaClient

client = OmekaClient()  # reads OMEKA_API_URL / OMEKA_API_KEY from .env
item = client.get_item(839)
files = client.get_files_by_item(839)
collection = client.get_collection(item["collection"]["id"])

# follow any URL in the JSON payload
resolved = client.resolve_url(item["files"]["url"])
```

`OmekaClient` methods:

| Method | Endpoint |
|---|---|
| `get_item(item_id)` | `/items/{id}` |
| `get_collection(collection_id)` | `/collections/{id}` |
| `get_exhibit(exhibit_id)` | `/exhibits/{id}` |
| `get_exhibit_pages(exhibit_id)` | `/exhibit_pages?exhibit={id}` |
| `get_exhibit_pages_by_item(item_id)` | `/exhibit_pages?item={id}` |
| `get_files_by_item(item_id)` | `/files?item={id}` |
| `get_user(user_id)` | `/users/{id}` |
| `get_tag(tag_id)` | `/tags/{id}` |
| `get_element_set(set_id)` | `/element_sets/{id}` |
| `get_element(element_id)` | `/elements/{id}` |
| `resolve_url(full_url)` | any |

### Extract all items → DataFrame

```python
import omeka_tools as ot
from omeka_tools.omeka_extractor import fetch_all_items

raw = fetch_all_items()                       # list[dict] from /items
items = [ot.filter_json(i) for i in raw]      # keep id, type, files count, tags, element_texts
tags_df = ot.extract_tags(items)              # 1 row per (item, tag)
metadata_df = ot.extract_metadata(items)      # 1 row per (item, element_text)
```

`metadata_df` columns:
`id, item_type__id, item_type__name, files__count, element_set__id, element_set__name, element__id, element__name, text`

### Category-based field grouping

```python
from omeka_tools.utils import load_yaml, reverse_yaml

categories = load_yaml("metadata_categories_global.yaml")
field_to_category = reverse_yaml(categories)
# {'FormerDB-ID': 'Identification', 'Viewpoint Latitude': 'Spatial Data', ...}

metadata_df["category"] = metadata_df["element__name"].map(field_to_category)
```

Two YAML files:
- `metadata_categories.yaml` — keeps language-specific buckets (e.g. *Content Description (English)*). Use when you care about language splits.
- `metadata_categories_global.yaml` — collapses languages (11 buckets). Use for analysis / KG payloads.

### Extract file URLs

```python
from omeka_tools.utils import extract_file_urls

files = client.get_files_by_item(839)
thumb_urls = extract_file_urls(files, url_type="thumbnail")
# url_type ∈ {"original", "fullsize", "thumbnail", "square_thumbnail"}
```

### Normalize messy dates

```python
from omeka_tools.standarize.dates import (
    find_date_patterns, normalize_date, extract_and_standardize_dates
)

find_date_patterns("around xx/04/1945 to 10.04.1945")
# ['xx/04/1945', '10.04.1945']

normalize_date("xx/04/1945")    # '1945-04-01T00:00:00Z'
normalize_date("1944")          # '1944-01-01T00:00:00Z'

extract_and_standardize_dates({"Dates of Creation": "1944-05-04", "note": "n/a"})
# {'Dates of Creation': ['1944-05-04T00:00:00Z']}
```

Handles: full ISO, year-only, year-month, `xx/xx/yyyy`, `dd.mm.yyyy`, bracketed `[..]`. Output always RFC3339 UTC.

---

## Pipeline notebooks

Numbered notebooks run sequentially; lettered notebooks are independent stages.

| # | Notebook | In | Out | What it does |
|---|---|---|---|---|
| 1 | `1.Extract_Omeka_Items` | Omeka API | `metadata_df.csv` (10,886 rows / 740 items) | Pull all items, flatten `element_texts` |
| 2 | `2.Analyze_Omeka_Metadata` | `metadata_df.csv` + yaml | `metadata_subset_df.csv` (567 items) | Coverage analysis, drop test/inconsistent rows |
| 3 | `3.Link_Items_KG` | subset | `bergen-belsen-omeka.csv` (374 items) | Collapse to wide format, extract geo (lat/lon/elev × viewpoint/origin/reference), normalize dates |
| A | `A.Prepare_for_KG_Integration` | wide CSV | `omeka_items_wide.parquet`, `omeka_times.json` | Priority field merging, geo + temporal payloads |
| B | `B.Omeka2Qdrant` | parquet | Qdrant collection `omeka_items` | Embed title+text with `all-MiniLM-L6-v2` (384-d), upsert with payload, datetime index → semantic + date-filter search |
| C | `C.Text2KG_Preparation` | times JSON | `omeka_bb_dataset.html` / `.pdf`, `omeka_times_fixed.json` | Date normalization audit, sortable HTML + PDF report |

> ⚠ Notebook B has Qdrant URL + API key **hardcoded**. Move to `.env` before sharing.

---

## Customization

### Point at a different Omeka instance

Two-step swap.

**1. Edit `.env`** — the client reads URL + key from env at construction.

```dotenv
OMEKA_API_URL=https://my-other-omeka.org/api
OMEKA_API_KEY=<your-key>
```

Or pass directly, bypassing env:

```python
client = OmekaClient(
    base_url="https://my-other-omeka.org/api",
    api_key="<your-key>",
)
```

`OmekaClient.__init__` (src/omeka_tools/client.py:13) prefers constructor args over env, so both work.

**2. Override `get_public_url`** — it is **hardcoded** to the Bergen-Belsen host:

```python
# src/omeka_tools/utils.py:82
def get_public_url(item_id):
    return f"https://bb-g.futurememoryfoundation.org/items/show/{item_id}"
```

Quick fix at call site:

```python
def get_public_url(item_id, host="https://my-other-omeka.org"):
    return f"{host}/items/show/{item_id}"
```

Better fix: read `OMEKA_PUBLIC_URL` from env and default to deriving it from `OMEKA_API_URL` (strip trailing `/api`). Not yet in repo — small patch if you want it.

**3. Element / element_set IDs may differ across Omeka instances.** The Bergen-Belsen-specific element IDs (e.g. `123 = Translated Title (German)`) are encoded only in `metadata_categories*.yaml` *by name*, not by ID — so as long as the target instance uses the same element names, the YAML categorization works unchanged. If element names differ, edit the YAMLs.

**4. Hardcoded Qdrant config** in `notebooks/B.Omeka2Qdrant.ipynb` is independent — does not affect Omeka swap, but move it to `.env` before publishing.

### Add a new endpoint

Read-only endpoints follow a one-line pattern in `OmekaClient`:

```python
def get_thing(self, thing_id):
    return self._get(f"things/{thing_id}")
```

### Re-categorize metadata

Edit `metadata_categories_global.yaml` (or the per-language file). The category index is rebuilt by `reverse_yaml` at load time — no code change.

---

## Known gaps

- `pyproject.toml` declares no runtime dependencies — install manually.
- Root `client.py` and `omeka_extractor.py` duplicate the package; root `client.py:79` has a dead duplicate `return`.
- `standarize/text.py` is empty.
- `utils.get_public_url` is hardcoded to the Bergen-Belsen host — blocks clean instance swap (workaround in Customization).
- Qdrant credentials hardcoded in notebook B.
- No tests.
- Read-only; no POST/PUT/DELETE (out of scope).
