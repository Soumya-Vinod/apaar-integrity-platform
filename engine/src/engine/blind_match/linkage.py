# Owner: Dev A
"""Candidate generation over encoded records."""

from __future__ import annotations

from engine.types import EncodedRecord, MatchCandidate


def find_candidates(records: list[EncodedRecord], threshold: float) -> list[MatchCandidate]:
    """Return pairs of records whose Dice similarity is at least ``threshold``.

    Intended algorithm:
    1. Block records by ``birth_year_hash`` so only records with the same hashed
       birth year are compared.
    2. Within each block, compare every pair with ``encoder.dice``.
    3. Skip pairs sharing the same non-empty APAAR ID (exact duplicates are covered
       by DUP_CROSS_INSTITUTION).
    4. Emit a MatchCandidate per pair at or above ``threshold``, sorted by Dice descending.
    """
    raise NotImplementedError
