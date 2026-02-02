@echo off
echo.
echo ================================
echo   Lingxi Knowledge Base - Auto Install and Demo
echo ================================
echo.

REM Check if Python is installed
python --version > nul 2>&1
if errorlevel 1 (
    echo Error: Python not found. Please install Python first.
    echo Visit https://www.python.org/downloads/ to download and install Python
    pause
    exit /b 1
)

echo Upgrading pip...
python -m pip install --upgrade pip

echo.
echo Installing/Updating dependencies from requirements.txt...
pip install -r requirements.txt --upgrade

echo.
echo Verifying required packages installation...
echo.

REM Verify chromadb installation
python -c "import chromadb" > nul 2>&1
if errorlevel 1 (
    echo Installing chromadb separately...
    pip install chromadb --upgrade
)

REM Verify sentence-transformers installation
python -c "import sentence_transformers" > nul 2>&1
if errorlevel 1 (
    echo Installing sentence-transformers separately...
    pip install sentence-transformers --upgrade
)

REM Verify python-dotenv installation
python -c "import dotenv" > nul 2>&1
if errorlevel 1 (
    echo Installing python-dotenv separately...
    pip install python-dotenv --upgrade
)

echo.
echo Starting Lingxi Knowledge Base demo...
echo.

REM Run the demo script
python lingxi_demo.py

echo.
echo Demo completed!
echo.
pause