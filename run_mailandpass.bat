@echo off
cd /d "%~dp0"
set "PYTHON=%LocalAppData%\Programs\Python\Python313\python.exe"
if not exist "%PYTHON%" (
	echo Python 3.13 was not found at "%PYTHON%".
	pause
	exit /b 1
)
"%PYTHON%" "%~dp0emailandpass.py"
pause
