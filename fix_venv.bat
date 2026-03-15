@echo off
echo Fixing broken venv...
rmdir /s /q venv
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
echo Done! Please run Step 3 again.
