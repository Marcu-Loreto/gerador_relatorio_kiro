#!/bin/bash
export PYTHONPATH=apps/backend
exec .venv/bin/python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
