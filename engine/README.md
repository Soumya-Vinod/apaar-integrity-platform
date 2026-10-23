<!-- Owner: Dev A -->
# engine

Integrity engine for the APAAR Integrity Platform. The backend imports it as `engine` (editable dependency).

| Module | Purpose | Status |
| --- | --- | --- |
| `engine.types` | Shared dataclasses (`MatchCase`, `Signal`, `IntegrityScore`, etc.) | done |
| `engine.config` | Engine configuration defaults | done |
| `engine.routers` | FastAPI router endpoints (`/engine`, `/engine/health`, `/engine/blind-match`, `/engine/signals`) | done |
| `engine.blind_match.encoder` | Text normalization, character bigrams, birth year salting, HMAC Bloom-filter encoding | done |
| `engine.blind_match.similarity` | Dice and Jaccard similarity metrics over bit arrays | done |
| `engine.blind_match.models` | `BloomFilter`, `StudentRecord`, `LinkageMatch`, and `ReviewCaseRepository` interfaces | done |
| `engine.blind_match.linkage` | Candidate pairs blocked on hashed birth year with Dice threshold filtering | done |
| `engine.blind_match.service` | `BlindMatchService` and exact APAAR cross-institution duplicate detection | done |
| `engine.signals.base` | Signal severity mapping and evidence builders | done |
| `engine.signals.eligibility` | Eligibility vs AICTE APH rules violation detection | done |
| `engine.signals.shared_contacts` | Suspicious shared contact clusters across institutions | done |
| `engine.signals.backdated` | Backdated admissions detection with delay thresholds | done |
| `engine.signals.attrition` | Zero attrition repeated cap filling analysis | done |
| `engine.signals.registry` | Extensible `SignalRegistry` and execution engine | done |
| `engine.signals.rules` | Backward-compatible wrappers for rule signals | done |
| `engine.anomaly.isolation` | Isolation Forest ranking of institutions | stub |
| `engine.scoring.integrity` | Integrity Score 0-100 | stub |
| `engine.eval.harness` / `engine.evaluation` | Precision, recall and F1 per signal against datagen ground truth | stub |

---

## Integrity Signals Engine Architecture (Feature F15)

The Integrity Signals Engine provides rule-based intelligence detecting suspicious admission patterns at both the student and institution level.

```
Admission Records / Institution History
                     ↓
             [Signal Registry]
                     ↓
  ┌──────────────────┼──────────────────┬──────────────────┐
  ↓                  ↓                  ↓                  ↓
[Signal 1:         [Signal 2:         [Signal 3:         [Signal 4:
 Eligibility vs     Shared Contact     Backdated          Zero Attrition
 APH Rules]         Clusters]          Admissions]        Cap Filling]
  │                  │                  │                  │
  └──────────────────┴──────────────────┴──────────────────┘
                     ↓
        Configurable Severity & Confidence Scoring
                     ↓
          Structured Evidence Generation
                     ↓
             List of `Signal` Outputs
```

### Core Design Principles

1. **Pure Functions**: Every signal is implemented as a deterministic, stateless pure function with no database queries or HTTP dependencies.
2. **Standard Signal Contract**: Every signal outputs the existing `Signal` model (`signal_id`, `institution_id`, `signal_name`, `severity`, `score`, `evidence`, `description`, `created_at`).
3. **Structured Evidence**: All outputs provide strictly typed, structured evidence dictionaries rather than free-form text.
4. **Independent Extensibility**: New signals are added and registered dynamically via `SignalRegistry` without altering existing signals.

---

### Core Signals

#### 1. Eligibility vs APH Rules (`eligibility.py`)
Flags student admissions violating AICTE Approval Process Handbook (APH) norms:
- **Qualifying Exam %**: Compares student marks against minimum thresholds (45% for general, 40% for reserved categories).
- **Category Validation**: Enforces approved admission categories (`general`, `ews`, `obc`, `sc`, `st`).
- **Quota Validation**: Enforces recognized seat pools (`regular`, `tfw`, `fn_oci_pio`, `nri`).
- **Plausible Age**: Validates student age at admission (default: 16–35 years).
- **Approved Intake Overrun**: Flags programmes where total admissions exceed approved capacity.
- **Programme Eligibility**: Validates programme codes against configured eligible offerings.

#### 2. Shared Contact Clusters (`shared_contacts.py`)
Identifies suspicious sharing of phone numbers, guardian phone numbers, and emails across institutions:
- Groups students sharing identical normalized contact credentials.
- Flags clusters spanning multiple institutions or exceeding cluster size thresholds within single institutions (indicative of unregulated admission brokers).

#### 3. Backdated Admissions (`backdated.py`)
Detects admissions uploaded significantly later than their declared admission date:
- Calculates elapsed days between declared `admission_date` and upload timestamp.
- Flags delays exceeding configurable thresholds (default: 30 days).

#### 4. Zero Attrition Cap Filling (`attrition.py`)
Analyzes multi-year institution statistics to detect synthetic cap filling:
- Evaluates seat utilisation and student dropout/attrition rates over consecutive academic years.
- Flags institutions exhibiting consistently 100% capacity utilization with 0% attrition across 2+ years.

---

### Signal Severity & Scoring

- **Severity Levels**: Mapped to platform standards (`"info"`, `"warning"`, `"review"`, `"error"`).
- **Dynamic Calculation**: `SignalSeverity.calculate(base_importance, affected_count, institution_wide)` scales severity according to rule criticality, number of affected students, and institution impact.
- **Confidence Scoring**: Each signal includes a confidence score between 0.0 and 100.0 based on sample size and deviation magnitude.

---

### Evidence Format

All signals produce structured evidence compliant with the platform contract:

```json
{
  "student_id": "STU_001",
  "institution_id": "INST_01",
  "reason": "1 admission eligibility violation(s) detected under AICTE APH norms.",
  "violated_rule": "QUALIFYING_BELOW_NORM",
  "programme": "BTECH_CSE",
  "expected_value": ">= 45.0%",
  "actual_value": "41.5%",
  "violations_count": 1,
  "violations": [
    {
      "violated_rule": "QUALIFYING_BELOW_NORM",
      "student_id": "STU_001",
      "programme": "BTECH_CSE",
      "expected_value": ">= 45.0%",
      "actual_value": "41.5%",
      "reason": "Qualifying percentage 41.5% is below AICTE minimum 45.0% for category 'general'"
    }
  ],
  "details": {
    "violations_count": 1,
    "violations": [...]
  }
}
```

---

### Signal Registry Design & Adding New Signals

`SignalRegistry` manages signal registration, discovery, and execution:

```python
from engine.signals import SignalRegistry, Signal
from engine.types import Signal

registry = SignalRegistry()

# 1. Register via decorator
@registry.register("my_custom_rule")
def my_custom_rule(admissions: list[dict]) -> list[Signal]:
    signals = []
    # Pure rule logic...
    return signals

# 2. Register via direct call
registry.register("another_rule", another_rule_fn)

# 3. Execute all registered signals against records
signals = registry.execute(records)
```

The global default registry provides pre-registered core signals:
```python
from engine.signals import execute_signals

# Executes all default core signals
signals = execute_signals(institution_data)
```

---

### API Usage

#### POST `/engine/signals`

Executes in-memory integrity signals against institution admissions, seat pools, or historical statistics.

**Request:**

```json
{
  "admissions": [
    {
      "student_id": "stud-1",
      "institution_id": "inst-1",
      "programme_code": "BTECH_CSE",
      "category": "general",
      "qualifying_exam_pct": 38.0,
      "dob": "2005-05-15",
      "admission_date": "2023-01-10",
      "upload_date": "2023-04-15",
      "contact_phone": "9876543210"
    },
    {
      "student_id": "stud-2",
      "institution_id": "inst-2",
      "contact_phone": "9876543210"
    }
  ],
  "historical_stats": [
    {
      "institution_id": "inst-1",
      "academic_year": "2021-22",
      "approved_seats": 100,
      "enrolled_students": 100,
      "attrition_count": 0
    },
    {
      "institution_id": "inst-1",
      "academic_year": "2022-23",
      "approved_seats": 100,
      "enrolled_students": 100,
      "attrition_count": 0
    }
  ]
}
```

**Response (`200 OK`):**

```json
[
  {
    "signal_id": "19bfa6a1-0e11-4f11-9252-875883d659ad",
    "institution_id": "inst-1",
    "signal_name": "ELIGIBILITY_VIOLATION",
    "severity": "review",
    "score": 75.0,
    "evidence": {
      "institution_id": "inst-1",
      "student_id": "stud-1",
      "violated_rule": "QUALIFYING_BELOW_NORM",
      "programme": "BTECH_CSE",
      "expected_value": ">= 45.0%",
      "actual_value": "38.0%",
      "reason": "1 admission eligibility violation(s) detected under AICTE APH norms.",
      "violations_count": 1,
      "violations": [...]
    },
    "description": "Institution has 1 student admission(s) violating AICTE APH eligibility rules.",
    "created_at": "2026-10-23T12:00:00Z"
  },
  {
    "signal_id": "76e31cba-274c-4375-a8ea-c4309307779d",
    "institution_id": "inst-1",
    "signal_name": "SHARED_CONTACT_CLUSTER",
    "severity": "review",
    "score": 89.0,
    "evidence": {
      "cluster_size": 2,
      "affected_institutions": ["inst-1", "inst-2"],
      "repeated_values": ["9876543210"],
      "contact_type": "phone",
      "students": ["stud-1", "stud-2"]
    },
    "description": "Suspicious contact cluster: 2 students across 2 institution(s) share the same phone '9876543210'.",
    "created_at": "2026-10-23T12:00:00Z"
  },
  {
    "signal_id": "9a01e234-884c-4235-802e-503417a80b01",
    "institution_id": "inst-1",
    "signal_name": "BACKDATED_ADMISSIONS",
    "severity": "error",
    "score": 77.5,
    "evidence": {
      "institution_id": "inst-1",
      "student_id": "stud-1",
      "admission_date": "2023-01-10",
      "upload_date": "2023-04-15",
      "delay": 95,
      "backdated_count": 1,
      "threshold_days": 30
    },
    "description": "Institution entered 1 admission(s) with excessive delay (up to 95 days) beyond the 30-day threshold.",
    "created_at": "2026-10-23T12:00:00Z"
  },
  {
    "signal_id": "0133ac24-110f-488b-b152-32a2ef39c8f2",
    "institution_id": "inst-1",
    "signal_name": "ZERO_ATTRITION_CAP_FILLING",
    "severity": "review",
    "score": 85.0,
    "evidence": {
      "institution_id": "inst-1",
      "utilisation": 1.0,
      "attrition": 0.0,
      "years_analysed": ["2021-22", "2022-23"],
      "anomaly_reason": "Institution exhibits 100.0% seat utilisation with 0.0% student attrition across 2 consecutive academic years (2021-22, 2022-23), indicating synthetic cap-filling."
    },
    "description": "Repeated cap filling with zero attrition: 100% utilization across 2 academic years.",
    "created_at": "2026-10-23T12:00:00Z"
  }
]
```

---

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
