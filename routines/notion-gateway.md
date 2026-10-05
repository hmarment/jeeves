# Notion gateway

All Notion reads and writes from routines and skills go through these three operations.
They call two Zapier code actions (on the user's Zapier account, Notion app) through the
Zapier connector:

- `execute_zapier_write_action` with `selected_api` = the Notion app's id as listed by
  `inspect_zapier_actions`, `action` = `code_action_notioncliapi__jeeves_query`
  (inputs: `database_id`, `filter_json`, `page_ids`, `properties`)
- same, `action` = `code_action_notioncliapi__jeeves_apply` (input: `writes_json`)

- same, `action` = `code_action_notioncliapi__jeeves_page_text` (input: `page_id`)

IDs come from environment variables: `JEEVES_TASKS_DB`, `JEEVES_DAILY_PLAN_DB`,
`JEEVES_PREFERENCES_PAGE` (and `JEEVES_SCRATCH_DB` for tests).

Large results: when the connector says the result exceeds the token limit and saved it
to a file, use that file path directly as the input to `jeeves snapshot`; it unwraps the
Zapier envelope itself. Never paste large results into your reasoning. Any page or database the gateway touches must be
shared with the "Zapier" Notion integration (⋯ → Connections); a 404 "make sure ... shared
with your integration" error means it isn't.

## read_tasks(statuses, extra_ids)
`jeeves_query` with
- `database_id` = `$JEEVES_TASKS_DB`
- `filter_json` = `{"or":[{"property":"Status","status":{"equals":"<S>"}}, ...]}` for each status
- `page_ids` = extra_ids joined by commas (may be empty)
- `properties` = `Task name,Status,Due,Original due,Priority,Size,Deadline type,Area,Confidential,Deferrals,Last deferred,Planned by PA,Summary,Project Name,Project Category,Created time,Last edited time`

Returns `{"pages":[{id,url,created_time,last_edited_time,properties:{...}}],"count":N}`.
Values are flat: text, select/status name, date start (may be a UTC datetime — convert to
the Europe/Berlin date), number, true/false, relation id list, rollup list.

## read_daily_plan(dates)
`jeeves_query` with `database_id` = `$JEEVES_DAILY_PLAN_DB`,
`filter_json` = `{"or":[{"property":"Date","title":{"equals":"<YYYY-MM-DD>"}}, ...]}`.

## read_preferences()
`jeeves_page_text` with `page_id` = `$JEEVES_PREFERENCES_PAGE`. Save the returned `text`
to `prefs.txt`; `jeeves snapshot --prefs prefs.txt` extracts the JSON settings block.

## apply_writes(writes)
`jeeves_apply` with `writes_json` = a JSON array of
- `{"op":"update","page_id":"…","properties":{"<Notion name>": value}}`
- `{"op":"create","database_id":"…","properties":{…},"body_lines":["## h","- bullet","text"]}`
- `{"op":"replace_body","page_id":"…","body_lines":[…]}`

Values: dates `"YYYY-MM-DD"`; `null` clears a date/number/select; relations are id lists;
checkboxes true/false. Send at most 40 items per call. The response has one
`{index, ok, page_id, url, error}` per item; treat `ok:false` as that change failing and
record it in the run's change log. Items run in order; one failure doesn't stop the rest.

## Switch-over
If the Notion connector is re-approved, re-implement these three operations with it here,
keeping the same inputs and outputs, then re-render the skills.
