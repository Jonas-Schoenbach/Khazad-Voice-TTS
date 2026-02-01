@echo off
title LOTRO Narrator Installer
color 0A

echo ==================================================
echo      LOTRO NARRATOR - FIRST TIME SETUP
echo ==================================================
echo.

:: --- 1. Tool Checks (Git & Python) ---

:: Check for Git
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Git is not installed or not in PATH.
    echo Please download Git for Windows: https://git-scm.com/download/win
    echo.
    pause
    exit
)

:: Try to find Python 3.12
set PYTHON_CMD=python

:: Check if 'py' launcher is available and try to prefer 3.12
py -3.12 --version >nul 2>&1
if %errorlevel%==0 (
    echo [INFO] Found Python 3.12 via launcher.
    set PYTHON_CMD=py -3.12
    goto :FOUND_PYTHON
)

:: Fallback to default 'python' command
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.12 from python.org and tick "Add to PATH".
    pause
    exit
)

:FOUND_PYTHON
echo Using Python: 
%PYTHON_CMD% --version

:: Verify it is actually 3.12 (warn if not)
for /f "tokens=2" %%v in ('%PYTHON_CMD% --version 2^>^&1') do set PV=%%v
if not "%PV:~0,4%"=="3.12" (
    echo.
    echo [WARNING] You are using Python %PV%.
    echo We strictly recommend Python 3.12 for this project.
    echo If installation fails, please install Python 3.12.10.
    echo.
    pause
)

:: --- 2. Environment Setup ---
echo.
echo [1/5] Creating Virtual Environment...
%PYTHON_CMD% -m venv venv

echo [2/5] Activating Environment...
call venv\Scripts\activate

echo [3/5] Updating Setup Tools...
python -m pip install --upgrade pip setuptools wheel

echo.
echo ==================================================
echo           SELECT YOUR GPU DRIVER VERSION
echo ==================================================
echo PyTorch needs to match your computer's video card drivers.
echo.
echo [1] CUDA 12.1 Standard NVIDIA GPUs (Recommended RTX 40-Series, 30-Series, 20-Series, GTX 16xx/10xx)
echo [2] CUDA 12.8 Nightly (Required for new RTX 50-Series (RTX 5070, 5080, 5090))
echo [3] CPU Only  (Slow, not recommended for LuxTTS)
echo.
set /p choice="Enter selection [1, 2, or 3]: "

if "%choice%"=="1" (
    echo.
    echo Installing PyTorch for CUDA 12.1...
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
) else if "%choice%"=="2" (
    echo.
    echo Installing PyTorch for CUDA 12.8 Nightly...
    pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128
) else (
    echo.
    echo Installing PyTorch for CPU...
    pip install torch torchvision torchaudio
)

:: --- 3. LuxTTS Setup (NEW) ---
echo.
echo [4/5] Setting up LuxTTS...

if not exist "LuxTTS" (
    echo Cloning LuxTTS repository...
    git clone https://github.com/ysharma3501/LuxTTS.git
)

:: Enter folder and set specific commit
cd LuxTTS
echo Checking out optimization commit (Skip Whisper)...
git checkout f3810f535fbb09e18902964270753c3a406a1c9c
cd ..

if exist "LuxTTS\requirements.txt" (
    echo Installing LuxTTS dependencies...
    pip install -r LuxTTS\requirements.txt
)

:: --- 4. Main Requirements ---
echo.
echo [5/5] Installing Main Project Requirements...
pip install -r requirements.txt

echo.
echo ==================================================
echo           INSTALLATION COMPLETE!
echo ==================================================
echo You can now use "start.bat" to run the program.
pause