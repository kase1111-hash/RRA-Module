@echo off
REM SPDX-License-Identifier: FSL-1.1-ALv2
REM Copyright 2025 Kase Branham
REM
REM Build script for RRA Module on Windows.
REM Sets up Python virtual environment and installs dependencies.

setlocal enabledelayedexpansion

echo === RRA Module Build ===
echo.

REM Check if Python is installed
where python >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH.
    echo.
    echo Install Python 3.9+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    exit /b 1
)

REM Check Python version
for /f "tokens=2 delims= " %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Found Python %PYTHON_VERSION%

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo.
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo Error: Failed to create virtual environment.
        exit /b 1
    )
    echo Virtual environment created.
) else (
    echo Virtual environment already exists.
)

REM Activate virtual environment
echo.
echo Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo Error: Failed to activate virtual environment.
    exit /b 1
)

REM Upgrade pip
echo.
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo.
echo Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo Error: Failed to install dependencies.
    exit /b 1
)

REM Install the package in development mode
echo.
echo Installing RRA Module in development mode...
pip install -e .
if errorlevel 1 (
    echo Error: Failed to install RRA Module.
    exit /b 1
)

echo.
echo === Build Complete ===
echo.
echo To activate the virtual environment, run:
echo   venv\Scripts\activate.bat
echo.
echo Then you can use the RRA CLI:
echo   rra --help
echo.
echo Or use run.bat to run commands directly:
echo   run.bat --help
echo.

REM Optional: Compile Solidity contracts if Foundry is available
where forge >nul 2>&1
if not errorlevel 1 (
    echo.
    echo Foundry detected. Compiling Solidity contracts...
    echo.
    pushd contracts

    REM Install dependencies if needed
    if not exist "lib\openzeppelin-contracts" (
        echo Installing OpenZeppelin contracts...
        forge install OpenZeppelin/openzeppelin-contracts --no-commit
    )

    echo Compiling contracts...
    forge build
    if errorlevel 1 (
        echo Warning: Contract compilation failed.
    ) else (
        echo Contracts compiled successfully.
    )

    popd
) else (
    echo.
    echo Note: Foundry not found. Solidity contracts will not be compiled.
    echo Install Foundry from https://book.getfoundry.sh/getting-started/installation
)

echo.
echo Done!

endlocal
