# TODO

- Revisit `vercel-labs/agent-browser` once upstream issue #1692 (plain-text `errors` prints no message) is fixed; it was faster per action but hid the evidence QA needs (`test/README.md`).
  It was uninstalled on 2026-09-16; `npm install -g agent-browser` brings it back.
- Session naming is a convention, not enforced: nothing stops two agents choosing the same name.
  If collisions happen in practice, consider a tiny `pw` shell function that derives the name and prepends `-s=`.
