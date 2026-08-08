"""
Standalone verification script for Stage 5 — Persona Bible + Prompt Builder.

Run with:  python -m scripts.test_persona   (from backend/)

Checks:
1. persona.json loads and parses.
2. Every field the prompt builder depends on is present.
3. build_voice_profile_prompt() runs and produces non-empty text that
   contains the persona name, at least one voice trait, and the sample
   voice line — a cheap sanity check that nothing was silently dropped.
4. get_persona_name() returns the expected value.

No LLM calls, no network access, no database — this stage is pure
local logic.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.persona_service import (  # noqa: E402
    load_persona,
    build_voice_profile_prompt,
    get_persona_name,
)

REQUIRED_FIELDS = [
    "name", "tagline", "description", "tone", "voice_traits",
    "editorial_values", "topics_of_interest", "topics_avoided",
    "sourcing_standards", "writing_style_rules", "sample_voice",
]


def main() -> None:
    print("1. Loading persona.json...")
    persona = load_persona()
    print(f"   OK — persona name: {persona['name']}")

    print("2. Checking required fields...")
    missing = [f for f in REQUIRED_FIELDS if f not in persona]
    assert not missing, f"Missing fields in persona.json: {missing}"
    print(f"   OK — all {len(REQUIRED_FIELDS)} required fields present")

    print("3. Building voice profile prompt...")
    prompt = build_voice_profile_prompt(persona)
    assert len(prompt) > 200, "Prompt looks too short — something's missing"
    assert persona["name"] in prompt
    assert persona["voice_traits"][0] in prompt
    assert persona["sample_voice"] in prompt
    print(f"   OK — prompt built, {len(prompt)} chars")
    print("   --- preview (first 300 chars) ---")
    print("   " + prompt[:300].replace("\n", "\n   "))
    print("   ...")

    print("4. Checking get_persona_name()...")
    name = get_persona_name()
    assert name == persona["name"]
    print(f"   OK — get_persona_name() == '{name}'")

    print("\nAll Stage 5 persona checks passed.")


if __name__ == "__main__":
    main()
