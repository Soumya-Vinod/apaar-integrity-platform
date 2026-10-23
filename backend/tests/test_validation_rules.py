# Owner: Dev B
from datetime import date

import pytest

from app.core.rule_codes import RuleCode
from app.services.ingestion import TEMPLATE_COLUMNS, normalize_row
from app.services.validation import (
    ValidationContext,
    count_findings,
    error_rows,
    validate_rows,
)

SECRET = "test-pseudonym-secret"
BASE = {
    "institution_aicte_code": "1-9999003",
    "programme_code": "UG-CSE",
    "academic_year": "2026-27",
    "student_name": "aarav sharma",
    "dob": "2008-03-14",
    "gender": "male",
    "category": "general",
    "pwd": "false",
    "apaar_id": "999912340001",
    "apaar_opt_out": "false",
    "provisional_id": "",
    "nationality": "IN",
    "oci_status": "false",
    "fn_status": "false",
    "nri_category": "false",
    "seat_pool": "regular",
    "admission_mode": "cap",
    "admission_date": "2026-08-05",
    "qualifying_exam": "JEE Main",
    "qualifying_exam_pct": "92.4",
    "domicile_state": "Uttar Pradesh",
    "contact_phone": "+919800000001",
    "contact_email": "aarav@example.com",
    "guardian_name": "rakesh sharma",
}
IDENTITY = {c: c for c in TEMPLATE_COLUMNS}


def row(n: int = 1, **overrides: str):
    raw = {**BASE, **overrides}
    return normalize_row(raw, IDENTITY, n, SECRET)


def ctx(**kwargs) -> ValidationContext:
    defaults = {
        "cutoff": date(2026, 9, 30),
        "shared_contact_threshold": 5,
        "institution_code": "1-9999003",
        "programme_codes": {"UG-CSE", "UG-CE"},
        "run_engine_hooks": False,
    }
    return ValidationContext(**{**defaults, **kwargs})


def codes(rows, context=None) -> set[RuleCode]:
    return {f.rule_code for f in validate_rows(rows, context or ctx())}


def test_clean_row_has_no_findings():
    assert codes([row()]) == set()


# ---------------------------------------------------------------- one test per rule
@pytest.mark.parametrize("column", ["student_name", "dob", "seat_pool", "qualifying_exam"])
def test_required_field_missing(column):
    findings = validate_rows([row(**{column: ""})], ctx())
    assert any(
        f.rule_code is RuleCode.REQUIRED_FIELD_MISSING and f.evidence["field"] == column
        for f in findings
    )


def test_required_field_invalid_enum_and_boolean():
    findings = validate_rows([row(gender="robot", pwd="maybe")], ctx())
    fields = {
        f.evidence["field"] for f in findings if f.rule_code is RuleCode.REQUIRED_FIELD_MISSING
    }
    assert fields == {"gender", "pwd"}


def test_apaar_missing():
    assert RuleCode.APAAR_MISSING in codes([row(apaar_id="")])
    assert RuleCode.APAAR_MISSING not in codes([row()])


def test_apaar_format():
    assert RuleCode.APAAR_FORMAT in codes([row(apaar_id="99991234567")])
    assert RuleCode.APAAR_FORMAT not in codes([row()])


def test_apaar_opted_out_is_info_not_error():
    rows = [row(apaar_id="", apaar_opt_out="yes", provisional_id="prov-1-9999003-0001")]
    findings = validate_rows(rows, ctx())
    assert {f.rule_code for f in findings} == {RuleCode.APAAR_OPTED_OUT}
    assert findings[0].severity == "info"
    assert error_rows(findings) == set()


def test_opted_out_without_provisional_id_is_an_error():
    findings = validate_rows([row(apaar_id="", apaar_opt_out="true")], ctx())
    assert any(f.evidence.get("field") == "provisional_id" for f in findings)


def test_dup_in_batch():
    rows = [row(1), row(2, student_name="Someone Else")]
    findings = validate_rows(rows, ctx())
    dup = [f for f in findings if f.rule_code is RuleCode.DUP_IN_BATCH]
    assert [(f.row_number, f.evidence["duplicate_of_row"]) for f in dup] == [(2, 1)]
    assert dup[0].evidence["apaar_id_masked"] == "XXXX-XXXX-0001"
    assert RuleCode.DUP_IN_BATCH not in codes([row(1), row(2, apaar_id="999912340002")])


def test_dup_cross_institution_uses_lookup():
    seen = []

    def lookup(ids):
        seen.append(ids)
        return {"999912340001": "1-9999002"}

    findings = validate_rows(
        [row(), row(2, apaar_id="999912340002")], ctx(cross_institution_lookup=lookup)
    )
    cross = [f for f in findings if f.rule_code is RuleCode.DUP_CROSS_INSTITUTION]
    assert [(f.row_number, f.evidence["other_institution_code"]) for f in cross] == [
        (1, "1-9999002")
    ]
    assert cross[0].severity == "review"
    assert seen == [["999912340001", "999912340002"]]
    assert RuleCode.DUP_CROSS_INSTITUTION not in codes(
        [row()], ctx(cross_institution_lookup=lambda ids: {})
    )


def test_dup_cross_institution_skipped_without_lookup():
    assert RuleCode.DUP_CROSS_INSTITUTION not in codes([row()], ctx())


def test_programme_unknown():
    assert RuleCode.PROGRAMME_UNKNOWN in codes([row(programme_code="UG-XYZ")])
    assert RuleCode.PROGRAMME_UNKNOWN not in codes([row(programme_code="ug-ce")])


def test_programme_unknown_for_other_institution_row():
    findings = validate_rows([row(institution_aicte_code="1-9999001")], ctx())
    assert [f.evidence.get("reason") for f in findings] == ["institution_mismatch"]


def test_pool_unknown():
    assert RuleCode.POOL_UNKNOWN in codes([row(seat_pool="vip")])
    assert RuleCode.POOL_UNKNOWN not in codes([row(seat_pool="TFW")])


def test_date_invalid():
    findings = validate_rows([row(dob="2008-02-30")], ctx())
    assert [f.rule_code for f in findings] == [RuleCode.DATE_INVALID]
    assert RuleCode.DATE_INVALID not in codes([row(dob="14/03/2008")])


def test_admission_after_cutoff():
    assert RuleCode.ADMISSION_AFTER_CUTOFF in codes([row(admission_date="2026-10-01")])
    assert RuleCode.ADMISSION_AFTER_CUTOFF not in codes([row(admission_date="2026-09-30")])


def test_fn_without_nationality():
    assert RuleCode.FN_WITHOUT_NATIONALITY in codes(
        [row(fn_status="true", seat_pool="fn_oci_pio", nationality="India")]
    )
    assert RuleCode.FN_WITHOUT_NATIONALITY not in codes(
        [row(fn_status="true", seat_pool="fn_oci_pio", nationality="NP")]
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"oci_status": "true", "nationality": "IN", "seat_pool": "fn_oci_pio"},
        {"oci_status": "true", "fn_status": "true", "nationality": "US", "seat_pool": "fn_oci_pio"},
        {"seat_pool": "fn_oci_pio"},
    ],
)
def test_oci_inconsistent(overrides):
    assert RuleCode.OCI_INCONSISTENT in codes([row(**overrides)])


def test_oci_consistent():
    assert RuleCode.OCI_INCONSISTENT not in codes(
        [row(oci_status="true", nationality="US", seat_pool="fn_oci_pio")]
    )


def test_nri_pool_mismatch():
    assert RuleCode.NRI_POOL_MISMATCH in codes([row(nri_category="true")])
    assert RuleCode.NRI_POOL_MISMATCH in codes([row(seat_pool="nri")])
    assert RuleCode.NRI_POOL_MISMATCH not in codes([row(nri_category="true", seat_pool="nri")])


@pytest.mark.parametrize("dob", ["2012-01-01", "1960-01-01"])
def test_age_implausible(dob):
    assert RuleCode.AGE_IMPLAUSIBLE in codes([row(dob=dob)])


def test_age_plausible_at_boundaries():
    assert RuleCode.AGE_IMPLAUSIBLE not in codes([row(dob="2011-08-05")])  # exactly 15


def test_shared_contact_cluster():
    shared = [
        row(n, apaar_id=f"9999123400{n:02d}", contact_email="desk@example.com") for n in range(1, 6)
    ]
    findings = validate_rows(shared, ctx())
    cluster = [f for f in findings if f.rule_code is RuleCode.SHARED_CONTACT_CLUSTER]
    assert sorted(f.row_number for f in cluster) == [1, 2, 3, 4, 5]
    assert all(f.evidence == {"cluster_size": 5} for f in cluster)
    assert RuleCode.SHARED_CONTACT_CLUSTER not in codes(shared[:4])


def test_shared_contact_cluster_respects_threshold():
    shared = [row(n, apaar_id=f"9999123400{n:02d}", contact_phone="9800000009") for n in (1, 2)]
    assert RuleCode.SHARED_CONTACT_CLUSTER in codes(shared, ctx(shared_contact_threshold=2))


# ---------------------------------------------------------------- engine hooks and totals
def test_engine_hooks_skip_while_not_implemented():
    assert codes([row()], ctx(run_engine_hooks=True)) == set()


def test_engine_signal_rows_become_findings(monkeypatch):
    import engine.signals.rules as rules
    from engine.types import Signal

    monkeypatch.setattr(
        rules,
        "backdating",
        lambda rows: [Signal("BACKDATED_ENTRY", "x", "review", {"row_numbers": [1]})],
    )
    findings = validate_rows([row()], ctx(run_engine_hooks=True))
    assert [(f.row_number, f.rule_code) for f in findings] == [(1, RuleCode.BACKDATED_ENTRY)]


def test_error_rows_and_counts():
    rows = [
        row(1),
        row(2, apaar_id="123", contact_email="b@example.com"),
        row(3, apaar_id="", apaar_opt_out="true", provisional_id="P-1"),
    ]
    findings = validate_rows(rows, ctx())
    assert error_rows(findings) == {2}
    assert count_findings(3, findings) == {
        "rows_total": 3,
        "errors": 1,
        "warnings": 0,
        "review": 0,
        "info": 1,
    }


def test_evidence_never_holds_raw_contacts_or_full_apaar():
    rows = [row(n, contact_phone="+91 98000 00001") for n in range(1, 7)]
    text = repr([(f.message, f.evidence) for f in validate_rows(rows, ctx())])
    assert "9800000001" not in text
    assert "999912340001" not in text
