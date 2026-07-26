@echo off
title Notion Live Analyzer Setup
echo =============================================
echo  Part 1: Install Python 3.11.9 (if needed)
echo =============================================
echo.
echo Python 3.11.9 is required. Checking if installed...
echo.

where python 2>nul >nul
if %errorlevel% equ 0 (
    python --version | find "3.11" >nul
    if %errorlevel% equ 0 (
        echo ✅ Python 3.11 found!
        goto :INSTALL_DEPS
    )
)

echo ⚠️  Python 3.11 not found. Opening download page...
echo.
echo 1. Download from: https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
echo 2. Run the installer
echo 3. IMPORTANT: CHECK "Add Python to PATH" at the bottom
echo 4. Click "Install Now"
echo 5. When done, close this window and re-run setup.bat
echo.
start https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
pause
exit /b

:INSTALL_DEPS
echo.
echo =============================================
echo  Part 2: Create Virtual Environment
echo =============================================
echo.

cd /d "%~dp0"

echo Creating virtual environment...
python -m venv .venv
if %errorlevel% neq 0 (
    echo ❌ Failed to create virtual environment
    pause
    exit /b
)
echo ✅ Virtual environment created

echo.
echo =============================================
echo  Part 3: Install Dependencies (fast wheels)
echo =============================================
echo.

.venv\Scripts\python.exe -m pip install --upgrade pip --quiet

echo Installing core packages (this will be fast with Python 3.11)...
.venv\Scripts\python.exe -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ❌ Some packages failed to install
    pause
    exit /b
)
echo ✅ All packages installed successfully!

echo.
echo =============================================
echo  Part 4: Launch App
echo =============================================
echo.
echo 🚀 Starting Streamlit app...
echo    App will open at: http://localhost:8501
echo.

.venv\Scripts\streamlit run app.py --server.address 0.0.0.0 --server.port 8501
pause
</｜DSML｜parameter>
