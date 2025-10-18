#!/bin/bash
# Code quality checks for Books Library project
# Run this before committing code

set -e  # Exit on error

echo "🔍 Running code quality checks..."
echo ""

# Black - Code formatter
echo "📝 Checking code formatting with Black..."
pipenv run black --check gateway_backend/ tests/ || {
    echo "❌ Black found formatting issues. Run 'pipenv run black gateway_backend/ tests/' to fix."
    exit 1
}
echo "✅ Black: All code is properly formatted"
echo ""

# Ruff - Linter
echo "🔎 Running Ruff linter..."
pipenv run ruff check gateway_backend/ tests/ || {
    echo "❌ Ruff found linting issues. Run 'pipenv run ruff check --fix gateway_backend/ tests/' to auto-fix."
    exit 1
}
echo "✅ Ruff: No linting issues found"
echo ""

# MyPy - Type checker (optional, can be slow)
if [ "$1" = "--with-mypy" ]; then
    echo "🔬 Running MyPy type checker..."
    pipenv run mypy gateway_backend/ tests/ || {
        echo "⚠️  MyPy found type issues (not blocking)"
    }
    echo ""
fi

# Pytest - Unit tests
echo "🧪 Running tests..."
PYTHONPATH=. pipenv run pytest || {
    echo "❌ Tests failed!"
    exit 1
}
echo "✅ All tests passed"
echo ""

echo "✨ All quality checks passed! Ready to commit. ✨"
