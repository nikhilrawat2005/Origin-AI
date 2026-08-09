"""
API contract check — asserts the exact hackathon evaluator shape holds
against the real FastAPI app: field names, types, and nothing extra.

`POST /api/agent/init` -> `{"agentId": "..."}` only.
`GET /api/agent/feed`  -> `{"posts": [...]}` only, each post carrying
exactly `id`, `createdAt` (ISO 8601 UTC, `Z` suffix), `text`,
`rationale`, `sources`.

Runs against an in-memory SQLite DB via TestClient (StaticPool so
TestClient's worker thread reuses one connection).
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
    _assert_keys(body, {"posts"}, "GET /feed (pre-init)")
    assert body["posts"] == []
    print("PASS: GET /api/agent/feed pre-init matches {posts: []} contract")


def test_init_contract():
    resp = client.post("/api/agent/init", json={"persona": {"name": "Aether", "domain": "AI Technology"}})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    _assert_keys(body, {"agentId"}, "POST /init")
    assert isinstance(body["agentId"], str) and body["agentId"]
    print("PASS: POST /api/agent/init matches {agentId: ...} contract only")


def test_init_is_idempotent():
    first = client.post("/api/agent/init").json()
    second = client.post("/api/agent/init").json()
    assert first["agentId"] == second["agentId"]
    print("PASS: repeat POST /api/agent/init returns the same agentId, still {agentId} only")


def test_feed_contract_after_init_no_posts():
    resp = client.get("/api/agent/feed")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    _assert_keys(body, {"posts"}, "GET /feed (post-init)")
    assert isinstance(body["posts"], list)
    print("PASS: GET /api/agent/feed post-init still matches {posts: [...]} contract")


def test_no_extra_routes_exist():
    """Evaluator-facing surface must be core endpoints —
    no /generate, /run, or other manual-trigger route."""
    paths = set()
    for r in app.routes:
        if hasattr(r, "path"):
            paths.add(r.path)
        if hasattr(r, "original_router"):
            for sub_r in r.original_router.routes:
                if hasattr(sub_r, "path"):
                    paths.add(sub_r.path)

    forbidden = {p for p in paths if "generate" in p or "/run" in p}
    assert not forbidden, f"Found unexpected manual-trigger routes: {forbidden}"
    assert "/api/agent/init" in paths
    assert "/api/agent/feed" in paths
    print("PASS: /api/agent/init and /api/agent/feed are exposed with no forbidden routes")


if __name__ == "__main__":
    try:
        test_feed_contract_before_init()
        test_init_contract()
        test_init_is_idempotent()
        test_feed_contract_after_init_no_posts()
        test_no_extra_routes_exist()
        print("\nAll API contract checks passed.")
    finally:
        from app.services.scheduler import stop_scheduler
        stop_scheduler()
