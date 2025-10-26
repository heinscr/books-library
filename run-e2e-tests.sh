#!/bin/bash
#
# E2E Test Runner Script
#
# Usage:
#   ./run-e2e-tests.sh                    # Run all E2E tests (headless)
#   ./run-e2e-tests.sh --headed           # Run with visible browser
#   ./run-e2e-tests.sh --debug            # Run with Playwright inspector
#   ./run-e2e-tests.sh test_authentication.py  # Run specific test file
#

set -e

# Load .env file if it exists
if [ -f .env ]; then
    echo "📄 Loading environment variables from .env file..."
    export $(grep -v '^#' .env | xargs)
fi

# Check for required environment variables
if [ -z "$TEST_USER_EMAIL" ] || [ -z "$TEST_USER_PASSWORD" ]; then
    echo "❌ Error: TEST_USER_EMAIL and TEST_USER_PASSWORD environment variables must be set"
    echo ""
    echo "Please either:"
    echo "  1. Create a .env file in the project root with:"
    echo "     TEST_USER_EMAIL=your-email@example.com"
    echo "     TEST_USER_PASSWORD=your-password"
    echo ""
    echo "  2. Or export them manually:"
    echo "     export TEST_USER_EMAIL='your-test-user@example.com'"
    echo "     export TEST_USER_PASSWORD='your-test-password'"
    echo ""
    exit 1
fi

# Default values
BROWSER="chromium"
HEADED=""
DEBUG=""
SLOWMO=""
TEST_PATH="tests/e2e"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --headed)
            HEADED="--headed"
            shift
            ;;
        --debug)
            DEBUG="PWDEBUG=1"
            HEADED="--headed"
            shift
            ;;
        --slow)
            SLOWMO="--slowmo 1000"
            HEADED="--headed"
            shift
            ;;
        --firefox)
            BROWSER="firefox"
            shift
            ;;
        --webkit)
            BROWSER="webkit"
            shift
            ;;
        *)
            TEST_PATH="tests/e2e/$1"
            shift
            ;;
    esac
done

echo "🧪 Running E2E tests..."
echo "   Browser: $BROWSER"
echo "   Test path: $TEST_PATH"
echo ""

# Run tests
if [ -n "$DEBUG" ]; then
    env $DEBUG PYTHONPATH=. pipenv run pytest -m e2e $TEST_PATH \
        --browser $BROWSER \
        $HEADED \
        $SLOWMO \
        -v
else
    PYTHONPATH=. pipenv run pytest -m e2e $TEST_PATH \
        --browser $BROWSER \
        $HEADED \
        $SLOWMO \
        -v
fi

echo ""
echo "✅ E2E tests complete!"
