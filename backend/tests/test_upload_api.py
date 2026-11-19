"""API tests for ECG file upload metadata validation and defaults."""

from unittest.mock import MagicMock

from bson import ObjectId
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

import upload as upload_module
from auth import get_current_user
from database import get_db


@pytest.fixture
def upload_client(tmp_path, monkeypatch):
    user = {"_id": ObjectId(), "role": "doctor"}
    db = MagicMock()
    record_id = ObjectId()
    db["ecg_recordings"].insert_one.return_value.inserted_id = record_id
    db["ecg_recordings"].find_one.return_value = {
        "_id": record_id,
        "original_name": "sample.csv",
        "size_bytes": 7,
        "patient_id": str(user["_id"]),
        "sampling_rate_hz": 500,
        "lead_count": 12,
        "processing_status": "uploaded",
    }

    monkeypatch.setattr(upload_module, "UPLOADS_DIR", tmp_path)
    app = FastAPI()
    app.include_router(upload_module.router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app), db


@pytest.mark.parametrize(
    "metadata",
    [
        {"sampling_rate_hz": 99},
        {"sampling_rate_hz": 2001},
        {"lead_count": 2},
        {"duration_seconds": 0},
        {"duration_seconds": 3601},
    ],
)
def test_ecg_upload_rejects_invalid_signal_metadata(upload_client, metadata):
    client, db = upload_client

    response = client.post(
        "/api/data/ecg",
        files={"file": ("sample.csv", b"1,2,3\n", "text/csv")},
        data=metadata,
    )

    assert response.status_code == 422
    db["ecg_recordings"].insert_one.assert_not_called()


def test_ecg_upload_defaults_to_standard_12_lead_metadata(upload_client):
    client, db = upload_client

    response = client.post(
        "/api/data/ecg",
        files={"file": ("sample.csv", b"1,2,3\n", "text/csv")},
    )

    assert response.status_code == 201
    saved_record = db["ecg_recordings"].insert_one.call_args.args[0]
    assert saved_record["sampling_rate_hz"] == 500
    assert saved_record["lead_count"] == 12
    assert response.json()["lead_count"] == 12
