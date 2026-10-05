# Building snapshot.json

Work in the cloned `jeeves` repo. All files go in `/tmp/jeeves/` (never commit them).

1. `read_preferences()` → `/tmp/jeeves/prefs.txt`.
2. `read_daily_plan(dates)` for today and the previous 7 days (Europe/Berlin) →
   `/tmp/jeeves/plan.json`. Collect the task ids in Must-dos / Quick wins of those rows.
3. `read_tasks(["Backlog","Not Started","Today","In Progress","Pending"], extra_ids)` with
   the ids from step 2 → `/tmp/jeeves/tasks.json` (or the connector's saved file).
4. Google Calendar `list_events` on the primary calendar from today 00:00 to today + 8 days
   24:00, Europe/Berlin → write the raw event objects as a JSON list to
   `/tmp/jeeves/events.json`. Each needs `id`, `summary`, `start`, `end` (as Google returns
   them: `{"dateTime": …}` or `{"date": …}`), and when present `description`, `eventType`,
   `transparency`, `attendees` (with `self` and `responseStatus`). `jeeves snapshot` drops
   declined and free events and detects `[jeeves]` blocks and out-of-office itself.
5. Inferences → `/tmp/jeeves/inferences.json` (rules below).
6. ```bash
   uv run jeeves snapshot --tasks /tmp/jeeves/tasks.json --daily-plan /tmp/jeeves/plan.json \
     --events /tmp/jeeves/events.json --prefs /tmp/jeeves/prefs.txt \
     --inferences /tmp/jeeves/inferences.json --now "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
     > /tmp/jeeves/snapshot.json
   ```
   Exit code 2 = invalid input: read the error, fix the input file once, retry.

## Inferences
Write a JSON object `{task_id: {...}}` for every open task whose Area, Size or Deadline type
is empty, and for duplicate checks on tasks created since the previous working day. To find
them without reading the whole file into your context, use a short `jq`/Python filter over
`tasks.json` that prints id, Task name, Summary, Project Name, Project Category, Due and the
empty fields only.

- `area`: `Work` or `Personal`. Use Project Category (Business → Work, Life → Personal),
  **except** for the "Phone Tasks" project, which is a capture inbox: judge from the title.
- `size`: `S` ≤ 15 min of effort (a reply, a booking, a quick check); `M` ≤ 2 h; `L` needs
  several sessions.
- `deadline_type`: `Hard` only with evidence — a `90 |` / `JIRA |` prefix, an agreed date in
  the summary or source, or an official / health / legal deadline. Otherwise `Soft`.
- `confidential`: true if the title or summary matches a word in the Preferences
  `confidential_keywords`, or is clearly about people, pay, hiring or legal matters. When
  unsure, true.
- `duplicate_of`: id of an open task with the same intent; `duplicate_certain` only when the
  titles are near-identical and from the same source.
Omit fields you can't judge. Never infer for closed tasks.
