import json
import re
from pathlib import Path

TOKEN = re.compile(r"\{\{([A-Z_]+)\}\}")


def render(text: str, values: dict[str, str]) -> str:
    def substitute(match: re.Match) -> str:
        key = match.group(1).lower()
        if not values.get(key):
            raise KeyError(f"config/notion.json has no value for {key}")
        return values[key]

    return TOKEN.sub(substitute, text)


def build(source: Path, config: Path, target: Path) -> list[Path]:
    values = json.loads(config.read_text())
    written = []
    for skill in sorted(source.glob("*/SKILL.md")):
        out = target / skill.parent.name / "SKILL.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render(skill.read_text(), values))
        written.append(out)
    return written
