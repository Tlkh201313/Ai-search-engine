#!/usr/bin/env bash
set -e
echo "Installing ai-search-engine..."
pip install -r requirements.txt
[ -f .env ] || cp .env.example .env
echo ""
echo "Done! Run with:"
echo "  uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload"
