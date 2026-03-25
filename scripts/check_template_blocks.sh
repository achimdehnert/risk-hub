#!/usr/bin/env bash
# check_template_blocks.sh — CI guard for Django template block mismatches
#
# Detects child templates that override blocks not defined in their parent.
# Prevents silent JS/CSS loss when block names diverge.
#
# Usage:  ./scripts/check_template_blocks.sh [template_dir] [base_template]
# Exit 0 = OK, Exit 1 = mismatches found

set -euo pipefail

TEMPLATE_DIR="${1:-src/templates}"
BASE_TEMPLATE="${2:-$TEMPLATE_DIR/base.html}"

if [[ ! -f "$BASE_TEMPLATE" ]]; then
    echo "ERROR: Base template not found: $BASE_TEMPLATE"
    exit 1
fi

# Extract block names defined in base template
BASE_BLOCKS=$(grep -oP '\{% block \K[a-z_]+' "$BASE_TEMPLATE" | sort -u)

echo "=== Template Block Consistency Check ==="
echo "Base: $BASE_TEMPLATE"
echo "Blocks defined: $(echo $BASE_BLOCKS | tr '\n' ' ')"
echo "---"

ERRORS=0

# Find all templates extending base.html
for child in $(grep -rl 'extends "base.html"' "$TEMPLATE_DIR" 2>/dev/null); do
    # Get blocks used in child
    CHILD_BLOCKS=$(grep -oP '\{% block \K[a-z_]+' "$child" 2>/dev/null | sort -u)

    for block in $CHILD_BLOCKS; do
        if ! echo "$BASE_BLOCKS" | grep -qx "$block"; then
            echo "MISMATCH: $child uses {% block $block %} — not defined in base.html"
            ERRORS=$((ERRORS + 1))
        fi
    done
done

# Check 2: Self-include in {# #} comments (causes RecursionError)
echo "---"
echo "=== Self-Include in Comments Check ==="
for partial in $(find "$TEMPLATE_DIR" -name '_*.html' 2>/dev/null); do
    basename=$(basename "$partial")
    dirname=$(basename "$(dirname "$partial")")
    # Look for {% include ... self-filename ... inside {# #} comments
    if grep -Pq '\{#.*\{% include.*'"$basename"'.*#\}' "$partial" 2>/dev/null; then
        echo "SELF-INCLUDE: $partial contains {% include ...${basename}... %} inside {# #} comment"
        echo "  Django parses template tags inside {# #} — use {% comment %}{% endcomment %} instead"
        ERRORS=$((ERRORS + 1))
    fi
done

echo "---"
if [[ $ERRORS -gt 0 ]]; then
    echo "FAIL: $ERRORS issue(s) found."
    exit 1
else
    echo "OK: All template checks passed."
    exit 0
fi
