"""Load the supplier (bidder) configuration used to fill commitment letters."""

from __future__ import annotations

from typing import Dict, Optional

import yaml

PLACEHOLDER = "______"

# Canonical supplier keys in display order.
SUPPLIER_KEYS = [
    "company_name",
    "company_type",
    "legal_representative",
    "address",
    "postal_code",
    "phone",
    "email",
    "bank_name",
    "bank_account",
    "authorized_representative",
    "authorized_representative_id",
    "date",
]


def load_supplier(path: Optional[str]) -> Dict[str, str]:
    """Read a supplier YAML file; missing / blank values are dropped."""
    if not path:
        return {}
    try:
        with open(path, encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
    except FileNotFoundError:
        return {}
    return {k: v for k, v in data.items() if v not in (None, "")}


def value(supplier: Dict[str, str], key: str) -> str:
    """Return the supplier value for *key*, or the placeholder when absent."""
    val = supplier.get(key)
    if val is None or str(val).strip() == "":
        return PLACEHOLDER
    return str(val).strip()
