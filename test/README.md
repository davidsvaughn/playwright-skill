# Test app and checks

- `server.py`: a synthetic "Acme Orders" app (login, a 240-row orders table with filters, a settings form whose save fails with a 422 and then an uncaught `TypeError`).
  No dependencies beyond Python 3.
- `brief.md`: the subagent brief and what to check in its transcript.
- `measure.sh`: the same flow scripted, timing and sizing each command; writes `test/out/measure.tsv`.

## Head-to-head of 2026-09-16 (why the wrapper was retired)

`playwright-cli` 0.1.20 against `vercel-labs/agent-browser` 0.38.0 on this app; one fresh subagent per tool, same brief.

| | playwright-cli | agent-browser |
|---|---|---|
| Both tasks correct, root cause and second bug found | yes | yes |
| Agent tokens / tool calls / wall time | 67,952 / 24 / 188 s | 72,064 / 23 / 153 s |
| Median time per scripted action | 306 ms | 7 ms |
| Snapshot of the 240-row page | 57 KB | 48 KB full, 35 KB with `-i` |
| Size of the tool's agent guide | 15 KB | 37 KB (143 KB with `--full`) |

- Neither agent needed the old wrapper: native `console`, `requests`, `request <n>`, `request-body`/`response-body` and `eval` covered the whole diagnosis.
- `playwright-cli` friction: its official skill never mentions `request-body`/`response-body`/`requests --static`; the snapshot printed after `fill --submit` caught a loading screen; `--raw eval` returns strings JSON-encoded.
  All three are covered in `SKILL.md`.
- `agent-browser` friction: plain-text `errors` prints a bare `✗` with no message (upstream issue #1692, open in 0.38.0) and plain `network request <id>` prints only the URL, so the evidence only shows with `--json`; uncaught exceptions appear under `errors`, not `console`; `snapshot --delta` fell back to a full snapshot after the filter re-rendered the table.
- One run per tool, so the token difference is noise.
  Decision: stay on `playwright-cli`; revisit `agent-browser` when #1692 is fixed (see `TODO.md`).
