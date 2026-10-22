# Owner: Dev A
"""Bloom-filter encoding of identity fields for privacy-preserving duplicate detection."""

from __future__ import annotations


def encode_identity(fields: dict[str, str], secret: bytes, bits: int = 1024, k: int = 20) -> bytes:
    """Encode identity fields into a Bloom filter of ``bits`` bits.

    Intended algorithm:
    1. Normalise each field value (lowercase, strip accents and punctuation, collapse spaces).
    2. Split each value into character bigrams, padded with a leading and trailing space.
       Prefix each bigram with its field name so equal bigrams in different fields differ.
    3. For each bigram, derive ``k`` bit positions with HMAC-SHA256 keyed by ``secret``
       (double hashing: position_i = (h1 + i * h2) mod bits).
    4. Set those bits and return the filter as ``bits // 8`` bytes.
    """
    raise NotImplementedError


def dice(a: bytes, b: bytes) -> float:
    """Dice coefficient of two equal-length bit arrays: 2 * |A and B| / (|A| + |B|).

    Returns 1.0 when neither array has any bit set.
    """
    if len(a) != len(b):
        raise ValueError("Bloom filters must have the same length")
    int_a = int.from_bytes(a, "big")
    int_b = int.from_bytes(b, "big")
    total = int_a.bit_count() + int_b.bit_count()
    if total == 0:
        return 1.0
    return 2 * (int_a & int_b).bit_count() / total
