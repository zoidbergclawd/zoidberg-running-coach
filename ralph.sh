#!/bin/bash
# ralph.sh - Run Claude Code in a loop to implement the PRD
#
# Usage: ./ralph.sh <iterations>
# Example: ./ralph.sh 5

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <iterations>"
    exit 1
fi

ITERATIONS=$1
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "🦀 Zoidberg's Ralph Loop - Starting $ITERATIONS iterations"
echo "Project: $PROJECT_DIR"
echo ""

for ((i=1; i<=$ITERATIONS; i++)); do
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔄 Iteration $i of $ITERATIONS"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    result=$(cd "$PROJECT_DIR" && claude -p \
"@prd.json @progress.txt @AGENTS.md

You are implementing the Zoidberg Running Coach project.

1. Read prd.json to see all tasks and their status
2. Read progress.txt to see what has been done
3. Choose the HIGHEST PRIORITY incomplete task (passes: false)
4. Implement that ONE task completely
5. Run type checking: python -m mypy src/ --ignore-missing-imports (if applicable)
6. Update progress.txt with:
   - Task completed (reference PRD item number)
   - Key decisions made
   - Files changed
   - Any blockers or notes
7. Make a git commit with a descriptive message

ONLY WORK ON ONE TASK PER ITERATION.

If you discover all tasks are complete (all passes: true), output:
<promise>COMPLETE</promise>

Begin." 2>&1) || true
    
    echo "$result"
    echo ""
    
    if [[ "$result" == *"<promise>COMPLETE</promise>"* ]]; then
        echo "✅ PRD complete! All tasks finished."
        exit 0
    fi
    
    echo "Waiting 5 seconds before next iteration..."
    sleep 5
done

echo ""
echo "🏁 Completed $ITERATIONS iterations. Check progress.txt for status."
