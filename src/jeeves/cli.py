import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from jeeves.model import Snapshot
from jeeves.plan import decide
from jeeves.reset import propose_reset
from jeeves.skills_build import build
from jeeves.snapshot import build_snapshot

COMMANDS = {"decide": decide, "reset": propose_reset}


def _load(path: Path):
    text = path.read_text()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _snapshot(args: argparse.Namespace) -> int:
    try:
        snapshot = build_snapshot(
            tasks_payload=_load(args.tasks),
            plan_payload=_load(args.daily_plan),
            events_payload=_load(args.events),
            prefs_payload=_load(args.prefs),
            now=args.now,
            inferences_payload=_load(args.inferences) if args.inferences else None,
        )
    except (ValidationError, ValueError, KeyError) as error:
        print(error, file=sys.stderr)
        return 2
    print(snapshot.model_dump_json(indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="jeeves")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in COMMANDS:
        commands.add_parser(name).add_argument("snapshot", type=Path)
    commands.add_parser("build-skills")
    snapshot_parser = commands.add_parser("snapshot")
    for flag in ("--tasks", "--daily-plan", "--events", "--prefs"):
        snapshot_parser.add_argument(flag, type=Path, required=True)
    snapshot_parser.add_argument("--inferences", type=Path)
    snapshot_parser.add_argument("--now", required=True)
    args = parser.parse_args(argv)
    if args.command == "build-skills":
        for path in build(
            Path("skills"), Path("config/notion.json"), Path("dist/skills")
        ):
            print(path)
        return 0
    if args.command == "snapshot":
        return _snapshot(args)
    try:
        snapshot = Snapshot.model_validate_json(args.snapshot.read_text())
    except ValidationError as error:
        print(error, file=sys.stderr)
        return 2
    print(COMMANDS[args.command](snapshot).model_dump_json(indent=2))
    return 0
