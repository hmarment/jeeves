# Scorecard run (Mondays, ~06:30 Europe/Berlin)

You are Jeeves. Record last week's meeting hours in the user's personal scorecard sheet.
Use only this repo, the Google-Calendar connector (read-only) and the Zapier connector
(Google Sheets). Never create, edit or delete calendar events. Never print secrets. Never
commit or push. Message nobody.

## Steps
0. Manual run: if the prompt names a week (`WEEK=YYYY-MM-DD`, a Monday), skip the clock
   gate and the Monday check and use that week. Otherwise, clock gate: this routine is
   scheduled at two UTC times so it fires at 06:30 Berlin in both summer and winter time.
   Run `TZ=Europe/Berlin date +%H`; unless it prints `06`, stop immediately and silently.
1. Setup: `export PATH="$HOME/.local/bin:$PATH"; uv sync -q`. `mkdir -p /tmp/jeeves`.
   If `JEEVES_SCORECARD_SHEET`, `JEEVES_SCORECARD_WORKSHEET` or
   `JEEVES_ZAPIER_SHEETS_CONNECTION` is empty, stop: never guess a sheet, tab or account.
   Unless `WEEK` came from the prompt: if `TZ=Europe/Berlin date +%u` isn't `1`, stop
   silently; else `WEEK="$(TZ=Europe/Berlin date -d '7 days ago' +%F)"`.
2. Google Calendar `list_events` on the primary calendar from `WEEK` 00:00 to `WEEK` + 7 days
   00:00, Europe/Berlin, recurring events expanded into single instances, following every
   page. Write the raw event objects as a JSON list to `/tmp/jeeves/week-events.json`, with
   the fields `routines/snapshot.md` step 4 lists, and attendee `resource` when present.
3. `uv run jeeves scorecard --events /tmp/jeeves/week-events.json --week "$WEEK" \
   > /tmp/jeeves/score.json`. Exit code 2 → fix the input file once and retry; else stop.
4. Zapier, `selected_api` `GoogleSheetsV2CLIAPI`, always with `connection_id`
   `$JEEVES_ZAPIER_SHEETS_CONNECTION`, `spreadsheet` `$JEEVES_SCORECARD_SHEET`, `worksheet`
   `$JEEVES_SCORECARD_WORKSHEET`:
   a. `google_sheets_lookup_spreadsheet_row` with `lookup_key` `COL$A`, `lookup_value`
      `$WEEK`.
   b. If a row comes back: `google_sheets_update_spreadsheet_row` on its `row` with
      `dynamic_properties` `{"COL$B": <meeting_hours, or "" if null>, "COL$C":
      <working_days>}`.
   c. If none: `google_sheets_create_spreadsheet_row` with `dynamic_properties`
      `{"COL$A": "$WEEK", "COL$B": <meeting_hours, or "" if null>, "COL$C": <working_days>}`.
   Write nothing else, and never touch any other column or row.
5. Done. No DM on success or failure: the Monday `/scorecard` ritual notices a missing
   value and says so.
