# Reminder runs (read-only except for the DM)

Clock gate first: each reminder is scheduled at two UTC times (summer/winter). Run
`TZ=Europe/Berlin date +%H` and continue only if it prints the hour named for your section
(`09` ritual-reminder, `17` shutdown-nudge, `18` shutdown-reminder); otherwise stop silently.

Use the Zapier connector only. Read today's Daily Plan row with `read_daily_plan([today])`
(see `routines/notion-gateway.md`; today = current Europe/Berlin date). If there is no row,
stop silently — no row means no plan was made (non-working day or planner failure, which
already sent its own DM).

- **ritual-reminder (~09:15):** if `Ritual done` is false, DM: "Your plan is waiting —
  /start-day takes 10 minutes." plus the row URL.
- **shutdown-nudge (~17:30):** DM: "Shutdown time — /shutdown takes 3 minutes."
- **shutdown-reminder (~18:30):** if `Shutdown done` is false, DM: "Last call for
  /shutdown — 3 minutes and tomorrow starts clean."

DM exactly as in `routines/plan-run.md` ("Slack DM"). Never modify Notion or the calendar
in these runs.
