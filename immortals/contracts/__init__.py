"""Versioned JSON contracts — the seams of the architecture."""

from .validate import ContractError, is_valid, validate, validate_self_described

__all__ = ["ContractError", "is_valid", "validate", "validate_self_described"]
