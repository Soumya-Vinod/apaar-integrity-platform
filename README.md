# APAAR Integrity Platform

Verifiable, consent-first student records for AICTE-approved institutions.

SIH 2026 · Problem Statement 26263 · AICTE Regulation Bureau

## Summary

AICTE needs an APAAR ID-based student data management and verification platform. After admissions close, institutions upload student-level admission data. The platform validates it (missing or invalid APAAR, duplicates, admissions over approved intake, inconsistent data, duplicate enrolment across institutions). It gives AICTE and institutions real-time dashboards, offers consent-based verification to employers and regulators, generates verifiable student records and certificates that show the APAAR ID next to the student ID, and exposes integration APIs.

Pipeline:

**Institution → Student Data Upload → APAAR Validation → Data Verification → AICTE Central Repository → Analytics & Monitoring → Authorized Verification**

Key features:

- **Seat Ledger**: approved intake split into pools per programme and academic year (`regular`, `tfw`, `fn_oci_pio`, `nri`). Each admission consumes a seat at commit; an overrun raises a review case.
- **Integrity engine**: rule signals, Isolation Forest ranking of institutions, Integrity Score 0–100.
- **Blind Match**: privacy-preserving fuzzy duplicate detection on Bloom-filter encodings of identity fields.
- **Hash-chained audit log** with tamper detection.
- **Student side**: consent ledger, access log, Ed25519-signed credential QR with per-verifier pseudonyms, offline verifier app, Telegram "Is this you?" confirmations.
- **Reports and certificates**: PDF/XLSX reports; certificates with APAAR ID, student ID and a verify QR.
- **Opted-out students** (no APAAR) get a provisional ID and are never treated as errors.

Anything that stands in for a government system (APAAR, ABC, DigiLocker, AICTE portal SSO) is labelled `SIMULATED`.

## Git policy

1. **No git write commands. Ever.** Do not run `git add`, `git add .`, `commit`, `push`, `pull`, `fetch`, `merge`, `rebase`, `reset`, `restore`, `checkout`, `switch`, `stash`, `tag`, `rm`, `mv`, `init`, `clone`, `config`, or anything else that changes git state, history or configuration. Read-only git (`status`, `diff`, `log`, `show`) is fine. Humans stage, commit and push everything themselves. This rule applies to every AI tool used on this repo: Claude Code, Google Antigravity, Gemini, GitHub Copilot, Cursor, Codex and any other.
2. **No AI attribution anywhere.** Never write `Co-Authored-By`, `Claude-Session`, "Generated with Claude Code", or any other AI attribution or trailer, in commit messages, PR descriptions, file headers, code comments or docs. At the end, give Sam the file list grouped into suggested commits, each with a plain one-line commit message and nothing else.

Each teammate runs this once after cloning to enable the commit-message hook that blocks AI attribution lines:

```sh
git config core.hooksPath .githooks
```

## Folder map

| Folder | What it holds | Owner |
| --- | --- | --- |
| `engine/` | Integrity engine: rule signals, Isolation Forest, Integrity Score, Blind Match | Dev A |
| `backend/` | FastAPI service, mock mode, audit chain, contract export | Dev B (integrity and blind-match routers: Dev A; reports and certificates routers: Dev C; credentials, students and webhooks routers: Dev E) |
| `supabase/` | Postgres migrations and seed | Dev B |
| `shared/` | Contracts: CSV templates, rule codes, realtime events, OpenAPI and JSON Schemas | Dev B |
| `datagen/` | Synthetic data generator with planted anomalies | Dev C |
| `reports/` | Report and certificate templates | Dev C |
| `frontend/` | React + Vite + TypeScript + Tailwind v4 app | Dev D (institution, aicte, blindmatch pages, components), Dev E (student, verifier pages) |
| `bot/` | Telegram bot for "Is this you?" confirmations | Dev E |
| `deck/` | Presentation material | Presenter |
| `scripts/` | Dev helper scripts | Dev B |

## Quick start

Requirements: Python 3.12 via [uv](https://docs.astral.sh/uv/), Node 20+ with npm. On Windows, use PowerShell.

Copy the relevant block of `.env.example` into `backend/.env`, `frontend/.env` and `bot/.env`. Everything works in mock mode without Supabase.

```sh
# Backend (http://localhost:8000, docs at /docs)
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000

# Frontend (http://localhost:5173)
cd frontend
npm install
npm run dev

# Engine tests
cd engine
uv run pytest

# Synthetic data (writes datagen/out/)
cd datagen
uv run python generate.py --small

# Telegram bot (needs TELEGRAM_BOT_TOKEN)
cd bot
uv run python main.py
```

To start backend and frontend together on Windows: `./scripts/dev.ps1`.

After any backend model or endpoint change, regenerate contracts and frontend types:

```sh
cd backend && uv run python -m scripts.export_contracts
cd ../frontend && npm run gen:api
```

## Data

All data in this repo is synthetic. No real student, institution or Aadhaar data is ever stored or logged. APAAR IDs in fixtures start with `9999` so they are obviously fake. Phone numbers and emails are hashed before storage.
