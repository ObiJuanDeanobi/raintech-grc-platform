from __future__ import annotations

import io
import zipfile

from cmmc_tracker.db import connect, init_db
from cmmc_tracker.platform_services import (
    create_assessment,
    create_client,
    create_quote_record,
    evidence_capture_rows,
    export_platform_package,
    generate_documents,
    get_assessment,
    get_profile,
    link_evidence,
    list_controls,
    list_documents,
    tailored_evidence_guidance,
    update_profile,
    update_result,
)
from cmmc_tracker.services import store_upload


def setup_platform(monkeypatch, tmp_path):
    monkeypatch.setenv("CMMC_TRACKER_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CMMC_TRACKER_DB", str(tmp_path / "tracker.db"))
    init_db()


def test_profile_quote_and_assessment_workspace(monkeypatch, tmp_path):
    setup_platform(monkeypatch, tmp_path)

    client = create_client({"name": "Acme Defense", "primary_contact_email": "it@example.com"})
    profile = update_profile(
        client["id"],
        {
            "legal_name": "Acme Defense",
            "system_name": "Acme CUI Enclave",
            "environment_shape": "enclave",
            "required_cloud": "gcc",
            "current_cloud": "commercial_m365",
            "cui_type": "basic",
            "cui_flow": "CUI enters from a prime portal and is stored in the CUI workspace.",
            "cui_users": 12,
            "endpoint_management": "managed",
            "mfa_status": "yes",
            "logging_status": "yes",
            "encryption_status": "yes",
            "internal_owner": "owner_it",
            "ongoing_support": "yes",
        },
    )
    quote = create_quote_record(client["id"], profile)
    assessment = create_assessment(client["id"], "CMMC Level 2 Readiness")

    assert get_profile(client["id"])["system_name"] == "Acme CUI Enclave"
    assert quote["package_name"] == "GCC Enclave + CMMC L2 Prep"
    assert quote["quote_range"] == "$40k-$75k"
    assert get_assessment(assessment["id"])["score"]["total"] == 320


def test_assessment_evidence_mapping_documents_and_export(monkeypatch, tmp_path):
    setup_platform(monkeypatch, tmp_path)
    client = create_client({"name": "Acme Defense"})
    update_profile(
        client["id"],
        {
            "system_name": "Acme CUI Enclave",
            "environment_shape": "enclave",
            "required_cloud": "gcc",
            "current_cloud": "commercial_m365",
            "cui_type": "basic",
            "cui_flow": "CUI enters from a prime portal and is stored in the CUI workspace.",
            "cui_users": 10,
        },
    )
    assessment = create_assessment(client["id"], "CMMC Level 2 Readiness")
    result = list_controls(assessment["id"])[0]
    evidence_id = store_upload(io.BytesIO(b"access list"), "Access List.xlsx", "Authorized user list")

    link_evidence(result["result_id"], evidence_id)
    update_result(result["result_id"], {"status": "partial", "notes": "Need owner approval record."})
    docs = generate_documents(client["id"], assessment["id"])
    package = export_platform_package(client["id"], assessment["id"])

    rows = evidence_capture_rows(assessment["id"])
    guidance = tailored_evidence_guidance(client["id"], result["objective_id"])

    assert rows[0]["evidence_count"] == 1
    assert guidance["recommended_sources"]
    assert len(docs) >= 4
    assert list_documents(client["id"], assessment["id"])
    with zipfile.ZipFile(package) as archive:
        names = archive.namelist()
        assert "reports/evidence_capture.xlsx" in names
        assert "reports/poam.xlsx" in names
        assert "evidence/manifest.csv" in names
        assert any(name.startswith("documents/") for name in names)
        assert any(name.startswith("evidence/") and name.endswith(".xlsx") for name in names)

    with connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM poam_items").fetchone()[0] == 1
