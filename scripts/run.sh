#!/usr/bin/env bash
# AE Dashboard Streamlit - Run Script
# Activates venv, loads .env, and runs the Streamlit dashboard

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Run setup first:"
    echo "   ./setup.sh"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Load .env if it exists (python-dotenv in the app will also load it, but export for subprocesses)
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
fi

# Default to main dashboard
DASHBOARD="${1:-streamlit_dashboard.py}"

echo "🚀 Starting AE Dashboard..."
echo "   Dashboard: $DASHBOARD"
echo "   URL: http://localhost:8501"
echo ""

exec streamlit run "$DASHBOARD" --server.headless true
