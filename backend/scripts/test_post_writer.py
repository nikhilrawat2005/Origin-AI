"""
Stage 16 verification — Post Writer.

Runs with a `ScriptedProvider` (no network, no real API key needed),
following the same pattern as Stage 14's `test_editorial_judgment.py`.
Confirms:
1. A well-formed TITLE/RATIONALE/CONTENT response is parsed correctly
   into a `WrittenPost`, with `sources == [candidate.url]` and the
   original judgment's fingerprint carried through.
2. A response missing a required marker raises `PostWriteError`.
3. A response with sections out of order raises `PostWriteError`.
4. A response with an empty section (e.g. `CONTENT:` with nothing
   after it) raises `PostWriteError`.
5. A provider exception during generate() raises `PostWriteError`
   without leaking the original exception type.
6. Calling `write_post()` with a *rejected* `JudgmentResult` raises
   `PostWriteError` immediately, without calling the provider at all.
7. An empty response string raises `PostWriteError`.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.editorial_judgment import JudgmentResult  # noqa: E402
from app.services.post_writer import PostWriteError, write_post  # noqa: E402
from app.services.topic_discovery import TopicCandidate  # noqa: E402


class _CallCounter:
    calls = 0


class ScriptedProvider:
    """Fake LLMProvider whose generate() returns a pre-scripted
    sequence of responses, one per call.
    """

    name = "scripted"

    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    def generate(self, prompt: str, system: str | None = None) -> str:
        _CallCounter.calls += 1
        return self._responses.pop(0)

    def judge(self, prompt: str, system: str | None = None) -> str:
        raise NotImplementedError

    def summarize(self, text: str, system: str | None = None) -> str:
        raise NotImplementedError


class RaisingProvider:
    """Fake LLMProvider whose generate() always raises."""

    name = "raising"

    def generate(self, prompt: str, system: str | None = None) -> str:
        _CallCounter.calls += 1
        raise RuntimeError("simulated provider outage")

    def judge(self, prompt: str, system: str | None = None) -> str:
        raise NotImplementedError

    def summarize(self, text: str, system: str | None = None) -> str:
        raise NotImplementedError


def make_candidate(title="OpenAI ships a new reasoning benchmark",
                    url="https://example.com/story", source_name="TechCrunch"):
    return TopicCandidate(title=title, url=url, source_name=source_name, category="industry")


def make_accepted_judgment(candidate=None, reason="Verifiable primary-source release, on-topic."):
    candidate = candidate or make_candidate()
    return JudgmentResult(
        candidate=candidate, fingerprint="fp-123", accepted=True, reason=reason
    )


def make_rejected_judgment(candidate=None, reason="Not on-topic."):
    candidate = candidate or make_candidate()
    return JudgmentResult(
        candidate=candidate, fingerprint="fp-456", accepted=False, reason=reason
    )


WELL_FORMED = (
    "TITLE: New Benchmark Puts Reasoning Claims to the Test\n"
    "RATIONALE: Primary-source release with reproducible numbers, though "
    "the benchmark itself is narrow.\n"
    "CONTENT:\n"
    "OpenAI released a new reasoning benchmark this week, according to "
    "the release notes. Early results show modest gains over prior "
    "methods.\n\n"
    "This matters because it gives researchers a concrete, if narrow, "
    "yardstick for reasoning progress."
)


def main() -> None:
    print("1. Well-formed response parses into a WrittenPost...")
    judgment = make_accepted_judgment()
    provider = ScriptedProvider([WELL_FORMED])
    post = write_post(judgment, llm_provider=provider)
    assert post.title == "New Benchmark Puts Reasoning Claims to the Test"
    assert "Primary-source release" in post.rationale
    assert post.content.startswith("OpenAI released a new reasoning benchmark")
    assert post.sources == [judgment.candidate.url]
    assert post.fingerprint == judgment.fingerprint
    print("   OK")

    print("2. Response missing a required marker raises PostWriteError...")
    provider2 = ScriptedProvider(["TITLE: Only a title, nothing else."])
    try:
        write_post(make_accepted_judgment(), llm_provider=provider2)
        assert False, "expected PostWriteError"
    except PostWriteError as exc:
        assert "missing required section markers" in str(exc)
    print("   OK")

    print("3. Sections out of order raises PostWriteError...")
    out_of_order = "CONTENT:\nBody first.\nTITLE: Title second\nRATIONALE: Rationale third"
    provider3 = ScriptedProvider([out_of_order])
    try:
        write_post(make_accepted_judgment(), llm_provider=provider3)
        assert False, "expected PostWriteError"
    except PostWriteError as exc:
        assert "out of order" in str(exc)
    print("   OK")

    print("4. Empty CONTENT section raises PostWriteError...")
    empty_content = "TITLE: A Title\nRATIONALE: A rationale.\nCONTENT:\n   "
    provider4 = ScriptedProvider([empty_content])
    try:
        write_post(make_accepted_judgment(), llm_provider=provider4)
        assert False, "expected PostWriteError"
    except PostWriteError as exc:
        assert "empty CONTENT section" in str(exc)
    print("   OK")

    print("5. Provider exception raises PostWriteError, not the raw exception...")
    try:
        write_post(make_accepted_judgment(), llm_provider=RaisingProvider())
        assert False, "expected PostWriteError"
    except PostWriteError as exc:
        assert "generation call failed" in str(exc)
    print("   OK — no raw RuntimeError leaked")

    print("6. Rejected JudgmentResult raises immediately, no provider call...")
    _CallCounter.calls = 0
    provider6 = ScriptedProvider(["TITLE: should never be reached\nRATIONALE: x\nCONTENT:\nx"])
    try:
        write_post(make_rejected_judgment(), llm_provider=provider6)
        assert False, "expected PostWriteError"
    except PostWriteError as exc:
        assert "rejected JudgmentResult" in str(exc)
    assert _CallCounter.calls == 0, "provider should never be called for a rejected judgment"
    print("   OK — no LLM call made")

    print("7. Empty response string raises PostWriteError...")
    provider7 = ScriptedProvider([""])
    try:
        write_post(make_accepted_judgment(), llm_provider=provider7)
        assert False, "expected PostWriteError"
    except PostWriteError as exc:
        assert "empty response" in str(exc)
    print("   OK")

    print("\nAll Stage 16 checks passed.")


if __name__ == "__main__":
    main()
