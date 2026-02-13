"""Cron types."""

from typing import Literal


class CronSchedule:
    """Schedule definition for a cron job."""

    __slots__ = ("kind", "at_ms", "every_ms", "expr", "tz")

    def __init__(
        self,
        kind: Literal["at", "every", "cron"],
        at_ms: int | None = None,
        every_ms: int | None = None,
        expr: str | None = None,
        tz: str | None = None,
    ):
        self.kind = kind
        self.at_ms = at_ms
        self.every_ms = every_ms
        self.expr = expr
        self.tz = tz


class CronPayload:
    """What to do when the job runs."""

    __slots__ = ("kind", "message", "deliver", "channel", "to")

    def __init__(
        self,
        kind: Literal["system_event", "agent_turn"] = "agent_turn",
        message: str = "",
        deliver: bool = False,
        channel: str | None = None,
        to: str | None = None,
    ):
        self.kind = kind
        self.message = message
        self.deliver = deliver
        self.channel = channel
        self.to = to


class CronJobState:
    """Runtime state of a job."""

    __slots__ = ("next_run_at_ms", "last_run_at_ms", "last_status", "last_error")

    def __init__(
        self,
        next_run_at_ms: int | None = None,
        last_run_at_ms: int | None = None,
        last_status: Literal["ok", "error", "skipped"] | None = None,
        last_error: str | None = None,
    ):
        self.next_run_at_ms = next_run_at_ms
        self.last_run_at_ms = last_run_at_ms
        self.last_status = last_status
        self.last_error = last_error


class CronJob:
    """A scheduled job."""

    __slots__ = (
        "id",
        "name",
        "enabled",
        "schedule",
        "payload",
        "state",
        "created_at_ms",
        "updated_at_ms",
        "delete_after_run",
    )

    def __init__(
        self,
        id: str,
        name: str,
        enabled: bool = True,
        schedule: CronSchedule | None = None,
        payload: CronPayload | None = None,
        state: CronJobState | None = None,
        created_at_ms: int = 0,
        updated_at_ms: int = 0,
        delete_after_run: bool = False,
    ):
        self.id = id
        self.name = name
        self.enabled = enabled
        self.schedule = schedule if schedule is not None else CronSchedule(kind="every")
        self.payload = payload if payload is not None else CronPayload()
        self.state = state if state is not None else CronJobState()
        self.created_at_ms = created_at_ms
        self.updated_at_ms = updated_at_ms
        self.delete_after_run = delete_after_run


class CronStore:
    """Persistent store for cron jobs."""

    __slots__ = ("version", "jobs")

    def __init__(self, version: int = 1, jobs: list | None = None):
        self.version = version
        self.jobs = list(jobs) if jobs is not None else []
