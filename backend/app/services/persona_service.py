"""
Persona service — Stage 5 scope only.

Loads the static persona bible (app/core/persona.json) and turns it into
a single reusable prompt string: the "voice profile." This is the text
every future LLM call (editorial judgment in Stage 14, post writing in
Stage 16, etc.) will be seeded with so Aether's voice stays consistent
across every call and every provider.

No LLM call happens here. Stage 6 builds the LLMProvider interface;
Stage 8 is the first place this voice profile actually gets sent to a
model, when /init generates and stores the agent's persona description.
"""
import json
from functools import lru_cache
from pathlib import Path

PERSONA_FILE = Path(__file__).resolve().parent.parent / "core" / "persona.json"


@lru_cache
def load_persona() -> dict:
    """Read and cache the persona bible from disk.

    Cached because this file never changes at runtime — it's a static
    editorial identity, not per-agent state. Per-agent state (the LLM's
    *generated* voice profile / persona_description) lives in the Agent
    row, not here.
    """
    with open(PERSONA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def build_voice_profile_prompt(persona: dict | None = None) -> str:
    """Flatten the persona bible into a single system-prompt-ready string.

    Kept as plain formatted text (not raw JSON) because it will be
    handed directly to an LLM as instructions — models follow prose
    instructions more reliably than they follow a JSON blob asked to
    be "interpreted." Every persona.json field is represented here, in
    the same order the bible defines them, so nothing is silently
    dropped if the bible grows.
    """
    p = persona if persona is not None else load_persona()

    lines: list[str] = []
    lines.append(f"You are {p['name']}. {p['tagline']}")
    lines.append("")
    lines.append(p["description"])
    lines.append("")

    lines.append(f"Tone: {p['tone']['primary']}.")
    lines.append("Avoid: " + ", ".join(p["tone"]["avoid"]) + ".")
    lines.append("")

    lines.append("Voice traits:")
    for trait in p["voice_traits"]:
        lines.append(f"- {trait}")
    lines.append("")

    lines.append("Editorial values:")
    for value in p["editorial_values"]:
        lines.append(f"- {value}")
    lines.append("")

    lines.append("Topics of interest:")
    for topic in p["topics_of_interest"]:
        lines.append(f"- {topic}")
    lines.append("")

    lines.append("Topics to avoid:")
    for topic in p["topics_avoided"]:
        lines.append(f"- {topic}")
    lines.append("")

    src = p["sourcing_standards"]
    lines.append(
        f"Sourcing standards: require at least {src['minimum_sources']} "
        f"source(s). Prefer: {', '.join(src['preferred_source_types'])}. "
        f"Never rely on: {', '.join(src['disallowed_source_types'])}."
    )
    lines.append("")

    lines.append("Writing style rules:")
    for rule in p["writing_style_rules"]:
        lines.append(f"- {rule}")
    lines.append("")

    lines.append(f"Example of the voice: \"{p['sample_voice']}\"")

    return "\n".join(lines)


def get_persona_name() -> str:
    """Convenience accessor — the one field Stage 8 needs immediately
    to seed Agent.persona_name without pulling in the full prompt."""
    return load_persona()["name"]
