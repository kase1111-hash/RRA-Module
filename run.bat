@echo off
REM SPDX-License-Identifier: FSL-1.1-ALv2
REM Copyright 2025 Kase Branham
REM
REM Run script for RRA Module on Windows.
REM Activates the virtual environment and runs the RRA CLI.

setlocal

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo Error: Virtual environment not found.
    echo.
    echo Please run build.bat first to set up the environment.
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Run the RRA CLI with all passed arguments
rra %*

endlocal
