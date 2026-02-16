#!/bin/bash
# sisyphus.sh - Push the boulder. Find the joy.
#
# An autonomous coding loop that processes PRD items one at a time.
# Supports multiple AI coding agents: Claude Code, Codex, Gemini CLI.
#
# Usage: ./sisyphus.sh [options] <iterations>
#
# Options:
#   -a, --agent <name>    Agent to use: claude (default), codex, gemini
#   -p, --push            Push to remote after each commit
#   -v, --verbose         Show agent output in real-time
#   -h, --help            Show this help message
#
# Example:
#   ./sisyphus.sh 10                    # Run 10 iterations with Claude
#   ./sisyphus.sh -a codex -p 5         # Run 5 iterations with Codex, push after each
#   ./sisyphus.sh -a gemini --push 3    # Run 3 iterations with Gemini, push after each

set -e

# Defaults
AGENT="claude"
PUSH_AFTER_COMMIT=false
VERBOSE=false
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -a|--agent)
            AGENT="$2"
            shift 2
            ;;
        -p|--push)
            PUSH_AFTER_COMMIT=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            head -24 "$0" | tail -20
            exit 0
            ;;
        *)
            ITERATIONS="$1"
            shift
            ;;
    esac
done

if [ -z "$ITERATIONS" ]; then
    echo "Usage: $0 [options] <iterations>"
    echo "Run '$0 --help' for more information."
    exit 1
fi

# Validate agent
case $AGENT in
    claude|codex|gemini)
        ;;
    *)
        echo -e "${RED}Error: Unknown agent '$AGENT'. Use: claude, codex, or gemini${NC}"
        exit 1
        ;;
esac

# Check for required files
if [ ! -f "$PROJECT_DIR/prd.json" ]; then
    echo -e "${RED}Error: prd.json not found in $PROJECT_DIR${NC}"
    exit 1
fi

if [ ! -f "$PROJECT_DIR/progress.txt" ]; then
    echo "# Sisyphus Progress Log" > "$PROJECT_DIR/progress.txt"
    echo "" >> "$PROJECT_DIR/progress.txt"
    echo "## Session Start: $(date '+%Y-%m-%d %H:%M:%S')" >> "$PROJECT_DIR/progress.txt"
    echo "" >> "$PROJECT_DIR/progress.txt"
fi

# The prompt given to each agent
read -r -d '' PROMPT << 'PROMPT_END' || true
@prd.json @progress.txt @AGENTS.md

You are Sisyphus - an autonomous coding agent processing a PRD.

## Your Task

1. Read prd.json to see all items and their status
2. Read progress.txt to see what has been completed
3. Find the HIGHEST PRIORITY incomplete item (passes: false, lowest id wins ties)
4. Implement that ONE item completely:
   - Write tests first (TDD)
   - Implement the feature
   - Verify tests pass
   - Run type checking if applicable
5. Update progress.txt with:
   - Item number and title
   - Route taken (A: simple, B: medium, C: complex)
   - Key decisions made
   - Files changed
   - Test results
6. Update prd.json: set the item's "passes" field to true
7. Make a git commit with this EXACT format:

   [ITEM-{id}] {title} (Route {route})

   {brief description of what was implemented}

   - {file1}: {change summary}
   - {file2}: {change summary}

   Tests: {number} passing

IMPORTANT:
- Work on exactly ONE item per invocation
- Do not skip the commit step
- If all items are complete, output: <sisyphus>COMPLETE</sisyphus>

The boulder awaits. Push it well.
PROMPT_END

# Agent command builders
run_claude() {
    claude --dangerously-skip-permissions -p "$PROMPT"
}

run_codex() {
    codex exec --yolo --sandbox danger-full-access "$PROMPT"
}

run_gemini() {
    gemini -p "$PROMPT"
}

# Main loop
echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║${NC}  ${YELLOW}⚙️  Sisyphus${NC} - Push the boulder. Find the joy.            ${CYAN}║${NC}"
echo -e "${CYAN}╠════════════════════════════════════════════════════════════╣${NC}"
echo -e "${CYAN}║${NC}  Agent:      ${GREEN}$AGENT${NC}                                         ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  Iterations: ${GREEN}$ITERATIONS${NC}                                           ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  Push:       ${GREEN}$PUSH_AFTER_COMMIT${NC}                                      ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  Project:    ${BLUE}$PROJECT_DIR${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

for ((i=1; i<=$ITERATIONS; i++)); do
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}🪨 Iteration $i of $ITERATIONS${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    # Run the appropriate agent
    if [ "$VERBOSE" = true ]; then
        result=$(cd "$PROJECT_DIR" && run_$AGENT 2>&1 | tee /dev/tty) || true
    else
        result=$(cd "$PROJECT_DIR" && run_$AGENT 2>&1) || true
    fi
    
    # Check for completion
    if [[ "$result" == *"<sisyphus>COMPLETE</sisyphus>"* ]]; then
        echo ""
        echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║${NC}  ${YELLOW}🏆 PRD COMPLETE!${NC}                                          ${GREEN}║${NC}"
        echo -e "${GREEN}║${NC}  The boulder has reached the top.                          ${GREEN}║${NC}"
        echo -e "${GREEN}║${NC}  Sisyphus smiles.                                          ${GREEN}║${NC}"
        echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
        exit 0
    fi
    
    # Check for new commit
    LATEST_COMMIT=$(cd "$PROJECT_DIR" && git log -1 --pretty=format:"%h %s" 2>/dev/null || echo "no commit")
    echo -e "${GREEN}✓ Committed:${NC} $LATEST_COMMIT"
    
    # Push if requested
    if [ "$PUSH_AFTER_COMMIT" = true ]; then
        echo -e "${BLUE}↑ Pushing to remote...${NC}"
        (cd "$PROJECT_DIR" && git push 2>/dev/null) && echo -e "${GREEN}✓ Pushed${NC}" || echo -e "${YELLOW}⚠ Push failed (no remote?)${NC}"
    fi
    
    echo ""
    echo -e "${BLUE}Waiting 5 seconds before next iteration...${NC}"
    sleep 5
done

echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║${NC}  ${YELLOW}🏁 Completed $ITERATIONS iterations${NC}                              ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  Check progress.txt for status.                             ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  The boulder rolls on.                                      ${CYAN}║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
