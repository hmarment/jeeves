# jeeves

- `src/jeeves/` is pure and deterministic: snapshot JSON in, plan JSON out. No network or
  connector calls here.
- `routines/` holds prompts for scheduled agents; they read IDs and secrets from env vars.
- Never commit task data, snapshots, IDs or secrets — this repo is public.

## Commands
- `mise install && uv sync`
- `uv run pytest -q`
- `uv run ruff check . && uv run ruff format .`
