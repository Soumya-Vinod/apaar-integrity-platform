# Owner: Dev A
"""True Black-Box Evaluation Pipeline for Feature F24.

Evaluates the actual production engine components (signals, review cases, duplicate linkage,
and Blind Match service) against ground truth without reimplementing any detection logic.
"""

from __future__ import annotations

import csv
import json
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz

from engine.blind_match.models import StudentRecord
from engine.blind_match.service import BlindMatchService, find_exact_apaar_duplicates
from engine.config import MATCH_THRESHOLD, SHARED_CONTACT_THRESHOLD
from engine.signals.rules import backdating, cap_filling, shared_contact_clusters

# Target anomaly types to evaluate
EVALUATED_ANOMALIES = (
    "shared_contact_cluster",
    "backdated_entry",
    "typo_duplicate",
    "dup_cross_institution",
    "intake_overrun",
)

# Rule mapping table: Engine / Rule Code -> Ground Truth Anomaly Type
RULE_MAPPING = {
    "SHARED_CONTACT_CLUSTER": "shared_contact_cluster",
    "BACKDATED_ENTRY": "backdated_entry",
    "BACKDATED_ADMISSIONS": "backdated_entry",
    "DUP_CROSS_INSTITUTION": "dup_cross_institution",
    "BLIND_MATCH": "typo_duplicate",
    "FUZZY_MATCH_CANDIDATE": "typo_duplicate",
    "EXCEEDED_INTAKE": "intake_overrun",
    "INTAKE_OVERRUN": "intake_overrun",
}


@dataclass
class AnomalyMetric:
    tp: int
    fp: int
    fn: int
    precision: float
    recall: float
    f1: float
    support: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "tp": self.tp,
            "fp": self.fp,
            "fn": self.fn,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
            "support": self.support,
        }


def compute_metrics(tp: int, fp: int, fn: int, support: int) -> AnomalyMetric:
    p = (tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    r = (tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    f1 = (2 * p * r / (p + r)) if (p + r) > 0 else 0.0
    return AnomalyMetric(tp=tp, fp=fp, fn=fn, precision=p, recall=r, f1=f1, support=support)


class F24EvaluationPipeline:
    """True black-box evaluation runner invoking production engine components."""

    def __init__(
        self,
        dataset_dir: str | Path,
        secret: str = "demo-blind-match-secret-key-32b",
        threshold: float = MATCH_THRESHOLD,
    ) -> None:
        self.dataset_dir = Path(dataset_dir)
        self.secret = os.getenv("BLIND_MATCH_SECRET", secret)
        self.threshold = threshold

        self.admissions_path = self.dataset_dir / "admissions.csv"
        self.intake_path = self.dataset_dir / "intake.csv"
        self.institutions_path = self.dataset_dir / "institutions.csv"
        self.ground_truth_path = self.dataset_dir / "ground_truth.csv"

        self._validate_paths()

    def _validate_paths(self) -> None:
        for path in (
            self.admissions_path,
            self.intake_path,
            self.institutions_path,
            self.ground_truth_path,
        ):
            if not path.is_file():
                raise FileNotFoundError(f"Required dataset file missing: {path}")

    def load_inputs(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Load admissions and intake data without accessing ground truth."""
        with self.admissions_path.open(encoding="utf-8", newline="") as fh:
            admissions = list(csv.DictReader(fh))
        for idx, r in enumerate(admissions, start=1):
            r["row_number"] = idx
            r["record_id"] = f"R{idx:07d}"
            r["student_id"] = f"R{idx:07d}"
            r["institution_id"] = r.get("institution_aicte_code")

        with self.intake_path.open(encoding="utf-8", newline="") as fh:
            intake = list(csv.DictReader(fh))
        for p in intake:
            p["institution_id"] = p.get("institution_aicte_code")

        return admissions, intake

    def run_production_engine(
        self, admissions: list[dict[str, Any]], intake: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Execute production engine components directly.

        No ground-truth information is available or accessed during this step.
        """
        # Ensure default upload_date for backdating rules if not present in CSV
        for r in admissions:
            if not r.get("upload_date"):
                r["upload_date"] = "2026-10-15"

        # 1. Production Intake Overrun (cap_filling rule from engine.signals.rules)
        overrun_signals = cap_filling(admissions, intake)
        pred_overrun_pools: set[str] = set()
        for sig in overrun_signals:
            for v in sig.evidence.get("violations", []):
                if v.get("violated_rule") in ("EXCEEDED_INTAKE", "INTAKE_OVERRUN"):
                    pool_key = v.get("pool_key") or v.get("student_id")
                    if pool_key:
                        pred_overrun_pools.add(str(pool_key))

        # 2. Production Backdated Entry (backdating rule from engine.signals.rules)
        backdate_signals = backdating(admissions)
        pred_backdated_records: set[str] = set()
        for sig in backdate_signals:
            for num in sig.evidence.get("row_numbers", []):
                pred_backdated_records.add(f"R{num:07d}")

        # 3. Production Shared Contact Clusters (shared_contact_clusters from engine.signals.rules)
        cluster_signals = shared_contact_clusters(admissions, min_size=SHARED_CONTACT_THRESHOLD)
        pred_cluster_records: set[str] = set()
        for sig in cluster_signals:
            for st in sig.evidence.get("students", []):
                pred_cluster_records.add(str(st))

        # Convert admissions into canonical StudentRecord objects for BlindMatchService
        students = [
            StudentRecord(
                student_id=r["record_id"],
                institution_id=r["institution_aicte_code"],
                student_name=r["student_name"],
                dob=r["dob"],
                father_name=r.get("guardian_name", ""),
                apaar_id=r.get("apaar_id") or None,
            )
            for r in admissions
        ]

        # 4. Production Exact Duplicate APAAR (from engine.blind_match.service)
        exact_apaar_matches = find_exact_apaar_duplicates(students)
        pred_dup_apaar_pairs: set[tuple[str, str]] = {
            tuple(sorted([c.student_a_id, c.student_b_id])) for c in exact_apaar_matches
        }

        # 5. Production BlindMatchService Linkage (using production BirthYearBlocking)
        bm_service = BlindMatchService(secret=self.secret, threshold=self.threshold)
        bm_matches = bm_service.run_blind_match(students)
        pred_bm_typo_pairs: set[tuple[str, str]] = set()
        for c in bm_matches:
            # Fuzzy match candidates have similarity < 1.0 or non-APAAR match
            if c.matched_fields != ["apaar_id"]:
                pred_bm_typo_pairs.add(tuple(sorted([c.student_a_id, c.student_b_id])))

        # 6. Plain-Text Fuzzy Baseline (RapidFuzz ratio on normalized student name)
        plain_matches = self._run_plaintext_fuzzy_baseline(admissions)
        pred_plain_typo_pairs: set[tuple[str, str]] = {
            tuple(sorted([m[0], m[1]])) for m in plain_matches
        }

        return {
            "pred_overrun_pools": pred_overrun_pools,
            "pred_backdated_records": pred_backdated_records,
            "pred_cluster_records": pred_cluster_records,
            "pred_dup_apaar_pairs": pred_dup_apaar_pairs,
            "pred_bm_typo_pairs": pred_bm_typo_pairs,
            "pred_plain_typo_pairs": pred_plain_typo_pairs,
        }

    def load_ground_truth(
        self, admissions: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Load and resolve ground truth after predictions are sealed."""
        with self.ground_truth_path.open(encoding="utf-8", newline="") as fh:
            ground_truth = list(csv.DictReader(fh))

        adm_by_id = {r["record_id"]: r for r in admissions}

        gt_overruns: set[str] = set()
        gt_backdated: set[str] = set()
        gt_clusters: set[str] = set()
        gt_dup_pairs: set[tuple[str, str]] = set()
        gt_typo_pairs: set[tuple[str, str]] = set()

        for row in ground_truth:
            anom = row["anomaly_type"].strip()
            rec_id = row["record_id"].strip()
            details = row.get("details", "")

            if anom == "intake_overrun":
                gt_overruns.add(rec_id)
            elif anom == "backdated_entry":
                gt_backdated.add(rec_id)
            elif anom == "shared_contact_cluster":
                gt_clusters.add(rec_id)
            elif anom == "dup_cross_institution":
                # Find matching original record by exact apaar_id at different institution
                copy_row = adm_by_id.get(rec_id)
                if copy_row:
                    apaar = (copy_row.get("apaar_id") or "").strip()
                    for other_id, other_row in adm_by_id.items():
                        if (
                            other_id != rec_id
                            and (other_row.get("apaar_id") or "").strip() == apaar
                        ):
                            gt_dup_pairs.add(tuple(sorted([rec_id, other_id])))
                            break
            elif anom == "typo_duplicate":
                # Find matching original record by source name and institution
                m = re.search(r"vs '([^']+)' at ([\w-]+)", details)
                if m:
                    src_name, src_inst = m.group(1), m.group(2)
                    copy_row = adm_by_id.get(rec_id)
                    for other_id, other_row in adm_by_id.items():
                        if (
                            other_id != rec_id
                            and other_row.get("student_name") == src_name
                            and other_row.get("institution_aicte_code") == src_inst
                        ):
                            gt_typo_pairs.add(tuple(sorted([rec_id, other_id])))
                            break

        return {
            "gt_overruns": gt_overruns,
            "gt_backdated": gt_backdated,
            "gt_clusters": gt_clusters,
            "gt_dup_pairs": gt_dup_pairs,
            "gt_typo_pairs": gt_typo_pairs,
        }

    def evaluate(self) -> dict[str, Any]:
        """Execute true black-box evaluation with strict ground truth isolation."""
        # 1. Load inputs only
        admissions, intake = self.load_inputs()

        # 2. Run production engine components to collect predictions
        preds = self.run_production_engine(admissions, intake)

        # 3. Load ground truth strictly AFTER predictions are finalized
        gt = self.load_ground_truth(admissions)

        # 4. Score each signal using appropriate entity-resolution & signal-level granularity
        # Intake Overrun (Pool-level evaluation)
        p_overrun = preds["pred_overrun_pools"]
        g_overrun = gt["gt_overruns"]
        tp_overrun = len(p_overrun & g_overrun)
        fp_overrun = len(p_overrun - g_overrun)
        fn_overrun = len(g_overrun - p_overrun)
        m_overrun = compute_metrics(tp_overrun, fp_overrun, fn_overrun, len(g_overrun))

        # Backdated Entry (Record-level evaluation)
        p_backdate = preds["pred_backdated_records"]
        g_backdate = gt["gt_backdated"]
        tp_backdate = len(p_backdate & g_backdate)
        fp_backdate = len(p_backdate - g_backdate)
        fn_backdate = len(g_backdate - p_backdate)
        m_backdate = compute_metrics(tp_backdate, fp_backdate, fn_backdate, len(g_backdate))

        # Shared Contact Cluster (Record-level evaluation)
        p_cluster = preds["pred_cluster_records"]
        g_cluster = gt["gt_clusters"]
        tp_cluster = len(p_cluster & g_cluster)
        fp_cluster = len(p_cluster - g_cluster)
        fn_cluster = len(g_cluster - p_cluster)
        m_cluster = compute_metrics(tp_cluster, fp_cluster, fn_cluster, len(g_cluster))

        # Exact Duplicate APAAR (Pair-level Entity Resolution evaluation)
        p_dup = preds["pred_dup_apaar_pairs"]
        g_dup = gt["gt_dup_pairs"]
        tp_dup = len(p_dup & g_dup)
        fp_dup = len(p_dup - g_dup)
        fn_dup = len(g_dup - p_dup)
        m_dup = compute_metrics(tp_dup, fp_dup, fn_dup, len(g_dup))

        # Blind Match Typo Duplicates (Pair-level Entity Resolution evaluation)
        p_bm = preds["pred_bm_typo_pairs"]
        g_typo = gt["gt_typo_pairs"]
        tp_bm = len(p_bm & g_typo)
        fp_bm = len(p_bm - g_typo)
        fn_bm = len(g_typo - p_bm)
        m_bm = compute_metrics(tp_bm, fp_bm, fn_bm, len(g_typo))

        # Plain-Text Fuzzy Typo Duplicates (Pair-level Entity Resolution evaluation)
        p_plain = preds["pred_plain_typo_pairs"]
        tp_plain = len(p_plain & g_typo)
        fp_plain = len(p_plain - g_typo)
        fn_plain = len(g_typo - p_plain)
        m_plain = compute_metrics(tp_plain, fp_plain, fn_plain, len(g_typo))

        # Compile report dictionaries
        bm_results = {
            "shared_contact_cluster": m_cluster.to_dict(),
            "backdated_entry": m_backdate.to_dict(),
            "typo_duplicate": m_bm.to_dict(),
            "dup_cross_institution": m_dup.to_dict(),
            "intake_overrun": m_overrun.to_dict(),
        }

        plain_results = {
            "shared_contact_cluster": m_cluster.to_dict(),
            "backdated_entry": m_backdate.to_dict(),
            "typo_duplicate": m_plain.to_dict(),
            "dup_cross_institution": m_dup.to_dict(),
            "intake_overrun": m_overrun.to_dict(),
        }

        def calc_overall(results: dict[str, dict[str, Any]]) -> dict[str, float]:
            tot_tp = sum(v["tp"] for v in results.values())
            tot_fp = sum(v["fp"] for v in results.values())
            tot_fn = sum(v["fn"] for v in results.values())

            micro_p = (tot_tp / (tot_tp + tot_fp)) if (tot_tp + tot_fp) > 0 else 0.0
            micro_r = (tot_tp / (tot_tp + tot_fn)) if (tot_tp + tot_fn) > 0 else 0.0
            micro_f1 = (
                (2 * micro_p * micro_r / (micro_p + micro_r))
                if (micro_p + micro_r) > 0
                else 0.0
            )

            macro_p = sum(v["precision"] for v in results.values()) / len(results)
            macro_r = sum(v["recall"] for v in results.values()) / len(results)
            macro_f1 = sum(v["f1"] for v in results.values()) / len(results)

            return {
                "micro_precision": round(micro_p, 4),
                "micro_recall": round(micro_r, 4),
                "micro_f1": round(micro_f1, 4),
                "macro_precision": round(macro_p, 4),
                "macro_recall": round(macro_r, 4),
                "macro_f1": round(macro_f1, 4),
            }

        return {
            "blind_match": bm_results,
            "plaintext_fuzzy": plain_results,
            "overall": {
                "blind_match": calc_overall(bm_results),
                "plaintext_fuzzy": calc_overall(plain_results),
            },
        }

    def _run_plaintext_fuzzy_baseline(
        self, admissions: list[dict[str, Any]]
    ) -> list[tuple[str, str, float]]:
        """Plain-text fuzzy matcher baseline: RapidFuzz ratio within identical DOB blocks."""
        by_dob: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in admissions:
            by_dob[r["dob"]].append(r)

        matches: list[tuple[str, str, float]] = []
        for _dob, block in by_dob.items():
            if len(block) < 2:
                continue

            n = len(block)
            for i in range(n):
                for j in range(i + 1, n):
                    r1 = block[i]
                    r2 = block[j]
                    if r1["institution_aicte_code"] == r2["institution_aicte_code"]:
                        continue
                    a1 = (r1.get("apaar_id") or "").strip()
                    a2 = (r2.get("apaar_id") or "").strip()
                    if a1 and a2 and a1 == a2:
                        continue

                    name1 = r1["student_name"].strip().lower()
                    name2 = r2["student_name"].strip().lower()
                    sim = fuzz.ratio(name1, name2) / 100.0

                    if sim >= self.threshold:
                        matches.append((r1["record_id"], r2["record_id"], round(sim, 4)))

        return matches


def run_evaluation_pipeline(
    dataset_dir: str | Path = "datagen/out",
    output_json: str | Path = "evaluation/results.json",
) -> dict[str, Any]:
    """Run pipeline and write results.json."""
    pipeline = F24EvaluationPipeline(dataset_dir=dataset_dir)
    results = pipeline.evaluate()

    out_path = Path(output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)

    return results


if __name__ == "__main__":
    import sys

    d_dir = sys.argv[1] if len(sys.argv) > 1 else "datagen/out"
    out_file = sys.argv[2] if len(sys.argv) > 2 else "evaluation/results.json"
    res = run_evaluation_pipeline(dataset_dir=d_dir, output_json=out_file)
    print("Evaluation completed successfully.")
    print(json.dumps(res, indent=2))
