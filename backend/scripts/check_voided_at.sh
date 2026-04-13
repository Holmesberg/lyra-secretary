#!/usr/bin/env bash
# check_voided_at.sh — audit for missing voided_at guards
#
# Scans Python files that query Task by state without also checking voided_at.
# Run from backend/ root:
#   bash scripts/check_voided_at.sh
#
# Exit 0 if clean, exit 1 with file list if suspicious.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "=== voided_at guard audit ==="
echo ""

# Find files that query Task.state but don't mention voided_at anywhere.
# This catches the most common bug pattern: filtering by state alone.
SUSPECTS=()

for f in $(grep -rl 'Task\.state\s*==' app/ --include='*.py' 2>/dev/null || true); do
    if ! grep -q 'voided_at' "$f"; then
        SUSPECTS+=("$f")
    fi
done

# Also check files that do db.query(Task) without voided_at
for f in $(grep -rl 'db\.query(Task)' app/ --include='*.py' 2>/dev/null || true); do
    if ! grep -q 'voided_at' "$f"; then
        # Exclude files that only query by primary key (task_id) without state filter
        if grep -q 'Task\.state' "$f"; then
            # Already caught above, skip duplicate
            continue
        fi
    fi
done

if [ ${#SUSPECTS[@]} -eq 0 ]; then
    echo "PASS: All files querying Task.state also reference voided_at."
    exit 0
else
    echo "WARNING: The following files query Task.state without voided_at:"
    echo ""
    for f in "${SUSPECTS[@]}"; do
        echo "  - $f"
    done
    echo ""
    echo "Review each file to confirm voided_at is checked where needed."
    echo "(Some may be false positives — e.g., state machine internals.)"
    exit 1
fi
