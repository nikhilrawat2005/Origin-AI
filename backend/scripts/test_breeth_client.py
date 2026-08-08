"""
Standalone verification script for Stage 9 — Breeth Client (connection only).

Run with:  python -m scripts.test_breeth_client   (from backend/)

Checks:
1. BreethClient raises a clear BreethConfigError when used without an
   API key, instead of a confusing network/auth failure.
2. If BREETH_API_KEY is set in the environment, makes two real calls
   as a live connection test: writes a test fact via `write_fact()`,
   then searches for it via `search()` and confirms the written fact
   shows up in the results. If it's not set (the expected case in this
   sandboxed dev environment — see PROJECT_STATUS.md "Known
   Constraints"), both steps are skipped with a clear message rather
   than failing the script.

This is a connection smoke test only — no namespace-per-agent logic
(Stage 10), no dedup/rejected-topic queries (Stage 15+). Just: can we
reach Breeth with these credentials and round-trip one fact.
"""
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.breeth_client import (  # noqa: E402
    BreethClient,
    BreethConfigError,
)
from app.core.config import get_settings  # noqa: E402


def main() -> None:
    print("1. Confirming missing API key raises a clear error...")
    unconfigured = BreethClient(api_key="")
    try:
        unconfigured.write_fact("Aether", "tests", "connectivity")
        raise AssertionError("Expected BreethConfigError with no API key")
    except BreethConfigError as e:
        print(f"   OK — BreethConfigError raised: {e}")

    print("2. Checking for a real BREETH_API_KEY for a live connection test...")
    settings = get_settings()
    if not settings.breeth_api_key:
        print(
            "   SKIPPED — no BREETH_API_KEY set in backend/.env. This is "
            "expected in this sandboxed dev environment (see "
            "PROJECT_STATUS.md 'Known Constraints'). Set a real key and "
            "re-run this script to exercise the live write/search path."
        )
        print("\nAll Stage 9 BreethClient checks passed (live path skipped).")
        return

    client = BreethClient()

    # Unique object value per run so search results are unambiguous
    # even if this script has been run against the same account before.
    marker = f"stage9-verification-{uuid.uuid4().hex[:8]}"
    print(f"   Writing test fact with marker: {marker!r}")
    write_result = client.write_fact(
        subject="Aether",
        predicate="verified_connection_with_marker",
        object_=marker,
        group_id="stage9-test",
    )
    assert write_result.get("ok") is True
    print(f"   OK — write succeeded, episode_name={write_result.get('episode_name')!r}")

    print("   Searching for the fact we just wrote...")
    search_result = client.search(
        query=f"What is the marker {marker}?",
        group_id="stage9-test",
    )
    facts = [edge.get("fact", "") for edge in search_result.get("edges", [])]
    found = any(marker in fact for fact in facts)
    assert found, (
        f"Wrote a fact with marker {marker!r} but did not find it in "
        f"search results: {facts}"
    )
    print(f"   OK — search found the marker in {len(facts)} candidate edge(s)")

    print("\nAll Stage 9 BreethClient checks passed, including the live round-trip.")


if __name__ == "__main__":
    main()
