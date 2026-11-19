@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  py -3.12 -m venv .venv
  if errorlevel 1 goto python_error
)
if not exist ".venv\bullbench-local-installed" (
  ".venv\Scripts\python.exe" -m pip install -r requirements-local.lock
  if errorlevel 1 goto install_error
  ".venv\Scripts\python.exe" -m pip install --no-deps -e .
  if errorlevel 1 goto install_error
  ".venv\Scripts\python.exe" -m pip check
  if errorlevel 1 goto install_error
  ".venv\Scripts\python.exe" scripts\run_local.py --check
  if errorlevel 1 goto install_error
  echo installed> ".venv\bullbench-local-installed"
)
".venv\Scripts\python.exe" scripts\run_local.py
if errorlevel 1 pause
exit /b
:python_error
echo Install 64-bit Python 3.12 from python.org, including the Python launcher, then try again.
pause
exit /b 1
:install_error
echo Setup did not finish. Read the error above. Internet access is needed for the first dependency installation.
pause
exit /b 1
