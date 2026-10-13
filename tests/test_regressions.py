"""Regression tests for oxygenation validity, CSV robustness and audit signatures."""
import csv
import math
import pytest
from pf_ratio_ards import (
    pf_ratio, spo2_fio2_ratio, oxygenation_index, a_a_gradient,
    normal_a_a_gradient, berlin_ards_classification, process_csv,
)
from agents.base import AuditTrail


@pytest.mark.parametrize("fio2", [-1, 0, 1.01, math.nan, math.inf])
def test_invalid_fio2(fio2):
    with pytest.raises(ValueError):
        pf_ratio(80, fio2)


@pytest.mark.parametrize("pao2", [-1, math.nan, math.inf])
def test_invalid_pao2(pao2):
    with pytest.raises(ValueError):
        pf_ratio(pao2, 0.5)


def test_rejects_invalid_other_measurements():
    with pytest.raises(ValueError):
        spo2_fio2_ratio(math.nan, 0.5)
    with pytest.raises(ValueError):
        oxygenation_index(0.4, math.inf, 80)
    with pytest.raises(ValueError):
        a_a_gradient(0.4, 80, 40, rq=0)
    with pytest.raises(ValueError):
        normal_a_a_gradient(-10)


def test_missing_peep_is_unverified():
    result = berlin_ards_classification(80, 0.5)
    assert result["pf_ratio"] == 160
    assert result["meets_peep_criteria"] is False
    assert "unverified" in result["peep_warning"]
    assert result["ards_diagnosis_confirmed"] is False


@pytest.mark.parametrize("pf,fragment", [(300,"Mild"), (200,"Moderate"), (100,"Severe"), (301,"No ARDS")])
def test_exact_berlin_cutoffs(pf, fragment):
    assert fragment in berlin_ards_classification(pf * 0.5, 0.5, 5)["severity"]


def test_batch_optional_columns_and_header(tmp_path):
    source, target = tmp_path / "data.csv", tmp_path / "out.csv"
    source.write_text("patient_id,pao2,fio2,paco2,peep,spo2,age\n"
                      "A,80,0.5,40,10,95,\n"
                      "B,60,0.4,40,,,55\n")
    assert process_csv(str(source), str(target)) == 2
    with target.open(newline="") as file:
        rows = list(csv.DictReader(file))
    assert len(rows) == 2
    assert rows[0]["spo2_fio2_ratio"] != ""
    assert rows[1]["spo2_fio2_ratio"] == ""
    assert rows[0]["normal_a_a_gradient"] == ""
    assert rows[1]["normal_a_a_gradient"] != ""


def test_bad_batch_does_not_truncate_existing_output(tmp_path):
    source, target = tmp_path / "data.csv", tmp_path / "out.csv"
    source.write_text("pao2,fio2,paco2\n80,0.5,40\n60,0,40\n")
    target.write_text("existing content")
    with pytest.raises(ValueError, match="row 3"):
        process_csv(str(source), str(target))
    assert target.read_text() == "existing content"
    with pytest.raises(ValueError):
        process_csv(str(source), str(source))


def test_audit_signature_tamper_detected():
    ledger = AuditTrail("local-test-secret")
    ledger.log("supervisor", "tier", "event", {"status":"ok"})
    assert ledger.verify_integrity()
    snapshot = ledger.get_trail()
    snapshot[0]["event_type"] = "changed"
    assert ledger.verify_integrity()  # returned trail cannot mutate original
    ledger.logs[0]["event_type"] = "changed"
    assert not ledger.verify_integrity()


def test_api_assessment(tmp_path):
    from fastapi.testclient import TestClient
    from agents.api import app
    client = TestClient(app)
    good = client.post("/api/assessment", json={"pao2": 80, "fio2":0.5})
    assert good.status_code == 200
    assert good.json()["meets_peep_criteria"] is False
    bad = client.post("/api/assessment", json={"pao2": 80, "fio2": 1.2})
    assert bad.status_code == 422
    assert client.get("/").status_code == 200
    assert client.get("/api/audit/logs").status_code == 403
