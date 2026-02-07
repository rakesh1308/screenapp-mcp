#!/bin/bash

# ScreenApp MCP Server - Quick Start Script

echo "🚀 ScreenApp MCP Server Setup"
echo "================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.11 or higher."
    exit 1
fi

echo "✓ Python found: $(python3 --version)"
echo ""

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

echo "✓ Virtual environment activated"
echo ""

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

echo "✓ Dependencies installed"
echo ""

# Setup environment file
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo "✓ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env file and add your ScreenApp credentials:"
    echo "   - SCREENAPP_API_TOKEN"
    echo "   - SCREENAPP_TEAM_ID"
    echo ""
    echo "Get them from: https://screenapp.io → Settings → Integration → API"
    echo ""
else
    echo "✓ .env file already exists"
    echo ""
fi

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your ScreenApp credentials"
echo "2. Run: source venv/bin/activate  (or venv\Scripts\activate on Windows)"
echo "3. Test: python src/server.py"
echo "4. Deploy to Zeabur (see README.md)"
echo ""
