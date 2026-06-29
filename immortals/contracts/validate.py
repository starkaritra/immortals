"""Contract loading and validation for Immortals.

The versioned JSON Schemas in ``schemas/`` are the architecture's seams. Every plan,
artifact, manifest, and event crossing a boundary is validated here.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

SCHEMA_DIR = Path(__file__).parent / "schemas"

# Logical contract name -> schema file.
_SCHEMA_FILES = {
    "plan/v1": "plan.v1.json",
    "artifact/v1": "artifact.v1.json",
    "registry/v1": "registry.v1.json",
    "event/v1": "event.v1.json",
}


class ContractError(ValueError):
    """Raised when an instance fails its contract."""


@lru_cache(maxsize=None)
def _load_schema(name: str) -> dict[str, Any]:
    try:
        filename = _SCHEMA_FILES[name]
    except KeyError:
        raise KeyError(f"Unknown contract {name!r}; known: {sorted(_SCHEMA_FILES)}")
    return json.loads((SCHEMA_DIR / filename).read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def _validator(name: str) -> Draft202012Validator:
    return Draft202012Validator(_load_schema(name))


def is_valid(instance: Any, contract: str) -> bool:
    """Return True iff ``instance`` satisfies ``contract`` (e.g. ``"plan/v1"``)."""
    return _validator(contract).is_valid(instance)


def validate(instance: Any, contract: str) -> None:
    """Validate ``instance`` against ``contract``; raise :class:`ContractError` on failure.

    The contract may be passed explicitly, or inferred from the instance's own ``schema``
    field when ``contract`` matches it. Errors are aggregated for a readable message.
    """
    validator = _validator(contract)
    errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.path))
    if errors:
        detail = "; ".join(_format_error(e) for e in errors)
        raise ContractError(f"{contract} validation failed: {detail}")


def validate_self_described(instance: Any) -> str:
    """Validate using the instance's own ``schema`` field; return the contract name."""
    if not isinstance(instance, dict) or "schema" not in instance:
        raise ContractError("instance has no 'schema' field to self-describe its contract")
    contract = instance["schema"]
    validate(instance, contract)
    return contract


def _format_error(err: ValidationError) -> str:
    loc = "/".join(str(p) for p in err.path) or "<root>"
    return f"at {loc}: {err.message}"
