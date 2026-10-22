<!-- Owner: Dev B -->
# backend

FastAPI service for the APAAR Integrity Platform.

```sh
uv sync
uv run uvicorn app.main:app --reload --port 8000   # http://localhost:8000/docs
uv run pytest
uv run ruff check .
uv run python -m scripts.export_contracts           # writes ../shared/openapi.json and ../shared/schemas/
```

## Mock mode

`MOCK_MODE=true` is the default. Every endpoint returns fixtures from `app/mocks/`, and every response carries `X-Mock: true`. The current user comes from headers:

- `X-Demo-Role`: `institution_admin`, `institution_operator`, `aicte_admin` (default), `student`, `verifier`, `auditor`
- `X-Demo-Institution`: institution id (optional)

With `MOCK_MODE=false`, the backend verifies a Supabase HS256 access token, reading `app_metadata.role` and `app_metadata.institution_id` from its claims. Endpoints return `501` until they are implemented.

## Layout

| Path | Purpose | Owner |
| --- | --- | --- |
| `app/main.py` | App, CORS, `X-Mock` middleware, routers | Dev B |
| `app/core/` | Settings, auth, audit hash chain, rule codes | Dev B |
| `app/models/` | Pydantic v2 models, one file per domain (the contract) | Dev B |
| `app/routers/integrity.py`, `blind_match.py` | Integrity and Blind Match endpoints | Dev A |
| `app/routers/reports.py`, `certificates.py` | Reports and certificates | Dev C |
| `app/routers/credentials.py`, `students.py`, `webhooks.py` | Student side | Dev E |
| other `app/routers/` | Everything else | Dev B |
| `app/services/` | Business logic; placeholders except `validation.py`, `batches.suggest_mapping` and `reports` rendering | Dev B |
| `app/mocks/` | Fixtures. Ids follow `<prefix>-0000-4000-8000-<n>`: `1…` institutions, `2…` programmes, `3…` batches, `4…` students, `5…` admissions, `6…` review cases | Dev B |

Demo identities: "Shadow Institute of Technology" is `10000000-0000-4000-8000-000000000003`; the demo student is `40000000-0000-4000-8000-000000000001`. The mock credential is signed with a demo Ed25519 key derived from a public string, so it is for mock mode only.

After changing a model or endpoint, run the contract export and then `npm run gen:api` in `frontend/`.
