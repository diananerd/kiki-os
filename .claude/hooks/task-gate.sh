#!/usr/bin/env bash
# Blocks TaskCompleted until basic doc integrity holds.
# Exit 2 = block + feedback to Claude. Exit 0 = allow.

INPUT=$(cat)
TASK_NAME=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('task',{}).get('name',''))" 2>/dev/null)

# Verify no SPEC files remain outside docs/specs/
MISPLACED=$(find docs -maxdepth 2 -name "*.md" ! -path "docs/specs/*" -exec grep -l "^type: SPEC" {} \; 2>/dev/null | head -5)
if [ -n "$MISPLACED" ]; then
  echo "SPEC files found outside docs/specs/: $MISPLACED" >&2
  exit 2
fi

exit 0
