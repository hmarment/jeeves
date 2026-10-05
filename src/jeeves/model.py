from __future__ import annotations

from datetime import date, datetime, time
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, field_validator

Size = Literal["S", "M", "L"]
DeadlineType = Literal["Hard", "Soft"]
Area = Literal["Work", "Personal"]
FieldValue = date | bool | int | str | None

BERLIN = ZoneInfo("Europe/Berlin")
PROTECTED_PREFIXES = ("90 |", "JIRA |")
PARKED_STATUS = "Backlog"
OPEN_STATUSES = frozenset({"Backlog", "Not Started", "Today", "In Progress", "Pending"})
SELECTABLE_STATUSES = frozenset({"Not Started", "Today", "In Progress"})


def _require_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("datetimes must be timezone-aware (Europe/Berlin)")
    return value.astimezone(BERLIN)


class Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Task(Frozen):
    id: str
    title: str
    status: str
    created: date
    last_edited: date
    due: date | None = None
    original_due: date | None = None
    priority: str | None = None
    size: Size | None = None
    deadline_type: DeadlineType | None = None
    area: Area | None = None
    confidential: bool = False
    deferrals: int = 0
    last_deferred: date | None = None
    planned_by_pa: date | None = None
    rock_linked: bool = False

    @property
    def is_open(self) -> bool:
        return self.status in OPEN_STATUSES

    @property
    def is_protected(self) -> bool:
        return self.title.startswith(PROTECTED_PREFIXES)

    @property
    def effective_deadline_type(self) -> DeadlineType | None:
        return "Hard" if self.is_protected else self.deadline_type

    @property
    def is_manual_today(self) -> bool:
        return self.status == "Today" and self.planned_by_pa is None

    @property
    def needs_inference(self) -> bool:
        return self.area is None or self.size is None or self.deadline_type is None


class CalendarEvent(Frozen):
    id: str
    title: str
    start: datetime
    end: datetime
    all_day: bool = False
    pa_created: bool = False
    out_of_office: bool = False

    @field_validator("start", "end")
    @classmethod
    def _aware(cls, value: datetime) -> datetime:
        return _require_aware(value)


class Preferences(Frozen):
    mode: Literal["propose-only", "auto"] = "propose-only"
    work_start: time = time(9, 0)
    work_end: time = time(17, 30)
    meeting_buffer_minutes: int = 10
    min_block_minutes: int = 30
    size_minutes: dict[str, int] = {"S": 15, "M": 90}
    work_must_dos: int = 3
    personal_must_dos: int = 1
    quick_wins_minutes: int = 30
    quick_wins_start: time = time(13, 30)
    deferral_limit: int = 3
    queue_cap: int = 5
    stale_days: int = 45
    recent_soft_days: int = 30
    week_ahead_working_days: int = 5
    ooo_keywords: list[str] = ["OOO", "Out of office", "Holiday", "Urlaub", "Vacation"]
    confidential_keywords: list[str] = [
        "hiring",
        "salary",
        "compensation",
        "performance review",
        "restructure",
        "legal",
        "contract",
        "termination",
    ]


class DailyPlanState(Frozen):
    day: date
    must_do_ids: list[str] = []
    quick_win_ids: list[str] = []
    ritual_done: bool = False
    shutdown_done: bool = False
    must_dos_completed: int | None = None


class Inference(Frozen):
    area: Area | None = None
    size: Size | None = None
    deadline_type: DeadlineType | None = None
    confidential: bool | None = None
    duplicate_of: str | None = None
    duplicate_certain: bool = False


class Snapshot(Frozen):
    now: datetime
    prefs: Preferences = Preferences()
    tasks: list[Task]
    events: list[CalendarEvent] = []
    yesterday_plan: DailyPlanState | None = None
    today_plan: DailyPlanState | None = None
    inferences: dict[str, Inference] = {}

    @field_validator("now")
    @classmethod
    def _aware(cls, value: datetime) -> datetime:
        return _require_aware(value)

    @property
    def today(self) -> date:
        return self.now.date()


class FieldChange(Frozen):
    task_id: str
    field: str
    old: FieldValue
    new: FieldValue
    reason: str


class BlockCreate(Frozen):
    task_id: str | None
    start: datetime
    end: datetime
    title: str
    private: bool


class BlockDelete(Frozen):
    event_id: str
    reason: str


class PlanResult(Frozen):
    status: Literal["planned", "skipped", "locked"]
    reason: str = ""
    focus_minutes: int = 0
    must_do_ids: list[str] = []
    quick_win_ids: list[str] = []
    queue_ids: list[str] = []
    changes: list[FieldChange] = []
    blocks_create: list[BlockCreate] = []
    blocks_delete: list[BlockDelete] = []
    over_capacity_minutes: int = 0
    hard_overdue_count: int = 0
    deferral_limit_count: int = 0
    yesterday_completed: int | None = None
    dm_text: str = ""


class ResetProposal(Frozen):
    changes: list[FieldChange]
    uninferred_ids: list[str] = []


def change(task: Task, field: str, new: FieldValue, reason: str) -> FieldChange:
    return FieldChange(
        task_id=task.id, field=field, old=getattr(task, field), new=new, reason=reason
    )


def apply_changes(tasks: list[Task], changes: list[FieldChange]) -> list[Task]:
    by_id = {task.id: task for task in tasks}
    for item in changes:
        by_id[item.task_id] = by_id[item.task_id].model_copy(
            update={item.field: item.new}
        )
    return [by_id[task.id] for task in tasks]
