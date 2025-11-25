#!/bin/bash

# Script to install optional code quality tools for GitHub Analysis Dashboard

echo "Installing optional code quality analysis tools..."
echo ""

# Check if virtual environment is active
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  Warning: No virtual environment detected."
    echo "It's recommended to activate your virtual environment first:"
    echo "  source venv/bin/activate"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Install pylint
echo "📦 Installing pylint..."
pip install pylint>=3.0.0

if [ $? -eq 0 ]; then
    echo "✅ Pylint installed successfully"
else
    echo "❌ Failed to install pylint"
fi

echo ""
echo "Installation complete!"
echo ""
echo "Verification:"
echo "-------------"

# Verify installation
if command -v pylint &> /dev/null; then
    echo "✅ pylint: $(pylint --version | head -n 1)"
else
    echo "❌ pylint: Not found"
fi

echo ""
echo "Note: Pylint is optional. The analyzer will work without it,"
echo "but you'll get more comprehensive code quality metrics if it's installed."
