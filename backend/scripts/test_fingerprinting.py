"""
Stage 13 verification — Fingerprinting.

Pure unit tests, no DB required (fingerprinting is a standalone
function this stage — nothing is wired into `sources_cache` or any
route yet). Confirms:
1. `compute_fingerprint()` is deterministic.
2. Reworded/reordered titles for the same underlying story, same
   source, produce the SAME fingerprint (the case Stage 12's literal
   URL hash explicitly does not catch).
3. A genuinely different story from the same source produces a
   DIFFERENT fingerprint.
4. The same title from two different sources produces DIFFERENT
   fingerprints (source still matters).
5. `extract_keywords()` strips stopwords and caps at `max_keywords`.
6. `fingerprint_candidate()` matches calling `compute_fingerprint()`
   directly with the candidate's fields.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.fingerprint import (
    compute_fingerprint,
    extract_keywords,
    fingerprint_candidate,
    normalize_source,
)
from app.services.topic_discovery import TopicCandidate


def main() -> None:
    print("1. Confirming compute_fingerprint() is deterministic...")
    fp_a = compute_fingerprint("New LLM benchmark released", "Hacker News (AI/ML)")
    fp_b = compute_fingerprint("New LLM benchmark released", "Hacker News (AI/ML)")
    assert fp_a == fp_b, "same title+source should fingerprint identically"
    print("   OK")

    print("2. Reworded/reordered title, same story+source -> SAME fingerprint...")
    fp_original = compute_fingerprint(
        "OpenAI launches GPT-5 with major reasoning upgrades", "TechCrunch"
    )
    fp_reworded = compute_fingerprint(
        "GPT-5 launches: OpenAI's major upgrades to reasoning", "TechCrunch"
    )
    assert fp_original == fp_reworded, (
        "reworded/reordered title covering the same keywords should "
        "fingerprint the same"
    )
    print("   OK — near-duplicate title variant collapses to one fingerprint")

    print("3. Genuinely different story, same source -> DIFFERENT fingerprint...")
    fp_other_story = compute_fingerprint(
        "Google ships a new open-weights vision model", "TechCrunch"
    )
    assert fp_original != fp_other_story, "different story should not collide"
    print("   OK")

    print("4. Same title, different source -> DIFFERENT fingerprint...")
    fp_diff_source = compute_fingerprint(
        "OpenAI launches GPT-5 with major reasoning upgrades", "The Verge"
    )
    assert fp_original != fp_diff_source, "source must still distinguish fingerprints"
    print("   OK")

    print("5. extract_keywords() strips stopwords and respects max_keywords...")
    kws = extract_keywords("The New Model Will Change How We Build AI Agents")
    assert "the" not in kws and "will" not in kws and "how" not in kws and "we" not in kws
    assert "model" in kws and "build" in kws and "agents" in kws
    capped = extract_keywords(
        "one two three four five six seven eight nine ten", max_keywords=3
    )
    assert len(capped) == 3, f"expected exactly 3 keywords, got {len(capped)}"
    print(f"   OK — stopwords stripped, capped list: {capped}")

    print("6. normalize_source() collapses formatting differences...")
    assert normalize_source("Hacker News (AI/ML)") == normalize_source("hackernews-ai-ml")
    print("   OK")

    print("7. fingerprint_candidate() matches compute_fingerprint() on the same fields...")
    candidate = TopicCandidate(
        title="OpenAI launches GPT-5 with major reasoning upgrades",
        url="https://example.com/gpt5",
        source_name="TechCrunch",
        category="industry",
        summary="A look at the reasoning improvements.",
    )
    fp_via_candidate = fingerprint_candidate(candidate)
    fp_via_fields = compute_fingerprint(candidate.title, candidate.source_name, candidate.summary)
    assert fp_via_candidate == fp_via_fields
    print("   OK")

    print("\nAll Stage 13 checks passed.")


if __name__ == "__main__":
    main()
