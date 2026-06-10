# text_lengths

Per-item text length (chars + words) for the Bergen-Belsen Omeka collection.

## Files

- `text_lengths.csv` — 740 rows. Columns: `id, item_type, title, chars, words`.
- `reproduce.py` — refetches live and recomputes.
- `metadata_categories.yaml` — field grouping used to pick which element_texts count as "text".

## Definition of "text"

For each item, concatenate the `text` of every `element_text` whose element name falls under the **Content Description (English)** category, joined with `".\n "`. Then:

- `chars` = `len(full_text)`
- `words` = `len(full_text.split())`

Element names included:

```
Translated Title (English)
Main Caption (English)
Additional Caption 1 (English)
Additional Caption 2 (English)
Translated Full Text Fragment (English)
Translated Text Snippet (English)
Display Label (English)
Translated Biographical Text (English)
Description
```

Matches the text-construction logic from `omeka-tools/notebooks/3.Link_Items_KG.ipynb`.

## Reproduce

```bash
pip install requests python-dotenv pyyaml

export OMEKA_API_URL=https://bb-g.futurememoryfoundation.org/api
export OMEKA_API_KEY=<your-key>

python reproduce.py
```

Overwrites `text_lengths.csv`.

## Source

`https://bb-g.futurememoryfoundation.org/api/items` (Future Memory Foundation, Bergen-Belsen).
Each `id` resolves to `https://bb-g.futurememoryfoundation.org/items/show/{id}`.
