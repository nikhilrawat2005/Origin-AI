"""
scheduler.py — Stage 18 scope.

Chains Stages 11/12 -> 14 -> 15 -> 16 -> 17 into the single autonomous
publish cycle the PRD describes, run repeatedly by APScheduler on
`PUBLISH_INTERVAL_MINUTES`, with zero further human prompting after
`POST /api/agent/init` starts it. This is the first stage where the
full discovery -> judgment -> memory -> generation -> publish pipeline
actually executes end-to-end, rather than existing as standalone,
independently-callable functions the way Stages 12-17 deliberately
left them (each of their own docstrings says "not wired into any
route or scheduler yet — Stage 18 will chain this in").

The chain, exactly as every prior stage's docstring already described
it:

    discover_new_topics(db)                       (Stage 12)
      -> judge_candidates(...)   (accepted only)   (Stage 14)
      -> check_memory_batch(...) (not-duplicate)   (Stage 15)
      -> write_post(...)                           (Stage 16)
      -> publish_post(...)                         (Stage 17)

Design notes:

- `run_publish_cycle()` is a plain function taking a `db: Session` and
  an `Agent` — it knows nothing about APScheduler, so it stays
  directly unit-testable the same way every prior service has been,
  without needing a running scheduler or a background thread. This
  mirrors the README's own Stage 17 manual-pipeline snippet almost
  line for line — that snippet *is* this function, now made real.
- `start_scheduler()` is the only piece that knows about APScheduler.
  Its job (`_tick`) opens its own DB session per run rather than
  reusing anything request-scoped, because a `BackgroundScheduler`
  job fires on its own thread, entirely outside any FastAPI request —
  there is no `get_db()`-yielded session available to borrow. The
  session is always closed in a `finally`, the same close-in-finally
  shape `get_db()` itself uses.
- One candidate failing at post-writing (Stage 16's documented
  fail-loud `PostWriteError`) must not abort the rest of that cycle's
  survivors or crash the scheduler thread — each survivor is
  attempted independently inside its own try/except, and a single
  failure is logged and skipped.
- Every stage of the chain (discovery, judgment, memory check) is
  also wrapped at the cycle level: an uncaught exception raised
  inside an APScheduler job does not stop future ticks by itself, but
  letting exceptions escape routinely is still worth avoiding — it
  fills logs with noise and risks tripping APScheduler's own
  max-instances/misfire handling on a heavily-loaded system. Catching
  and logging here keeps every tick's intent explicit: "skip this
  cycle," never "crash."
- `start_scheduler()` is idempotent via a module-level guard.
  `POST /api/agent/init` already returns the existing agent on repeat
  calls without redoing first-call setup (Stage 4/10's own
  docstring); the scheduler must follow the same rule, or a second
  `/init` call would spin up a second, competing `BackgroundScheduler`
  running the same pipeline twice as often against the same agent.
- The first tick is scheduled to fire immediately on start (rather
  than waiting one full `PUBLISH_INTERVAL_MINUTES` for the first
  post), so the evaluator's `GET /api/agent/feed` calls after `/init`
  see the feed actually growing without an arbitrary wait — matching
  PRD Section 9's "posts appear automatically over time" rather than
  "posts appear automatically after one interval has first elapsed."
  Every tick after that first one still follows the configured
  interval exactly.
"""
import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.agent import Agent
from app.services.editorial_judgment import judge_candidates
from app.services.memory_service import check_memory_batch
from app.services.post_writer import PostWriteError, write_post
from app.services.publisher import publish_post
from app.services.sources_cache_service import (
    discover_new_topics,
    release_rejected_from_cache,
    release_unaccepted_from_cache,
)

logger = logging.getLogger(__name__)

JOB_ID = "aether-publish-cycle"

# Module-level singleton — see "idempotent via a module-level guard" above.
_scheduler: BackgroundScheduler | None = None


def run_publish_cycle(db: Session, agent: Agent) -> int:
    """Run one full discover -> judge -> memory -> write -> publish
    cycle for `agent`. Returns the number of posts actually published
    this cycle.

    Zero is an entirely normal, expected return value — most cycles
    will discover nothing new, or discover things that don't clear
    editorial judgment or memory dedup. It is not itself evidence of
    a problem.

    Every stage of the chain is wrapped so that a failure partway
    through skips the *rest of this cycle* rather than raising out of
    the function — see module docstring.
    """
    try:
        candidates = discover_new_topics(db)
    except Exception as exc:  # noqa: BLE001 - a cycle failure must not kill future ticks
        logger.error("run_publish_cycle: discovery failed, skipping this cycle: %s", exc)
        return 0

    if not candidates:
        logger.info("run_publish_cycle: no new candidates this cycle.")
        return 0

    try:
        # Cap judgment at 5 accepted candidates per cycle for fast response & steady batching
        judgments = judge_candidates(db, agent.id, candidates, max_accepts=5)
    except Exception as exc:  # noqa: BLE001
        logger.error("run_publish_cycle: editorial judgment failed, skipping this cycle: %s", exc)
        return 0

    accepted = [j for j in judgments if j.accepted]
    accepted_urls = {j.candidate.url for j in accepted}
    unaccepted = [c for c in candidates if c.url not in accepted_urls]

    # Free all unaccepted URLs (both explicitly rejected AND unevaluated candidates
    # skipped due to max_accepts) from sources_cache so they re-enter the pool next cycle.
    # Published URLs (accepted below) stay locked for 24h via CACHE_TTL_HOURS.
    # RejectedTopic fingerprints will fast-reject same-story variants on
    # re-evaluation with zero LLM calls, so this doesn't cause redundant API spend.
    if unaccepted:
        try:
            release_unaccepted_from_cache(db, unaccepted)
        except Exception as exc:  # noqa: BLE001
            logger.warning("run_publish_cycle: cache release failed (non-fatal): %s", exc)

    if not accepted:
        logger.info(
            "run_publish_cycle: %d candidate(s) discovered, none accepted.",
            len(candidates),
        )
        return 0

    try:
        memory_results = check_memory_batch(db, agent, [j.candidate for j in accepted])
    except Exception as exc:  # noqa: BLE001
        logger.error("run_publish_cycle: memory check failed, skipping this cycle: %s", exc)
        return 0

    survivors = [j for j, m in zip(accepted, memory_results) if not m.is_duplicate]
    if not survivors:
        logger.info(
            "run_publish_cycle: %d accepted, all flagged as already-published duplicates.",
            len(accepted),
        )
        return 0

    published_count = 0
    for judgment in survivors:
        try:
            written = write_post(judgment)
            publish_post(db, agent, written)
        except PostWriteError as exc:
            # Stage 16's documented fail-loud mode — one bad generation
            # must not abort the rest of this cycle's survivors.
            logger.warning(
                "run_publish_cycle: post writing failed for %r, skipping: %s",
                judgment.candidate.title,
                exc,
            )
        except Exception as exc:  # noqa: BLE001 - publishing itself failing is unexpected but must not kill the cycle
            logger.error(
                "run_publish_cycle: publishing failed for %r, skipping: %s",
                judgment.candidate.title,
                exc,
            )
        else:
            published_count += 1
            logger.info("run_publish_cycle: published %r", written.title)

    return published_count


def _tick(agent_id: str) -> None:
    """One scheduler tick. Opens its own DB session (see module
    docstring on why a request-scoped session can't be reused here),
    re-fetches the agent fresh rather than closing over a stale
    object, and always closes the session.
    """
    db = SessionLocal()
    try:
        agent = db.query(Agent).filter_by(id=agent_id).first()
        if agent is None:
            logger.error("scheduler tick: agent %s no longer exists, skipping.", agent_id)
            return
        run_publish_cycle(db, agent)
    except Exception as exc:  # noqa: BLE001 - an uncaught exception here would surface as an
        # APScheduler executor error and, depending on misfire/error-count
        # config, can eventually suspend the job entirely — the whole
        # point of an autonomous scheduler is that a bad tick doesn't
        # end the loop, so this is caught and logged, never re-raised.
        logger.error("scheduler tick: unexpected error for agent %s: %s", agent_id, exc)
    finally:
        db.close()


def start_scheduler(agent_id: str) -> BackgroundScheduler:
    """Start the background scheduler for `agent_id`, idempotently.

    A repeat call (e.g. a second `POST /api/agent/init`, which Stage
    4/10 already made safe against duplicate agent rows) returns the
    already-running scheduler untouched instead of starting a second,
    competing one against the same agent.
    """
    global _scheduler
    if _scheduler is not None:
        logger.info("start_scheduler: scheduler already running, ignoring repeat start.")
        return _scheduler

    settings = get_settings()
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        _tick,
        trigger="interval",
        minutes=settings.publish_interval_minutes,
        args=[agent_id],
        id=JOB_ID,
        next_run_time=datetime.now(),  # fire immediately, then every interval — see module docstring
    )
    scheduler.start()
    _scheduler = scheduler
    logger.info(
        "start_scheduler: started for agent %s, running every %d minute(s), first tick immediately.",
        agent_id,
        settings.publish_interval_minutes,
    )
    return scheduler


def stop_scheduler() -> None:
    """Stop the running scheduler, if any, and clear the module-level
    guard. Used by app shutdown and by tests that need a clean slate
    between runs — without this, a test starting a second scheduler
    in the same process would silently be a no-op against the first.
    """
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("stop_scheduler: stopped.")


def is_running() -> bool:
    """Whether a scheduler is currently active in this process."""
    return _scheduler is not None


def get_next_run_time() -> str | None:
    """Return the ISO timestamp of the next scheduled publish cycle, if scheduler is running."""
    if _scheduler is None:
        return None
    job = _scheduler.get_job(JOB_ID)
    if job and job.next_run_time:
        return job.next_run_time.isoformat()
    return None
