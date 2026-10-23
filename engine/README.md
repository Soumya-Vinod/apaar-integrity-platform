<!-- Owner: Dev A -->
# engine

Integrity engine for the APAAR Integrity Platform. The backend imports it as `engine` (editable dependency).

| Module | Purpose | Status |
| --- | --- | --- |
| `engine.types` | Shared dataclasses | done |
| `engine.config` | Engine configuration defaults | done |
| `engine.routers` | FastAPI router endpoints (/engine, /engine/health) | done |
| `engine.blind_match.encoder` | Bloom-filter identity encoding; Dice coefficient | `dice` done, `encode_identity` stub |
| `engine.blind_match.linkage` | Candidate pairs blocked on hashed birth year | stub |
| `engine.signals.rules` | Rule-based signals | stub |
| `engine.anomaly.isolation` | Isolation Forest ranking of institutions | stub |
| `engine.scoring.integrity` | Integrity Score 0-100 | stub |
| `engine.eval.harness` / `engine.evaluation` | Precision, recall and F1 per signal against datagen ground truth | stub |

```sh
uv run pytest
uv run ruff check .
```

Owner: Dev A.
