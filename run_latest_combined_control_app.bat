@echo off
setlocal

set "ENV_NAME=hit-mv-shrc203-combined"
set "APP=combined_hit_controller_v1.36.py"
set "CONDA_ACTIVATE=%ProgramData%\anaconda3\Scripts\activate.bat"

cd /d "%~dp0"

if not exist "%CONDA_ACTIVATE%" (
    echo Could not find Anaconda activation script:
    echo %CONDA_ACTIVATE%
    exit /b 1
)

call "%CONDA_ACTIVATE%" "%ENV_NAME%"
if errorlevel 1 (
    echo Failed to activate conda environment: %ENV_NAME%
    exit /b 1
)

python "%APP%"
