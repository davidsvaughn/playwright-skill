# Agent check: does the skill suffice?

Run this after changing `SKILL.md` or upgrading `@playwright/cli`.
It sends one fresh subagent through a small QA task with nothing but the two skills, and checks the house rules held.

## Setup

```bash
python3 -u test/server.py 18792 > test/out/server.log 2>&1 &   # mkdir -p test/out first
python3 test/server.py --answer                                # expected answer to task 1
```

## Brief for the subagent

Replace `<port>` and `<workdir>` (a scratch directory; the CLI writes `.playwright-cli/` there).

> Do the task below the way you normally would on a real QA/debugging task, working only through a browser.
> Load the `playwright-skill` and `playwright-cli` skills and follow them.
> Start every Bash command with `cd <workdir> &&`.
>
> A local web app ("Acme Orders") runs at http://127.0.0.1:<port>/ . Sign in with username `demo`, password `demo123` (test credentials, not a real account).
> Run headless. Do not use curl, wget or other HTTP clients, and do not read the app's source.
>
> 1. On the Orders page: how many orders belong to customer "Globex" with status "pending", and what is their combined total in dollars? List their order IDs.
> 2. Bug report: "On the Settings page I change my display name and click Save. Nothing visibly happens, and after reloading my old name is back." Reproduce it (change the display name to `QA Tester`), then find the cause. Collect concrete evidence from the browser: console messages, the relevant network request with method, URL and status, and the request and response bodies. State the root cause as precisely as the evidence allows. Do not fix anything.
>
> Finish by closing your browser session. Reply with the answers, every browser command you ran in order, and honest notes on what was awkward.

## What to check in the transcript

- The session name follows section 1 of `SKILL.md` (`<repo>-<8 hex chars>` or a suffixed name from a parent), and every command carries `-s=`.
- Task 1 matches `server.py --answer` (11 orders, $13,708.64 with the seeded data).
- Task 2 names the field mismatch (`displayName` sent, `display_name` required, 422) and the follow-on `TypeError` on `data.user.name`, with `request-body`/`response-body` evidence.
- The agent closed its own session and ran neither `close-all` nor `kill-all`.
- Anything the agent reports as awkward that the skill does not already cover becomes a `SKILL.md` change or a `TODO.md` item.
