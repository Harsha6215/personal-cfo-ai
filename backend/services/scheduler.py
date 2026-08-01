"""
Data Refresh Engine — Story 3.9

Background scheduler that refreshes market data at different rates:
  - Prices: configurable (default every 5 min during market hours)
  - Company info: weekly
  - News: every 10 min
  - Economic indicators: hourly

Uses a simple async loop approach (production would use APScheduler or Celery).
Started via FastAPI lifespan events.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

import structlog

logger = structlog.get_logger(__name__)


class JobStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    FAILED = "failed"


@dataclass
class ScheduledJob:
    name: str
    interval_seconds: int
    status: JobStatus = JobStatus.IDLE
    last_run: datetime | None = None
    last_duration_ms: int | None = None
    run_count: int = 0
    error_count: int = 0
    last_error: str | None = None


class DataRefreshScheduler:
    """
    Manages background data refresh jobs.

    Usage:
        scheduler = DataRefreshScheduler()
        scheduler.register("prices", interval=300, func=refresh_prices)
        await scheduler.start()  # call in FastAPI startup
        await scheduler.stop()   # call in FastAPI shutdown
    """

    def __init__(self):
        self.jobs: dict[str, ScheduledJob] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._running = False
        self._functions: dict[str, callable] = {}

    def register(self, name: str, interval_seconds: int, func) -> None:
        """Register a job to run on a schedule."""
        self.jobs[name] = ScheduledJob(name=name, interval_seconds=interval_seconds)
        self._functions[name] = func
        logger.info("scheduler.registered", job=name, interval=interval_seconds)

    async def start(self) -> None:
        """Start all scheduled jobs as background tasks."""
        if self._running:
            return
        self._running = True
        for name in self.jobs:
            self._tasks[name] = asyncio.create_task(self._run_loop(name))
        logger.info("scheduler.started", jobs=list(self.jobs.keys()))

    async def stop(self) -> None:
        """Stop all background tasks."""
        self._running = False
        for task in self._tasks.values():
            task.cancel()
        self._tasks.clear()
        logger.info("scheduler.stopped")

    async def _run_loop(self, name: str) -> None:
        """Run a single job in a loop."""
        job = self.jobs[name]
        func = self._functions[name]

        # Wait a bit before first run to let the app fully start
        await asyncio.sleep(5)

        while self._running:
            try:
                job.status = JobStatus.RUNNING
                start = datetime.now(timezone.utc)

                await func()

                duration = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)
                job.status = JobStatus.IDLE
                job.last_run = datetime.now(timezone.utc)
                job.last_duration_ms = duration
                job.run_count += 1
                job.last_error = None

                logger.debug("scheduler.job.completed", job=name, duration_ms=duration, run=job.run_count)

            except asyncio.CancelledError:
                break
            except Exception as e:
                job.status = JobStatus.FAILED
                job.error_count += 1
                job.last_error = str(e)
                logger.warning("scheduler.job.failed", job=name, error=str(e))

            # Wait for next interval
            await asyncio.sleep(job.interval_seconds)

    def get_status(self) -> list[dict]:
        """Get status of all jobs."""
        return [
            {
                "name": job.name,
                "interval_seconds": job.interval_seconds,
                "status": job.status.value,
                "last_run": job.last_run.isoformat() if job.last_run else None,
                "last_duration_ms": job.last_duration_ms,
                "run_count": job.run_count,
                "error_count": job.error_count,
                "last_error": job.last_error,
            }
            for job in self.jobs.values()
        ]


# ── Global scheduler instance ─────────────────────────────────────────────────
scheduler = DataRefreshScheduler()


# ── Placeholder refresh functions (to be expanded) ─────────────────────────────

async def refresh_placeholder():
    """Placeholder — in production, this refreshes cached data."""
    pass


# Register default jobs
scheduler.register("asset_enrichment", interval_seconds=3600, func=refresh_placeholder)  # hourly
scheduler.register("news_refresh", interval_seconds=600, func=refresh_placeholder)       # 10 min
scheduler.register("economy_refresh", interval_seconds=3600, func=refresh_placeholder)   # hourly
