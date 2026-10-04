"""Deterministic byte encodings for hashing and signing records."""

import json


def canonical_json(value: object) -> bytes:
    """Encode internal integer/string records as sorted compact UTF-8 JSON.

    This is a package-specific encoding, not a general canonical-JSON standard.
    """
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
