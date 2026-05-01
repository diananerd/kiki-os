#!/usr/bin/env bash
# Blocks destructive git operations that could lose work.
# Called via PreToolUse on Bash.

INPUT=$(cat)
CMD=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('command',''))" 2>/dev/null)

BLOCKED_PATTERNS=(
  "git push --force"
  "git reset --hard"
  "git clean -f"
  "git checkout --"
  "git restore ."
  "rm -rf"
)

for pat in "${BLOCKED_PATTERNS[@]}"; do
  if echo "$CMD" | grep -qF "$pat"; then
    echo "Blocked destructive command: $pat. Ask the lead before running this." >&2
    exit 2
  fi
done

exit 0
