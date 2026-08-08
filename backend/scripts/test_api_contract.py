"""
Stage 20 verification — API contract check.

Distinct from `test_feed_endpoint.py` / earlier stage scripts, which
test each route's internal *logic* (empty-vs-populated states,
idempotency, dedup, etc.). This script instead asserts the exact
*shape* documented in `docs/API_CONTRACT.md` holds against the real
FastAPI app — field names, types, and nullability — so a future change
to either route's response model can't silently drift from what's
published as the frozen contract without this failing.

Runs against an in-memory SQLite DB via TestClient, same pattern as
`test_feed_endpoint.py` (StaticPool so TestClient's worker thread
reuses one connection).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.database import Base, get_db  # noqa: E402
import app.models  # noqa: F401,E402  (register models on Base.metadata)
from app.main import app  # noqa: E402

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db
client = TestClient(app)


def _assert_keys(body: dict, expected_keys: set, label: str):
    actual_keys = set(body.keys())
    assert actual_keys == expected_keys, (
        f"{label}: key mismatch.\n  expected: {sorted(expected_keys)}\n"
        f"  actual:   {sorted(actual_keys)}"
    )


def test_feed_contract_before_init():
    resp = client.get("/api/agent/feed")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    _assert_keys(
        body, {"agentId", "personaName", "status", "posts"}, "GET /feed (pre-init)"
    )
    assert body["agentId"] is None
    assert body["personaName"] is None
    assert body["status"] is None
    assert body["posts"] == []
    print("PASS: GET /api/agent/feed pre-init matches documented empty-feed contract")


def test_init_contract():
    resp = client.post("/api/agent/init")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    _assert_keys(
        body,
        {
            "agentId",
            "status",
            "personaName",
            "personaDescription",
            "breethAgentRef",
            "createdAt",
        },
        "POST /init",
    )
    assert isinstance(body["agentId"], str) and body["agentId"]
    assert body["status"] == "active"
    assert isinstance(body["personaName"], str) and body["personaName"]
    assert body["personaDescription"] is None or isinstance(
        body["personaDescription"], str
    )
    assert isinstance(body["breethAgentRef"], str) and body["breethAgentRef"]
    assert isinstance(body["createdAt"], str) and body["createdAt"]
    print("PASS: POST /api/agent/init matches documented contract (status=active)")


def test_init_is_idempotent():
    first = client.post("/api/agent/init").json()
    second = client.post("/api/agent/init").json()
    assert first["agentId"] == second["agentId"]
    print("PASS: repeat POST /api/agent/init returns the same agentId")


def test_feed_contract_after_init_no_posts():
    resp = client.get("/api/agent/feed")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    _assert_keys(
        body, {"agentId", "personaName", "status", "posts"}, "GET /feed (post-init)"
    )
    assert isinstance(body["agentId"], str) and body["agentId"]
    assert isinstance(body["personaName"], str) and body["personaName"]
    assert body["status"] == "active"
    assert isinstance(body["posts"], list)
    print(
        "PASS: GET /api/agent/feed post-init matches documented agent-identity contract"
    )


if __name__ == "__main__":
    test_feed_contract_before_init()
    test_init_contract()
    test_init_is_idempotent()
    test_feed_contract_after_init_no_posts()
    print("\nAll Stage 20 API contract checks passed.")
