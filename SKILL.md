---
name: playwright-skill
description: House rules for driving a browser with playwright-cli on this machine - session names that keep parallel Claude sessions and subagents apart, saved login profiles, finding bugs through console output and network request/response bodies, and the CLI's output gotchas. Use it for any browser work (verifying a UI, reproducing a web app bug, QA, signing in to a site, reading a rendered page), together with the playwright-cli skill, which is the command reference.
allowed-tools: Bash(playwright-cli:*)
---

# Browser work with playwright-cli: house rules

`playwright-cli` (Microsoft's `@playwright/cli`, installed globally) is the browser tool on this machine.
The `playwright-cli` skill is its command reference; it is regenerated on every upgrade, so local rules live here instead.
This skill covers what that reference leaves out or gets wrong for the way agents work here.
Verified against `@playwright/cli` 0.1.20 on 2026-09-16.

## 1. Sessions: pick a unique name and pass it on every command

- Browser sessions are machine-wide: every Claude Code session, subagent and terminal sees the same names, and `playwright-cli list` shows them all.
- A command without `-s=<name>` targets a session literally named `default`, which you did not open, and fails with `The browser 'default' is not open`.
  `PLAYWRIGHT_CLI_SESSION` does not survive between Bash tool calls, so pass `-s` on every command.
- Name the session after the repo plus the first 8 characters of your Claude Code session ID, so parallel sessions never share a browser.
  Work the name out once, then use it literally:

  ```bash
  echo "$(basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)")-${CLAUDE_CODE_SESSION_ID:0:8}"
  # -> myapp-4ce59141
  ```

- Subagents inherit their parent's session ID.
  When you hand browser work to parallel subagents, give each one its own name in the brief (`myapp-4ce59141-checkout`, `myapp-4ce59141-admin`); each subagent opens and closes its own browser.
- Close only your own sessions: `playwright-cli -s=<name> close`.
  Never run `close-all` or `kill-all` unless the user asks, because they close other agents' browsers too.

```bash
playwright-cli -s=myapp-4ce59141 open http://localhost:3000 --headed
playwright-cli -s=myapp-4ce59141 snapshot
playwright-cli -s=myapp-4ce59141 fill e5 "search term" --submit
playwright-cli -s=myapp-4ce59141 close
```

## 2. Headed or headless

- Open with `--headed` so the user can watch, unless the run is unattended or the user asked for headless.
- Headed browsers never time out, so always close them when done.
  Headless sessions shut down after an hour without commands; the next command then reports the browser is not open, so `open` again.

## 3. Signing in: saved login profiles

- Never type, fill or script the user's credentials.
  When a site needs a login, open it `--headed`, ask the user to sign in in that window, and save the state once they say they are done.
- Profiles live in `~/.local/state/playwright-auth/<profile>.json`.
  They hold live session cookies: keep the directory at mode 700 and the files at 600, and never print, commit or upload them.
- The project's CLAUDE.md names the profile it uses and says what a valid session looks like.

```bash
# save after the user has signed in
mkdir -p -m 700 ~/.local/state/playwright-auth
playwright-cli -s=<name> state-save ~/.local/state/playwright-auth/<profile>.json
chmod 600 ~/.local/state/playwright-auth/<profile>.json

# reuse in a new session: load before navigating
playwright-cli -s=<name> open --headed
playwright-cli -s=<name> state-load ~/.local/state/playwright-auth/<profile>.json
playwright-cli -s=<name> goto <url>
```

If the site sends you to its sign-in page anyway, the saved session has expired: ask the user to sign in again and re-save.

## 4. Finding the cause of a bug: console and network

- `console` lists console messages, including uncaught exceptions with `file:line:col`.
  After an action that should have had a visible effect but did not, check it; the action's own output already shows the page's error count (`Console: N errors`) and links any new console entries.
- `requests` lists fetch/XHR requests with a number; `requests --static` adds documents, scripts and images, and `--filter <regexp>` narrows by URL.
- `request <n>` shows the status and headers only, despite its help text.
  The bodies need `request-body <n>` and `response-body <n>`, which the `playwright-cli` skill does not mention.
- `response-body <n>` on a script request returns the JavaScript as the browser received it, which is often the quickest way to read the client code behind a bug.

```bash
playwright-cli -s=<name> click e18            # the action that misbehaves
playwright-cli -s=<name> console error
playwright-cli -s=<name> requests --filter "/api/"
playwright-cli -s=<name> request 7
playwright-cli -s=<name> request-body 7
playwright-cli -s=<name> response-body 7
```

## 5. Output gotchas

- `snapshot` with no arguments prints the whole accessibility tree inline (57 KB for a 240-row table), although the `playwright-cli` skill says it writes a file.
  On large pages use `find "<text>"`, `snapshot <ref-or-selector>` for one region, `snapshot --depth=<n>`, or `snapshot --filename=<file>` and search the file.
  Action commands (`click`, `fill`, `goto`) do link their snapshot as a file instead of printing it.
- The snapshot an action links to can show a loading state.
  There is no `wait` command; wait for the content first with `run-code 'async page => { await page.waitForSelector("<css>"); }'`, or `page.waitForURL(...)` after a login redirect.
- `eval` takes a single expression; statements joined with `;` are a SyntaxError.
  For several statements use `run-code 'async page => { ...; return value; }'` and `page.evaluate(...)`.
- `run-code` takes one function expression; get values out with `return`, since `console.log` inside it prints nothing.
- `--raw` prints only the result value, but strings come back JSON-encoded (quotes and escapes included).
  Return an object, or pipe through `jq -r`.
- Refs change prefix after a navigation (`e5`, then `f1e13`); the `f1` does not mean a frame.
  Take a fresh snapshot rather than reusing old refs.

## 6. Elements without refs, and file inputs

- Portal-rendered modals, canvas libraries and similar UI can be missing from the snapshot.
  Target them with a CSS selector or a Playwright locator instead of a ref: `click "#confirm"`, `click "getByRole('button', { name: 'Approve' })"`.
- For a hidden `<input type=file>`, set the files directly:
  `run-code 'async page => { await page.setInputFiles("input[type=file]", "/absolute/path/file.pdf"); }'`.

## 7. Files left behind

- Every command writes to `.playwright-cli/` in the current directory: snapshots, console logs, screenshots, traces.
  Traces and logs can contain session cookies, so run from the repo root or a scratch directory.
  `.playwright-cli/` is in the global gitignore on this machine (`~/.gitignore`), so it never needs a per-repo entry.

## Upgrades

The `README.md` next to this file says how to upgrade the CLI, regenerate the `playwright-cli` skill, and recheck these rules with the test app in `test/`.
Sections 1, 4 and 5 describe CLI behaviour, which changes between releases, so recheck them after every upgrade.
