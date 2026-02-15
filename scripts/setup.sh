#!/usr/bin/env bash
# AE Dashboard Streamlit - Setup Script
# Creates virtual environment, installs dependencies, and configures credentials

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "📦 AE Dashboard Streamlit - Setup"
echo "=================================="

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "Virtual environment already exists"
fi

# Activate and install dependencies
echo ""
echo "Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "✅ Dependencies installed"

# Create .env from template if it doesn't exist
if [ ! -f ".env" ]; then
    echo ""
    echo "Creating .env from template..."
    cp scripts/.env.example .env
    echo "✅ Created .env file"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and add your Salesforce credentials:"
    echo "   - SALESFORCE_USERNAME"
    echo "   - SALESFORCE_PASSWORD"
    echo "   - SALESFORCE_SECURITY_TOKEN"
    echo ""
    echo "   Run: nano .env  (or use your preferred editor)"
else
    echo ""
    echo ".env file already exists (credentials configured)"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "To run the dashboard:"
echo "  ./run.sh  (or ./scripts/run.sh)"
echo ""
echo "Or manually:"
echo "  source venv/bin/activate"
echo "  streamlit run streamlit_dashboard.py"
echo ""
