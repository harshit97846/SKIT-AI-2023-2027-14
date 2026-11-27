"""fix_database_anomalies.py - Diagnostic and repair utility for MongoDB data anomalies.

Form 2 Sprint 4: "Fix database issue - Will fix problem while testing the database"

Detects, audits, and fixes common issues uncovered during database testing:
  1. Orphan records (clinical records, ECG recordings, predictions referencing non-existent patients)
  2. Malformed or extreme outlier vital signs (blood pressure, cholesterol, heart rate)
  3. Missing timestamps or unparsed date strings
  4. Malformed explainability structures in prediction_results
  5. Missing compound and single-field performance indexes

Usage:
  python backend/fix_database_anomalies.py [--apply] [--verbose]
"""

import argparse
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from pymongo.database import Database

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("fix_database_anomalies")


def audit_and_repair_orphans(db: Database, apply_fix: bool = False) -> dict:
    """Detect and optionally clean or flag orphan records across collections."""
    patient_ids = set()
    for p in db["patients"].find({}, {"patientId": 1, "_id": 1}):
        if "patientId" in p:
            patient_ids.add(str(p["patientId"]))
        if "_id" in p:
            patient_ids.add(str(p["_id"]))

    orphan_summary = {
        "clinical_orphans": 0,
        "ecg_orphans": 0,
        "prediction_orphans": 0,
        "repaired_or_removed": 0,
    }

    # Check clinical_records
    for doc in db["clinical_records"].find({}, {"_id": 1, "patient_id": 1}):
        pid = str(doc.get("patient_id"))
        if pid not in patient_ids:
            orphan_summary["clinical_orphans"] += 1
            if apply_fix:
                db["clinical_records"].delete_one({"_id": doc["_id"]})
                orphan_summary["repaired_or_removed"] += 1

    # Check ecg_recordings
    for doc in db["ecg_recordings"].find({}, {"_id": 1, "patient_id": 1}):
        pid = str(doc.get("patient_id"))
        if pid not in patient_ids:
            orphan_summary["ecg_orphans"] += 1
            if apply_fix:
                db["ecg_recordings"].delete_one({"_id": doc["_id"]})
                orphan_summary["repaired_or_removed"] += 1

    # Check prediction_results
    for doc in db["prediction_results"].find({}, {"_id": 1, "patient_id": 1}):
        pid = str(doc.get("patient_id"))
        if pid not in patient_ids:
            orphan_summary["prediction_orphans"] += 1
            if apply_fix:
                db["prediction_results"].delete_one({"_id": doc["_id"]})
                orphan_summary["repaired_or_removed"] += 1

    return orphan_summary


def audit_and_repair_vitals(db: Database, apply_fix: bool = False) -> dict:
    """Detect and optionally repair malformed or out-of-range clinical vitals."""
    summary = {
        "scanned_records": 0,
        "bp_anomalies": 0,
        "cholesterol_anomalies": 0,
        "missing_timestamps": 0,
        "repaired_records": 0,
    }

    for doc in db["clinical_records"].find():
        summary["scanned_records"] += 1
        needs_fix = False
        updates: dict[str, Any] = {}

        # 1. Resting BP validation (range: 50 - 250 mmHg)
        bp = doc.get("resting_bp")
        if bp is not None:
            try:
                bp_val = float(bp)
                if bp_val < 50:
                    summary["bp_anomalies"] += 1
                    updates["resting_bp"] = 120.0
                    needs_fix = True
                elif bp_val > 250:
                    summary["bp_anomalies"] += 1
                    updates["resting_bp"] = 220.0
                    needs_fix = True
            except (ValueError, TypeError):
                summary["bp_anomalies"] += 1
                updates["resting_bp"] = 120.0
                needs_fix = True

        # 2. Cholesterol validation (range: 50 - 600 mg/dL)
        chol = doc.get("cholesterol")
        if chol is not None:
            try:
                chol_val = float(chol)
                if chol_val < 50:
                    summary["cholesterol_anomalies"] += 1
                    updates["cholesterol"] = 180.0
                    needs_fix = True
                elif chol_val > 600:
                    summary["cholesterol_anomalies"] += 1
                    updates["cholesterol"] = 500.0
                    needs_fix = True
            except (ValueError, TypeError):
                summary["cholesterol_anomalies"] += 1
                updates["cholesterol"] = 180.0
                needs_fix = True

        # 3. Timestamp verification
        recorded_at = doc.get("recorded_at")
        if not recorded_at:
            summary["missing_timestamps"] += 1
            updates["recorded_at"] = datetime.now(timezone.utc)
            needs_fix = True
        elif isinstance(recorded_at, str):
            try:
                parsed_dt = datetime.fromisoformat(recorded_at.replace("Z", "+00:00"))
                updates["recorded_at"] = parsed_dt
                needs_fix = True
            except Exception:
                updates["recorded_at"] = datetime.now(timezone.utc)
                needs_fix = True

        if needs_fix and apply_fix:
            db["clinical_records"].update_one(
                {"_id": doc["_id"]},
                {"$set": updates}
            )
            summary["repaired_records"] += 1

    return summary


def audit_and_repair_predictions(db: Database, apply_fix: bool = False) -> dict:
    """Ensure prediction_results have valid numeric risk scores and dict shap_values."""
    summary = {
        "scanned_predictions": 0,
        "malformed_shap": 0,
        "malformed_risk_score": 0,
        "repaired_predictions": 0,
    }

    for doc in db["prediction_results"].find():
        summary["scanned_predictions"] += 1
        needs_fix = False
        updates: dict[str, Any] = {}

        # 1. SHAP values validation
        shap = doc.get("shap_values")
        if shap is None or not isinstance(shap, dict):
            summary["malformed_shap"] += 1
            updates["shap_values"] = {}
            needs_fix = True

        # 2. Risk score validation (range: 0.0 - 1.0)
        risk = doc.get("risk_score")
        if risk is None:
            summary["malformed_risk_score"] += 1
            updates["risk_score"] = 0.5
            needs_fix = True
        else:
            try:
                r_val = float(risk)
                if r_val < 0.0 or r_val > 1.0:
                    summary["malformed_risk_score"] += 1
                    updates["risk_score"] = max(0.0, min(1.0, r_val))
                    needs_fix = True
            except (ValueError, TypeError):
                summary["malformed_risk_score"] += 1
                updates["risk_score"] = 0.5
                needs_fix = True

        # 3. Created_at timestamp check
        if not doc.get("created_at"):
            updates["created_at"] = datetime.now(timezone.utc)
            needs_fix = True

        if needs_fix and apply_fix:
            db["prediction_results"].update_one(
                {"_id": doc["_id"]},
                {"$set": updates}
            )
            summary["repaired_predictions"] += 1

    return summary


def verify_and_repair_indexes(db: Database, apply_fix: bool = False) -> dict:
    """Audit database collection indexes against expected schemas and rebuild missing ones."""
    expected_indexes = {
        "patients": ["patientId_1", "createdAt_-1"],
        "clinical_records": ["patient_id_1", "patient_id_1_recorded_at_-1"],
        "ecg_recordings": ["patient_id_1", "patient_id_1_uploaded_at_-1"],
        "prediction_results": ["patient_id_1", "patient_id_1_created_at_-1"],
    }

    status = {
        "checked_collections": len(expected_indexes),
        "missing_indexes": 0,
        "rebuilt_indexes": 0,
    }

    for coll_name, exp_names in expected_indexes.items():
        try:
            existing = [idx["name"] for idx in db[coll_name].list_indexes()]
        except Exception:
            existing = []

        for exp in exp_names:
            if exp not in existing:
                status["missing_indexes"] += 1
                if apply_fix:
                    try:
                        from database import init_indexes
                        init_indexes()
                        status["rebuilt_indexes"] += 1
                    except Exception as e:
                        logger.warning("Failed building index %s on %s: %s", exp, coll_name, e)

    return status


def run_full_database_diagnosis(db: Database, apply_fix: bool = False) -> dict:
    """Execute all diagnostic passes and assemble a unified health and repair report."""
    orphans = audit_and_repair_orphans(db, apply_fix=apply_fix)
    vitals = audit_and_repair_vitals(db, apply_fix=apply_fix)
    predictions = audit_and_repair_predictions(db, apply_fix=apply_fix)
    indexes = verify_and_repair_indexes(db, apply_fix=apply_fix)

    total_issues = (
        orphans["clinical_orphans"]
        + orphans["ecg_orphans"]
        + orphans["prediction_orphans"]
        + vitals["bp_anomalies"]
        + vitals["cholesterol_anomalies"]
        + vitals["missing_timestamps"]
        + predictions["malformed_shap"]
        + predictions["malformed_risk_score"]
        + indexes["missing_indexes"]
    )

    total_repairs = (
        orphans["repaired_or_removed"]
        + vitals["repaired_records"]
        + predictions["repaired_predictions"]
        + indexes["rebuilt_indexes"]
    )

    return {
        "mode": "APPLY_REPAIRS" if apply_fix else "DRY_RUN_AUDIT",
        "total_anomalies_detected": total_issues,
        "total_repairs_executed": total_repairs,
        "orphan_summary": orphans,
        "vitals_summary": vitals,
        "predictions_summary": predictions,
        "indexes_summary": indexes,
    }


def print_report_table(report: dict) -> None:
    """Print ASCII report table summarizing diagnostic and repair findings."""
    print("=" * 72)
    print("  CVD-XAI MONGODB DATABASE ANOMALY DIAGNOSTIC & REPAIR REPORT")
    print("  Sprint 4 (22/11/26 - 04/12/26): Fix Database Issue")
    print(f"  Mode: {report['mode']}")
    print("=" * 72)
    print(f"  Total Anomalies Detected: {report['total_anomalies_detected']}")
    print(f"  Total Repairs Executed:   {report['total_repairs_executed']}")
    print("-" * 72)
    print("  1. ORPHAN RECORDS AUDIT:")
    print(f"     - Clinical records without parent:    {report['orphan_summary']['clinical_orphans']}")
    print(f"     - ECG recordings without parent:      {report['orphan_summary']['ecg_orphans']}")
    print(f"     - Prediction results without parent:  {report['orphan_summary']['prediction_orphans']}")
    print(f"     - Repaired/Removed:                   {report['orphan_summary']['repaired_or_removed']}")
    print("-" * 72)
    print("  2. CLINICAL VITALS SANITIZATION:")
    print(f"     - Scanned Clinical Records:           {report['vitals_summary']['scanned_records']}")
    print(f"     - Blood Pressure Outliers:            {report['vitals_summary']['bp_anomalies']}")
    print(f"     - Cholesterol Outliers:               {report['vitals_summary']['cholesterol_anomalies']}")
    print(f"     - Missing/String Timestamps:          {report['vitals_summary']['missing_timestamps']}")
    print(f"     - Repaired Records:                   {report['vitals_summary']['repaired_records']}")
    print("-" * 72)
    print("  3. EXPLAINABILITY & PREDICTION INTEGRITY:")
    print(f"     - Scanned Predictions:                {report['predictions_summary']['scanned_predictions']}")
    print(f"     - Malformed SHAP Values:              {report['predictions_summary']['malformed_shap']}")
    print(f"     - Malformed Risk Scores:              {report['predictions_summary']['malformed_risk_score']}")
    print(f"     - Repaired Predictions:               {report['predictions_summary']['repaired_predictions']}")
    print("-" * 72)
    print("  4. COLLECTION INDEXING HEALTH:")
    print(f"     - Checked Core Collections:           {report['indexes_summary']['checked_collections']}")
    print(f"     - Missing Performance Indexes:        {report['indexes_summary']['missing_indexes']}")
    print(f"     - Rebuilt Indexes:                    {report['indexes_summary']['rebuilt_indexes']}")
    print("=" * 72)


def main():
    parser = argparse.ArgumentParser(description="Audit and repair CVD-XAI MongoDB data anomalies.")
    parser.add_argument("--apply", action="store_true", help="Apply fixes directly to the database.")
    args = parser.parse_args()

    try:
        from database import get_db, ping_db_resilient
        status = ping_db_resilient()
        if not status.get("connected"):
            print(f"[ERROR] Cannot connect to MongoDB: {status.get('error')}")
            sys.exit(1)
        db = get_db()
    except Exception as exc:
        print(f"[ERROR] Failed initializing MongoDB connection: {exc}")
        sys.exit(1)

    report = run_full_database_diagnosis(db, apply_fix=args.apply)
    print_report_table(report)


if __name__ == "__main__":
    main()
