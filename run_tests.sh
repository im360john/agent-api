#!/bin/bash

# Run tests for Competitive Pricing Agent

echo "🧪 Running Competitive Pricing Agent Tests..."
echo "=========================================="

# Install test dependencies if needed
if ! python -c "import pytest" 2>/dev/null; then
    echo "Installing test dependencies..."
    pip install -r requirements-test.txt
fi

# Run tests with coverage
echo ""
echo "Running unit tests..."
python -m pytest tests/test_competitive_pricing_agent.py -v --cov=agents.competitive_pricing_agent --cov-report=term-missing

# Run specific test categories
echo ""
echo "Running database operation tests..."
python -m pytest tests/test_competitive_pricing_agent.py::TestCompetitorPricingTools -k "database" -v

echo ""
echo "Running web scraping tests..."
python -m pytest tests/test_competitive_pricing_agent.py::TestCompetitorPricingTools -k "scrape" -v

echo ""
echo "Running integration tests..."
python -m pytest tests/test_competitive_pricing_agent.py::TestIntegration -v

echo ""
echo "✅ Test suite complete!"