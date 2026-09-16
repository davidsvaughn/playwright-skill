#!/usr/bin/env bash
# Scripted run of the brief.md flow against test/server.py, one TSV line per command:
# tool, step, exit code, milliseconds, stdout bytes, bytes of the snapshot file the output links to.
# Runs playwright-cli, and agent-browser too when it is on PATH. Output lands in test/out/.
#
#   test/measure.sh            # starts the server on port 18792, runs both tools, stops it
#   PORT=18800 test/measure.sh
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PORT="${PORT:-18792}"
URL="http://127.0.0.1:$PORT"
OUT="$HERE/out"; RES="$OUT/measure.tsv"
rm -rf "$OUT"; mkdir -p "$OUT/cmd" "$OUT/work-pw" "$OUT/work-ab"

python3 -u "$HERE/server.py" "$PORT" > "$OUT/server.log" 2>&1 &
SERVER=$!
trap 'kill "$SERVER" 2>/dev/null' EXIT
for _ in $(seq 50); do grep -q listening "$OUT/server.log" 2>/dev/null && break; sleep 0.1; done
grep -q listening "$OUT/server.log" || { echo "server did not start; see $OUT/server.log" >&2; exit 1; }

printf 'tool\tstep\texit\tms\tstdout_bytes\tlinked_file_bytes\n' > "$RES"
N=0
run() {  # run <tool> <step> <command...>
  local tool=$1 step=$2; shift 2
  N=$((N + 1))
  local f="$OUT/cmd/$(printf '%02d' $N)-$tool-$step.txt" t0 t1 rc linked=0 lf
  t0=$(date +%s%N)
  ( cd "$OUT/work-$tool" && "$@" ) > "$f" 2>&1; rc=$?
  t1=$(date +%s%N)
  lf=$(grep -oE '\.playwright-cli/page-[^)]+\.yml' "$f" | tail -1 || true)
  [ -n "$lf" ] && [ -f "$OUT/work-$tool/$lf" ] && linked=$(wc -c < "$OUT/work-$tool/$lf")
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$tool" "$step" "$rc" $(( (t1 - t0) / 1000000 )) "$(wc -c < "$f")" "$linked" | tee -a "$RES"
}

PW=(playwright-cli -s=playwright-skill-measure)
run pw open            "${PW[@]}" open "$URL/"
run pw snap-login      "${PW[@]}" snapshot
run pw fill-user       "${PW[@]}" fill 'input[name=username]' demo
run pw fill-pass       "${PW[@]}" fill 'input[name=password]' demo123
run pw submit          "${PW[@]}" click 'button[type=submit]'
run pw wait-table      "${PW[@]}" run-code 'async page => { await page.waitForSelector("#rows tr"); return "ok"; }'
run pw snap-orders     "${PW[@]}" snapshot
run pw find-globex     "${PW[@]}" find Globex
run pw select-pending  "${PW[@]}" select '#status' pending
run pw fill-search     "${PW[@]}" fill '#q' Globex
run pw snap-filtered   "${PW[@]}" snapshot
run pw eval-count      "${PW[@]}" eval 'document.getElementById("count").textContent'
run pw goto-settings   "${PW[@]}" goto "$URL/app#settings"
run pw wait-form       "${PW[@]}" run-code 'async page => { await page.waitForSelector("input[name=displayName]"); return "ok"; }'
run pw fill-name       "${PW[@]}" fill 'input[name=displayName]' 'QA Tester'
run pw click-save      "${PW[@]}" click 'button[type=submit]'
run pw console         "${PW[@]}" console
run pw requests        "${PW[@]}" requests
PWREQ=$(grep -E 'POST.*/api/settings' "$OUT"/cmd/*-pw-requests.txt | grep -oE '^[0-9]+' | head -1)
run pw request-detail  "${PW[@]}" request "${PWREQ:-0}"
run pw request-body    "${PW[@]}" request-body "${PWREQ:-0}"
run pw response-body   "${PW[@]}" response-body "${PWREQ:-0}"
run pw close           "${PW[@]}" close

if command -v agent-browser >/dev/null; then
  AB=(agent-browser --session playwright-skill-measure)
  run ab open            "${AB[@]}" open "$URL/"
  run ab snap-login      "${AB[@]}" snapshot -i
  run ab fill-user       "${AB[@]}" fill 'input[name=username]' demo
  run ab fill-pass       "${AB[@]}" fill 'input[name=password]' demo123
  run ab submit          "${AB[@]}" click 'button[type=submit]'
  run ab wait-table      "${AB[@]}" wait '#rows tr'
  run ab snap-orders     "${AB[@]}" snapshot
  run ab snap-orders-i   "${AB[@]}" snapshot -i
  run ab snap-delta-base "${AB[@]}" snapshot --delta
  run ab select-pending  "${AB[@]}" select '#status' pending
  run ab fill-search     "${AB[@]}" fill '#q' Globex
  run ab snap-delta      "${AB[@]}" snapshot --delta
  run ab snap-filtered   "${AB[@]}" snapshot
  run ab eval-count      "${AB[@]}" eval 'document.getElementById("count").textContent'
  run ab goto-settings   "${AB[@]}" open "$URL/app#settings"
  run ab wait-form       "${AB[@]}" wait 'input[name=displayName]'
  run ab fill-name       "${AB[@]}" fill 'input[name=displayName]' 'QA Tester'
  run ab click-save      "${AB[@]}" click 'button[type=submit]'
  run ab console         "${AB[@]}" console
  run ab errors          "${AB[@]}" errors --json
  run ab requests        "${AB[@]}" network requests --method POST --filter settings --json
  run ab close           "${AB[@]}" close
else
  echo "agent-browser not on PATH; skipped" | tee -a "$OUT/server.log"
fi
echo "done: $RES"
