@echo off
echo Starting Hospital Corridor AI Backend...
REM call myenv\Scripts\activate
REM Using python directly to avoid venv path issues
myenv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

