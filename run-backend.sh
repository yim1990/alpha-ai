cd /Users/jasonim/cursor-workspace/alpha-ai
PYTHONPATH=/Users/jasonim/cursor-workspace/alpha-ai
lsof -ti:8000 | xargs kill -9
poetry run uvicorn app.backend.main:app --reload --host 0.0.0.0 --port 8000