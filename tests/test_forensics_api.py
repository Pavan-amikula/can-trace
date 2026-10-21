from copy import deepcopy
from pathlib import Path
import json
import numpy as np
from fastapi.testclient import TestClient

from cantrace.api import create_app
from cantrace.forensics import package_case, verify_case


def test_integrity_detects_payload_mutation_and_chain_reordering():
    original = package_case(
        [{"score": 0.1}, {"score": 0.2}], "a" * 64, "b" * 64, {"rank": 4}
    )
    assert verify_case(original)
    modified = deepcopy(original)
    modified["case"]["chain"][0]["event"]["score"] = 100
    assert not verify_case(modified)
    reordered = deepcopy(original)
    reordered["case"]["chain"].reverse()
    assert not verify_case(reordered)
    assert not verify_case({})


def test_ready_api_export_stream_and_bounds():
    root = Path(__file__).resolve().parents[1]
    if not (root / "artifacts/replay.json").exists():
        import pytest

        pytest.skip("integration: run evaluation first")
    client = TestClient(create_app(root))
    assert client.get("/api/health").json()["status"] == "ready"
    response = client.get("/api/case/0/export")
    assert response.status_code == 200 and verify_case(response.json())
    assert "attachment;" in response.headers["content-disposition"]
    assert client.get("/api/case/-1").status_code == 404
    assert client.get("/api/stream?start=-1").status_code == 422
    summary = client.get("/api/summary").json()
    response = client.get(f"/api/stream?start={summary['events']-1}&speed=50")
    data = [
        json.loads(line[6:])
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ][0]
    case = client.get(f"/api/case/{summary['events']-1}").json()
    assert (
        abs(data["score"] - case["case"]["chain"][0]["event"]["explanation"]["score"])
        < 1e-12
    )
    assert "frame-ancestors" in response.headers["content-security-policy"]
