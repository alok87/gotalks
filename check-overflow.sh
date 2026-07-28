#!/usr/bin/env bash
# Reports the first slide that overflows at a given terminal size.
# presenterm stops at the first offender, so run this repeatedly while fixing.
#
# usage: ./check-overflow.sh [cols] [rows] [deck.md]
set -uo pipefail
COLS="${1:-120}"
ROWS="${2:-40}"
DECK="${3:-$(dirname "$0")/go-properly.md}"
HERE="$(cd "$(dirname "$0")" && pwd)"

python3 "$HERE/ptyrun.py" --cols "$COLS" --rows "$ROWS" --timeout 60 -- \
  presenterm --image-protocol ascii-blocks --validate-overflows --validate-snippets "$DECK" 2>&1 |
  perl -pe 's/\e\[[0-9;?]*[a-zA-Z]//g; s/\e[_\]P][^\e\a]*(\a|\e\\)//g' |
  tr -d '\0\r' |
  grep -Eo "presentation overflows [a-z]+ on slide [0-9]+|invalid command: [^q]*" |
  sort -u |
  head -5
