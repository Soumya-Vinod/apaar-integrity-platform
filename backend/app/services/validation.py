# Owner: Dev B
"""Row-level validation rules for uploaded admissions (shared/rule-codes.md).

Pure logic: database-backed checks arrive through ValidationContext callbacks, so every
rule can be unit-tested without Postgres. Evidence never contains raw contacts, and APAAR
IDs in evidence are masked.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from app.core.rule_codes import RULE_SEVERITY, RuleCode
from app.services.ingestion import REQUIRED_COLUMNS, NormalizedRow

log = logging.getLogger(__name__)

_APAAR_RE = re.compile(r"\d{12}")
SEAT_POOLS = ("regular", "tfw", "fn_oci_pio", "nri")
ADMISSION_MODES = ("cap", "management", "lateral", "spot")
GENDERS = ("male", "female", "transgender")
CATEGORIES = ("general", "ews", "obc", "sc", "st")
INDIA = {"IN", "IND", "INDIA", "INDIAN"}
_ACADEMIC_YEAR_RE = re.compile(r"\d{4}-\d{2}")
MIN_AGE, MAX_AGE = 15, 60


def validate_apaar(value: str | None, opted_out: bool) -> RuleCode | None:
    """Check an APAAR ID. Format only: no checksum is applied because none is published.

    12 digits passes (None). Blank with ``opted_out`` is APAAR_OPTED_OUT (info, not an
    error). Blank without opt-out is APAAR_MISSING. Anything else is APAAR_FORMAT.
    """
    cleaned = (value or "").strip()
    if not cleaned:
        return RuleCode.APAAR_OPTED_OUT if opted_out else RuleCode.APAAR_MISSING
    if _APAAR_RE.fullmatch(cleaned):
        return None
    return RuleCode.APAAR_FORMAT


def mask_apaar(value: str | None) -> str | None:
    """Mask an APAAR ID as XXXX-XXXX-1234."""
    if not value:
        return None
    return f"XXXX-XXXX-{value[-4:]}"


@dataclass
class Finding:
    row_number: int
    rule_code: RuleCode
    message: str
    evidence: dict[str, Any] = field(default_factory=dict)

    @property
    def severity(self) -> str:
        return RULE_SEVERITY[self.rule_code].value


@dataclass
class ValidationContext:
    cutoff: date
    shared_contact_threshold: int = 5
    institution_code: str | None = None
    # Programme codes approved for the institution; None skips PROGRAMME_UNKNOWN.
    programme_codes: set[str] | None = None
    # apaar_ids -> {apaar_id: other institution code} for active admissions elsewhere.
    # None skips DUP_CROSS_INSTITUTION (pure tests).
    cross_institution_lookup: Callable[[list[str]], dict[str, str]] | None = None
    run_engine_hooks: bool = True


def _age_on(dob: date, on: date) -> int:
    return on.year - dob.year - ((on.month, on.day) < (dob.month, dob.day))


def check_row(row: NormalizedRow, ctx: ValidationContext) -> list[Finding]:
    """All single-row rules."""
    v, n = row.values, row.row_number
    out: list[Finding] = []

    def add(code: RuleCode, message: str, **evidence: Any) -> None:
        out.append(Finding(n, code, message, evidence))

    for column in REQUIRED_COLUMNS:
        if column in row.invalid:
            continue
        if v.get(column) is None or v.get(column) == "":
            add(RuleCode.REQUIRED_FIELD_MISSING, f"{column} is blank.", field=column)
    enum_checks = {
        "gender": GENDERS,
        "category": CATEGORIES,
        "admission_mode": ADMISSION_MODES,
    }
    for column, allowed in enum_checks.items():
        if v.get(column) and v[column] not in allowed:
            add(
                RuleCode.REQUIRED_FIELD_MISSING,
                f"{column} must be one of {', '.join(allowed)}.",
                field=column,
                reason="invalid_value",
            )
    for column in ("pwd", "apaar_opt_out", "oci_status", "fn_status", "nri_category"):
        if column in row.invalid:
            add(
                RuleCode.REQUIRED_FIELD_MISSING,
                f"{column} must be true or false.",
                field=column,
                reason="invalid_value",
            )
    if "qualifying_exam_pct" in row.invalid:
        add(
            RuleCode.REQUIRED_FIELD_MISSING,
            "qualifying_exam_pct must be a number from 0 to 100.",
            field="qualifying_exam_pct",
            reason="invalid_value",
        )
    year = v.get("academic_year")
    if year and not _ACADEMIC_YEAR_RE.fullmatch(year):
        add(
            RuleCode.REQUIRED_FIELD_MISSING,
            "academic_year must look like 2026-27.",
            field="academic_year",
            reason="invalid_value",
        )

    opted_out = bool(v.get("apaar_opt_out"))
    apaar_code = validate_apaar(v.get("apaar_id"), opted_out)
    if apaar_code is RuleCode.APAAR_MISSING:
        add(apaar_code, "apaar_id is blank and the student has not opted out.")
    elif apaar_code is RuleCode.APAAR_FORMAT:
        add(apaar_code, "apaar_id must be exactly 12 digits.", length=len(v["apaar_id"]))
    elif apaar_code is RuleCode.APAAR_OPTED_OUT:
        add(apaar_code, "Student opted out of APAAR; provisional ID used.")
    if opted_out and not v.get("apaar_id") and not v.get("provisional_id"):
        add(
            RuleCode.REQUIRED_FIELD_MISSING,
            "provisional_id is required when apaar_opt_out is true.",
            field="provisional_id",
        )

    code = v.get("programme_code")
    if ctx.institution_code and v.get("institution_aicte_code") not in (
        None,
        ctx.institution_code,
    ):
        add(
            RuleCode.PROGRAMME_UNKNOWN,
            "Row belongs to a different institution than the uploader.",
            institution_aicte_code=v["institution_aicte_code"],
            reason="institution_mismatch",
        )
    elif code and ctx.programme_codes is not None and code not in ctx.programme_codes:
        add(RuleCode.PROGRAMME_UNKNOWN, f"{code} is not an approved programme.", programme=code)

    pool = v.get("seat_pool")
    if pool and pool not in SEAT_POOLS:
        add(RuleCode.POOL_UNKNOWN, f"seat_pool '{pool}' is not recognised.", seat_pool=pool)

    for column in ("dob", "admission_date"):
        if column in row.invalid:
            add(RuleCode.DATE_INVALID, f"{column} is not a valid date.", field=column)

    admitted = v.get("admission_date")
    if admitted and admitted > ctx.cutoff:
        add(
            RuleCode.ADMISSION_AFTER_CUTOFF,
            "Admission date is after the cutoff.",
            admission_date=admitted.isoformat(),
            cutoff=ctx.cutoff.isoformat(),
        )

    nationality = (v.get("nationality") or "").upper()
    if v.get("fn_status") and (not nationality or nationality in INDIA):
        add(
            RuleCode.FN_WITHOUT_NATIONALITY,
            "Foreign national with Indian or blank nationality.",
            nationality=nationality or None,
        )

    oci, fn = bool(v.get("oci_status")), bool(v.get("fn_status"))
    if oci and nationality in INDIA:
        add(RuleCode.OCI_INCONSISTENT, "OCI/PIO holder listed with Indian nationality.")
    elif oci and fn:
        add(RuleCode.OCI_INCONSISTENT, "Row is marked both OCI/PIO and foreign national.")
    elif pool == "fn_oci_pio" and not (oci or fn):
        add(RuleCode.OCI_INCONSISTENT, "fn_oci_pio seat without OCI/PIO or foreign status.")

    if v.get("nri_category") is not None and pool in SEAT_POOLS:
        if bool(v["nri_category"]) != (pool == "nri"):
            add(
                RuleCode.NRI_POOL_MISMATCH,
                "nri_category and seat_pool=nri disagree.",
                nri_category=bool(v["nri_category"]),
                seat_pool=pool,
            )

    dob = v.get("dob")
    if dob and admitted:
        age = _age_on(dob, admitted)
        if age < MIN_AGE or age > MAX_AGE:
            add(RuleCode.AGE_IMPLAUSIBLE, f"Age {age} on admission date.", age=age)
    return out


def check_batch(rows: list[NormalizedRow], ctx: ValidationContext) -> list[Finding]:
    """Rules that compare rows with each other or with the database."""
    out: list[Finding] = []

    seen: dict[str, int] = {}
    for row in rows:
        key = row.values.get("apaar_id") or row.values.get("provisional_id")
        if not key:
            continue
        if key in seen:
            evidence: dict[str, Any] = {"duplicate_of_row": seen[key]}
            if row.values.get("apaar_id"):
                evidence["apaar_id_masked"] = mask_apaar(key)
            out.append(
                Finding(
                    row.row_number,
                    RuleCode.DUP_IN_BATCH,
                    f"Same ID as row {seen[key]} of this batch.",
                    evidence,
                )
            )
        else:
            seen[key] = row.row_number

    if ctx.cross_institution_lookup is not None:
        valid = {
            r.values["apaar_id"]: r
            for r in rows
            if r.values.get("apaar_id") and _APAAR_RE.fullmatch(r.values["apaar_id"])
        }
        elsewhere = ctx.cross_institution_lookup(sorted(valid)) if valid else {}
        for apaar, other in elsewhere.items():
            out.append(
                Finding(
                    valid[apaar].row_number,
                    RuleCode.DUP_CROSS_INSTITUTION,
                    "APAAR ID has an active admission at another institution.",
                    {"apaar_id_masked": mask_apaar(apaar), "other_institution_code": other},
                )
            )

    clusters: dict[str, list[int]] = defaultdict(list)
    for row in rows:
        for column in ("contact_phone", "contact_email"):
            if row.values.get(column):
                clusters[row.values[column]].append(row.row_number)
    flagged: set[int] = set()
    for members in clusters.values():
        unique = sorted(set(members))
        if len(unique) < ctx.shared_contact_threshold:
            continue
        for number in unique:
            if number not in flagged:
                flagged.add(number)
                out.append(
                    Finding(
                        number,
                        RuleCode.SHARED_CONTACT_CLUSTER,
                        f"Contact shared by {len(unique)} rows in this batch.",
                        {"cluster_size": len(unique)},
                    )
                )
    return out


# ---------------------------------------------------------------------------- Dev A hooks
def _engine_rows(rows: list[NormalizedRow]) -> list[dict[str, Any]]:
    return [{"row_number": r.row_number, **r.to_json()["values"]} for r in rows]


def _signal_findings(signals: list, code: RuleCode) -> list[Finding]:
    """Engine signals point at rows through evidence['row_numbers']."""
    out = []
    for signal in signals:
        evidence = dict(getattr(signal, "evidence", {}) or {})
        numbers = evidence.pop("row_numbers", [])
        for number in numbers:
            out.append(Finding(int(number), code, f"Engine signal {signal.code}.", evidence))
    return out


def engine_findings(rows: list[NormalizedRow], blind_match_secret: str = "") -> list[Finding]:
    """FUZZY_MATCH_CANDIDATE, BACKDATED_ENTRY and QUALIFYING_BELOW_NORM come from Dev A's
    engine. Each hook is skipped silently while the engine raises NotImplementedError."""
    out: list[Finding] = []
    engine_rows = _engine_rows(rows)
    try:
        from engine.signals.rules import backdating

        out += _signal_findings(backdating(engine_rows), RuleCode.BACKDATED_ENTRY)
    except NotImplementedError:
        pass
    try:
        from engine.signals.rules import eligibility

        out += _signal_findings(eligibility(engine_rows), RuleCode.QUALIFYING_BELOW_NORM)
    except NotImplementedError:
        pass
    try:
        out += _fuzzy_findings(rows, blind_match_secret)
    except NotImplementedError:
        pass
    return out


def _fuzzy_findings(rows: list[NormalizedRow], secret: str) -> list[Finding]:
    import hashlib

    from engine.blind_match.encoder import encode_identity
    from engine.blind_match.linkage import find_candidates
    from engine.types import EncodedRecord

    records = []
    for row in rows:
        v = row.values
        if not v.get("student_name") or not v.get("dob"):
            continue
        fields = {
            "student_name": v["student_name"],
            "dob": v["dob"].isoformat(),
            "guardian_name": v.get("guardian_name") or "",
        }
        records.append(
            EncodedRecord(
                record_id=str(row.row_number),
                institution_id="batch",
                bloom=encode_identity(fields, secret.encode()),
                birth_year_hash=hashlib.sha256(str(v["dob"].year).encode()).hexdigest(),
                apaar_id=v.get("apaar_id"),
            )
        )
    out = []
    for candidate in find_candidates(records, threshold=0.85):
        later = max(int(candidate.record_a), int(candidate.record_b))
        earlier = min(int(candidate.record_a), int(candidate.record_b))
        out.append(
            Finding(
                later,
                RuleCode.FUZZY_MATCH_CANDIDATE,
                "Blind Match found a likely duplicate identity in this batch.",
                {"other_row": earlier, "dice": round(candidate.dice, 3)},
            )
        )
    return out


def validate_rows(
    rows: list[NormalizedRow], ctx: ValidationContext, blind_match_secret: str = ""
) -> list[Finding]:
    findings = [f for row in rows for f in check_row(row, ctx)]
    findings += check_batch(rows, ctx)
    if ctx.run_engine_hooks:
        findings += engine_findings(rows, blind_match_secret)
    return sorted(findings, key=lambda f: (f.row_number, f.rule_code.value))


def error_rows(findings: list[Finding]) -> set[int]:
    """Rows excluded from commit: any finding with severity error."""
    return {f.row_number for f in findings if f.severity == "error"}


def count_findings(total_rows: int, findings: list[Finding]) -> dict[str, int]:
    """Batch counts: rows with at least one finding of each severity."""
    by_severity: dict[str, set[int]] = defaultdict(set)
    for f in findings:
        by_severity[f.severity].add(f.row_number)
    return {
        "rows_total": total_rows,
        "errors": len(by_severity["error"]),
        "warnings": len(by_severity["warning"]),
        "review": len(by_severity["review"]),
        "info": len(by_severity["info"]),
    }
