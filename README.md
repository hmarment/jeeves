# jeeves

A small, deterministic planning core for a personal-assistant agent. It takes a JSON
snapshot of tasks, calendar events and preferences, and returns a plan: which tasks to do
today, focus blocks to book, which task fields to tidy, and what needs a human decision.
All I/O (task store, calendar, chat) is done by the agent that calls it.

```bash
uv run jeeves decide snapshot.json   # daily plan
uv run jeeves reset snapshot.json    # one-off backlog reset proposal
uv run pytest
```

The `routines/` folder holds the prompts the scheduled agent follows.
