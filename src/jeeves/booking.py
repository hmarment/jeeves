from datetime import datetime, timedelta

from jeeves.model import BlockCreate, Preferences, Task
from jeeves.selection import minutes_for
from jeeves.workday import Interval

QUICK_WINS_TITLE = "🎯 Quick wins"


def block_title(task: Task) -> str:
    return "🎯 Focus block" if task.confidential else f"🎯 Focus: {task.title}"


def _take(
    free: list[Interval],
    needed: timedelta,
    minimum: timedelta,
    not_before: datetime | None = None,
) -> Interval | None:
    for index, (start, end) in enumerate(free):
        begin = max(start, not_before) if not_before else start
        if end - begin < minimum:
            continue
        finish = min(begin + needed, end)
        free[index : index + 1] = [
            (s, e) for s, e in ((start, begin), (finish, end)) if e > s
        ]
        return begin, finish
    return None


def plan_blocks(
    must_dos: list[Task],
    quick_wins: bool,
    intervals: list[Interval],
    now: datetime,
    prefs: Preferences,
) -> list[BlockCreate]:
    free = list(intervals)
    minimum = timedelta(minutes=prefs.min_block_minutes)
    blocks = []
    if quick_wins:
        length = timedelta(minutes=prefs.quick_wins_minutes)
        preferred = datetime.combine(now.date(), prefs.quick_wins_start, now.tzinfo)
        slot = _take(free, length, minimum, preferred) or _take(free, length, minimum)
        if slot:
            blocks.append(
                BlockCreate(
                    task_id=None,
                    start=slot[0],
                    end=slot[1],
                    title=QUICK_WINS_TITLE,
                    private=False,
                )
            )
    for task in must_dos:
        if task.area == "Personal":
            continue
        needed = timedelta(minutes=minutes_for(task, prefs))
        slot = _take(free, needed, minimum)
        if slot:
            blocks.append(
                BlockCreate(
                    task_id=task.id,
                    start=slot[0],
                    end=slot[1],
                    title=block_title(task),
                    private=task.confidential,
                )
            )
    return blocks
