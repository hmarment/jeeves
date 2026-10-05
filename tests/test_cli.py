import json

from jeeves.cli import main
from tests.factories import make_snapshot, make_task


def test_decide_prints_plan_json(tmp_path, capsys):
    path = tmp_path / "snapshot.json"
    path.write_text(make_snapshot([make_task()]).model_dump_json())
    assert main(["decide", str(path)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "planned"


def test_invalid_snapshot_exits_nonzero_with_message(tmp_path, capsys):
    path = tmp_path / "snapshot.json"
    path.write_text('{"now": "2026-10-07T07:30:00", "tasks": []}')
    assert main(["decide", str(path)]) == 2
    assert "timezone-aware" in capsys.readouterr().err


def test_reset_prints_proposal_json(tmp_path, capsys):
    path = tmp_path / "snapshot.json"
    path.write_text(make_snapshot([make_task()]).model_dump_json())
    assert main(["reset", str(path)]) == 0
    assert "changes" in json.loads(capsys.readouterr().out)


def test_snapshot_command_writes_valid_snapshot(tmp_path, capsys):
    page = {
        "id": "p1",
        "created_time": "2026-09-01T10:00:00.000Z",
        "last_edited_time": "2026-10-01T10:00:00.000Z",
        "properties": {"Task name": "Write report", "Status": "Not Started"},
    }
    files = {
        "tasks.json": {"pages": [page]},
        "plan.json": {"pages": []},
        "events.json": [],
        "inferences.json": {"p1": {"size": "S"}},
    }
    for name, content in files.items():
        (tmp_path / name).write_text(json.dumps(content))
    (tmp_path / "prefs.txt").write_text('```json\n{"mode": "auto"}\n```')
    args = [
        "snapshot",
        "--tasks",
        str(tmp_path / "tasks.json"),
        "--daily-plan",
        str(tmp_path / "plan.json"),
        "--events",
        str(tmp_path / "events.json"),
        "--prefs",
        str(tmp_path / "prefs.txt"),
        "--inferences",
        str(tmp_path / "inferences.json"),
        "--now",
        "2026-10-07T07:30:00+02:00",
    ]
    assert main(args) == 0
    snapshot = json.loads(capsys.readouterr().out)
    assert snapshot["prefs"]["mode"] == "auto"
    assert snapshot["inferences"]["p1"]["size"] == "S"
