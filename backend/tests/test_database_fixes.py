"""test_database_fixes.py - Automated unit tests for Sprint 4 database fixes.

Tests:
  1. Connection retry decorator with exponential backoff on transient errors
  2. Retry exhaustion behavior
  3. BSON ObjectId and datetime recursive serialization
  4. normalize_mongo_doc and normalize_mongo_cursor transformations
  5. safe_find_one and safe_find query wrappers
  6. Database connection healthcheck probe
  7. Orphan detection and repair logic in fix_database_anomalies
  8. Clinical vitals outlier detection and sanitization
  9. Prediction explainability integrity and risk score bounding
  10. Unified diagnostic execution pipeline
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock
import mongomock
import pytest
from bson import ObjectId
from pymongo.errors import AutoReconnect, ConnectionFailure

from database import (
    with_db_retry,
    execute_with_retry,
    serialize_object_id,
    normalize_mongo_doc,
    normalize_mongo_cursor,
    safe_find_one,
    safe_find,
    check_connection_health,
)
from fix_database_anomalies import (
    audit_and_repair_orphans,
    audit_and_repair_vitals,
    audit_and_repair_predictions,
    run_full_database_diagnosis,
)


# =========================================================================
# 1. RETRY MECHANISM TESTS
# =========================================================================

def test_retry_decorator_success_first_try():
    """Verify standard execution when no exception occurs."""
    mock_func = MagicMock(return_value="db_connected")
    decorated = with_db_retry(max_retries=3, base_delay=0.01)(mock_func)

    res = decorated("arg1", key="val")
    assert res == "db_connected"
    assert mock_func.call_count == 1


def test_retry_decorator_recovers_after_transient_failure():
    """Verify recovery when transient AutoReconnect occurs twice then succeeds."""
    mock_func = MagicMock(side_effect=[AutoReconnect("Socket timeout"), AutoReconnect("Reset by peer"), "recovered_payload"])
    decorated = with_db_retry(max_retries=3, base_delay=0.01)(mock_func)

    res = decorated()
    assert res == "recovered_payload"
    assert mock_func.call_count == 3


def test_retry_decorator_raises_on_exhaustion():
    """Verify exception is raised when max retries are exceeded."""
    mock_func = MagicMock(side_effect=ConnectionFailure("Host unreachable"))
    decorated = with_db_retry(max_retries=2, base_delay=0.01)(mock_func)

    with pytest.raises(ConnectionFailure):
        decorated()
    assert mock_func.call_count == 2


def test_execute_with_retry_helper():
    """Verify helper function passes args and executes successfully."""
    def sample_query(coll_name: str, limit: int = 5):
        return f"queried_{coll_name}_{limit}"

    res = execute_with_retry(sample_query, "patients", limit=10, max_retries=2, base_delay=0.01)
    assert res == "queried_patients_10"


# =========================================================================
# 2. BSON SERIALIZATION AND NORMALIZATION TESTS
# =========================================================================

def test_serialize_object_id_primitives_and_nested():
    """Verify recursive serialization of ObjectId, datetime, and nested collections."""
    oid = ObjectId("654321654321654321654321")
    now = datetime(2026, 11, 27, 10, 0, 0, tzinfo=timezone.utc)

    raw_data = {
        "_id": oid,
        "name": "Test Patient",
        "nested": {
            "ref_id": oid,
            "created_at": now,
            "list_ids": [oid, 123, "plain_str"],
        },
    }

    serialized = serialize_object_id(raw_data)
    assert serialized["_id"] == "654321654321654321654321"
    assert serialized["nested"]["ref_id"] == "654321654321654321654321"
    assert serialized["nested"]["created_at"] == now.isoformat()
    assert serialized["nested"]["list_ids"][0] == "654321654321654321654321"
    assert serialized["nested"]["list_ids"][1] == 123


def test_normalize_mongo_doc_converts_id_field():
    """Verify _id is transformed to id and original _id removed."""
    oid = ObjectId("111111111111111111111111")
    doc = {"_id": oid, "patientId": "CVD-101", "risk": "high"}

    normalized = normalize_mongo_doc(doc, id_field="id", keep_raw_id=False)
    assert normalized["id"] == "111111111111111111111111"
    assert "_id" not in normalized
    assert normalized["patientId"] == "CVD-101"

    # None document returns None
    assert normalize_mongo_doc(None) is None


def test_normalize_mongo_cursor():
    """Verify normalizing a sequence of documents."""
    docs = [
        {"_id": ObjectId("111111111111111111111111"), "val": 1},
        {"_id": ObjectId("222222222222222222222222"), "val": 2},
    ]
    results = normalize_mongo_cursor(docs)
    assert len(results) == 2
    assert results[0]["id"] == "111111111111111111111111"
    assert results[1]["id"] == "222222222222222222222222"


def test_safe_find_one_and_safe_find():
    """Verify safe_find_one and safe_find execute against mock database with normalization."""
    mock_client = mongomock.MongoClient()
    db = mock_client["test_db"]
    db["items"].insert_many([
        {"item_name": "A", "score": 90},
        {"item_name": "B", "score": 80},
    ])

    one = safe_find_one("items", {"item_name": "A"}, db=db)
    assert one is not None
    assert "id" in one
    assert one["item_name"] == "A"

    all_items = safe_find("items", db=db, sort=[("score", -1)])
    assert len(all_items) == 2
    assert all_items[0]["item_name"] == "A"
    assert all_items[1]["item_name"] == "B"


def test_check_connection_health_on_mock():
    """Verify diagnostic check on mock database."""
    mock_client = mongomock.MongoClient()
    db = mock_client["test_health_db"]
    res = check_connection_health(db=db)
    assert res["ok"] is True
    assert res["writable"] is True
    assert res["database"] == "test_health_db"


# =========================================================================
# 3. DATABASE ANOMALY DIAGNOSTIC & REPAIR TESTS
# =========================================================================

def test_audit_and_repair_orphans():
    """Verify identification and cleanup of orphan clinical and prediction records."""
    mock_client = mongomock.MongoClient()
    db = mock_client["test_anomaly_db"]

    # 1 valid patient
    p_id = db["patients"].insert_one({"patientId": "CVD-999"}).inserted_id

    # 1 valid clinical record, 2 orphan clinical records
    db["clinical_records"].insert_one({"patient_id": "CVD-999", "systolic": 120})
    db["clinical_records"].insert_one({"patient_id": "NON_EXISTENT_1", "systolic": 140})
    db["clinical_records"].insert_one({"patient_id": "NON_EXISTENT_2", "systolic": 150})

    # Dry-run audit
    audit = audit_and_repair_orphans(db, apply_fix=False)
    assert audit["clinical_orphans"] == 2
    assert audit["repaired_or_removed"] == 0
    assert db["clinical_records"].count_documents({}) == 3

    # Apply fixes
    repair = audit_and_repair_orphans(db, apply_fix=True)
    assert repair["clinical_orphans"] == 2
    assert repair["repaired_or_removed"] == 2
    assert db["clinical_records"].count_documents({}) == 1


def test_audit_and_repair_vitals():
    """Verify outlier vital signs are clamped to safe boundaries and timestamps fixed."""
    mock_client = mongomock.MongoClient()
    db = mock_client["test_vitals_db"]

    # Insert anomaly records:
    # 1. Negative resting_bp and out-of-range cholesterol
    # 2. String timestamp
    db["clinical_records"].insert_one({
        "resting_bp": 300,  # too high (>250)
        "cholesterol": 20,   # too low (<50)
        "recorded_at": None,
    })

    # Dry-run
    dry_report = audit_and_repair_vitals(db, apply_fix=False)
    assert dry_report["bp_anomalies"] == 1
    assert dry_report["cholesterol_anomalies"] == 1
    assert dry_report["missing_timestamps"] == 1
    assert dry_report["repaired_records"] == 0

    # Apply fix
    fix_report = audit_and_repair_vitals(db, apply_fix=True)
    assert fix_report["repaired_records"] == 1

    repaired = db["clinical_records"].find_one()
    assert repaired["resting_bp"] == 220.0
    assert repaired["cholesterol"] == 180.0
    assert isinstance(repaired["recorded_at"], datetime)


def test_audit_and_repair_predictions():
    """Verify malformed SHAP and risk scores are sanitized."""
    mock_client = mongomock.MongoClient()
    db = mock_client["test_pred_db"]

    db["prediction_results"].insert_one({
        "patient_id": "CVD-101",
        "risk_score": 1.85,  # Out of [0, 1] range
        "shap_values": None,  # Not a dict
    })

    fix_report = audit_and_repair_predictions(db, apply_fix=True)
    assert fix_report["malformed_shap"] == 1
    assert fix_report["malformed_risk_score"] == 1
    assert fix_report["repaired_predictions"] == 1

    doc = db["prediction_results"].find_one({"patient_id": "CVD-101"})
    assert doc["risk_score"] == 1.0  # Clamped to 1.0
    assert doc["shap_values"] == {}
    assert "created_at" in doc


def test_run_full_database_diagnosis_pipeline():
    """Verify full end-to-end diagnostic suite execution."""
    mock_client = mongomock.MongoClient()
    db = mock_client["test_pipeline_db"]

    db["patients"].insert_one({"patientId": "CVD-PAT-1"})
    db["clinical_records"].insert_one({
        "patient_id": "ORPHAN-PAT",
        "resting_bp": 35,
        "cholesterol": 750,
        "recorded_at": None,
    })

    full_report = run_full_database_diagnosis(db, apply_fix=True)
    assert full_report["mode"] == "APPLY_REPAIRS"
    assert full_report["total_anomalies_detected"] >= 3
    assert full_report["total_repairs_executed"] >= 1
