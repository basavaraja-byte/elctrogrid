@echo off
cd /d "%~dp0"
echo Starting DISPATCHGRID FastAPI Server on http://127.0.0.1:8000/docs ...
start "" "http://127.0.0.1:8000/docs"
".\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
pause

