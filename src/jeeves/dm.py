from datetime import date

from jeeves.model import Task


def render_dm(
    day: date, focus: int, first: Task | None, queue_size: int, over_capacity: int
) -> str:
    lines = [
        f"☀️ Plan for {day:%a %d %b} is ready: {focus // 60}h{focus % 60:02d} focus time."
    ]
    if first is not None:
        lines.append(f"First must-do: {first.title}")
    if queue_size:
        plural = "s" if queue_size != 1 else ""
        lines.append(f"{queue_size} decision{plural} waiting.")
    if over_capacity:
        lines.append(f"⚠️ Over capacity by {over_capacity} min.")
    lines.append("Run /start-day when you're ready.")
    return "\n".join(lines)
