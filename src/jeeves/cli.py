import argparse
import sys
from pathlib import Path

from pydantic import ValidationError

from jeeves.model import Snapshot
from jeeves.plan import decide
from jeeves.reset import propose_reset
from jeeves.skills_build import build

COMMANDS = {"decide": decide, "reset": propose_reset}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="jeeves")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in COMMANDS:
        commands.add_parser(name).add_argument("snapshot", type=Path)
    commands.add_parser("build-skills")
    args = parser.parse_args(argv)
    if args.command == "build-skills":
        for path in build(
            Path("skills"), Path("config/notion.json"), Path("dist/skills")
        ):
            print(path)
        return 0
    try:
        snapshot = Snapshot.model_validate_json(args.snapshot.read_text())
    except ValidationError as error:
        print(error, file=sys.stderr)
        return 2
    print(COMMANDS[args.command](snapshot).model_dump_json(indent=2))
    return 0
