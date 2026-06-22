"""Re-export of the shared :mod:`memorise_taxonomy` package.

The tag taxonomy and match-key normalization are now a single source of truth in
``memorise-taxonomy`` so the survey side (ai-engine) and the content-ingest side
can never drift. This shim keeps existing ``omeka_tools.taxonomy`` imports working.
"""
from memorise_taxonomy import (  # noqa: F401
    ALIASES,
    DEFAULT_FACET,
    FacetAssignment,
    assign_facet,
    normalize_key,
    normalize_label,
    review_vocab,
    to_tag,
)
