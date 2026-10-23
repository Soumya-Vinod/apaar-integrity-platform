<!-- Owner: Dev A -->
# engine

Integrity engine for the APAAR Integrity Platform. The backend imports it as `engine` (editable dependency).

| Module | Purpose | Status |
| --- | --- | --- |
| `engine.types` | Shared dataclasses (`MatchCase`, `Signal`, `IntegrityScore`, etc.) | done |
| `engine.config` | Engine configuration defaults | done |
| `engine.routers` | FastAPI router endpoints (`/engine`, `/engine/health`, `/engine/blind-match`) | done |
| `engine.blind_match.encoder` | Text normalization, character bigrams, birth year salting, HMAC Bloom-filter encoding | done |
| `engine.blind_match.similarity` | Dice and Jaccard similarity metrics over bit arrays | done |
| `engine.blind_match.models` | `BloomFilter`, `StudentRecord`, `LinkageMatch`, and `ReviewCaseRepository` interfaces | done |
| `engine.blind_match.linkage` | Candidate pairs blocked on hashed birth year with Dice threshold filtering | done |
| `engine.blind_match.service` | `BlindMatchService` and exact APAAR cross-institution duplicate detection | done |
| `engine.signals.rules` | Rule-based signals | stub |
| `engine.anomaly.isolation` | Isolation Forest ranking of institutions | stub |
| `engine.scoring.integrity` | Integrity Score 0-100 | stub |
| `engine.eval.harness` / `engine.evaluation` | Precision, recall and F1 per signal against datagen ground truth | stub |

## Blind Match Architecture

The Blind Match engine enables privacy-preserving duplicate student detection across AICTE-approved institutions without exposing raw Personally Identifiable Information (PII) to central storage or untrusted third parties.

```
Student PII (Name, DOB, Parents' Names)
                ↓
    [1. Normalization] (NFKD, lowercase, strip punctuation/spaces)
                ↓
    [2. Bigram Generation] ("RAHUL" → "ra", "ah", "hu", "ul")
                ↓
    [3. Birth Year Salting & Scoping] (e.g. "2004:student_name:ra")
                ↓
    [4. HMAC-SHA256 Double Hashing] (k=20 bit positions via h1 + i*h2 mod 1024)
                ↓
    [5. Bloom Filter Encoding] (1024-bit immutable bit array)
                ↓
    [6. Hashed Birth Year Blocking] (HMAC-SHA256 block key)
                ↓
    [7. Pairwise Dice Similarity Linkage] (Dice >= MATCH_THRESHOLD)
                ↓
    [8. Cross-Institution Review Cases] (MatchCase outputs)
```

### Bloom Filter Explanation

1. **Text Normalization**: Unicode text is decomposed into ASCII base forms via NFKD, converted to lowercase, stripped of non-alphanumeric punctuation, and trimmed of excess whitespace.
2. **Bigram Extraction**: Field values are converted into 2-character sliding shingles (e.g., `"RAHUL"` produces `["ra", "ah", "hu", "ul"]`).
3. **Birth Year Salting**: Bigram tokens are prefixed with the student's birth year and field name (`{birth_year}:{field_name}:{bigram}`). This ensures cross-field separation and defends against frequency analysis across birth cohorts.
4. **HMAC-SHA256 Double Hashing**: Each token is hashed using HMAC-SHA256 keyed with `BLIND_MATCH_SECRET`. The 32-byte digest is split into `h1` and `h2`, generating $k=20$ unique bit positions inside a 1024-bit vector:
   $$\text{position}_i = (h1 + i \times h2) \pmod{1024}$$
5. **Configurable Field Weights**: Weights per field determine the proportion of bit positions allocated.

### Dice Similarity

The Dice similarity coefficient quantifies the bitwise overlap between two 1024-bit Bloom filters $A$ and $B$:

$$\text{Dice}(A, B) = \frac{2 \times |A \cap B|}{|A| + |B|}$$

- $\text{Dice} = 1.0$ for identical student profiles.
- $\text{Dice} \approx 0.85\text{--}0.95$ for profiles with minor typos or transliteration discrepancies.
- $\text{Dice} < 0.70$ for distinct individuals.

### Privacy Guarantees

- **One-Way Transformation**: Cryptographic HMAC-SHA256 prevents inversion of Bloom filters back into raw student names.
- **Cohort Salting**: Using hashed birth year salting thwarts dictionary and frequency attacks across the national student dataset.
- **Non-PII Linkage**: Only Bloom filter encodings and hashed block keys are shared for pairwise linkage. Raw names and Aadhaar/APAAR identities remain protected.

### Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `MATCH_THRESHOLD` | `0.85` | Minimum Dice similarity required to flag a potential cross-institution duplicate. |
| `MODEL_VERSION` | `0.1.0` | Active model / pipeline version. |
| `BLIND_MATCH_SECRET` | `default-insecure-blind-match-key-32b` | Secret HMAC key used to derive Bloom filter bit positions and block hashes. |

### API Usage

#### POST `/engine/blind-match`

Submits student records to execute in-memory privacy-preserving fuzzy matching and exact APAAR duplicate detection across institutions.

**Request:**

```json
{
  "records": [
    {
      "student_id": "stud-1",
      "institution_id": "inst-1",
      "student_name": "Aarav Sharma",
      "dob": "2004-05-15",
      "father_name": "Vijay Sharma",
      "mother_name": "Sunita Sharma",
      "apaar_id": "999900001111"
    },
    {
      "student_id": "stud-2",
      "institution_id": "inst-2",
      "student_name": "Aarav Sharma",
      "dob": "2004-05-15",
      "father_name": "Vijay Sharma",
      "mother_name": "Sunita Sharma",
      "apaar_id": "999900001111"
    }
  ],
  "threshold": 0.85
}
```

**Response (`200 OK`):**

```json
[
  {
    "case_id": "8488e0f6-...",
    "institution_a": "inst-1",
    "institution_b": "inst-2",
    "student_a_id": "stud-1",
    "student_b_id": "stud-2",
    "similarity_score": 1.0,
    "confidence": 1.0,
    "matched_fields": ["apaar_id"],
    "status": "open",
    "created_at": "2026-10-23T11:45:00Z"
  }
]
```

## Running Tests

```sh
# Engine test suite
cd engine
uv run pytest

# Lint check
uv run ruff check .
```

Owner: Dev A.
