@echo off
setlocal EnableDelayedExpansion

if "%~1" neq "__inside_cmd" (
    cmd /k ""%~f0" __inside_cmd"
    exit /b
)
shift /1

:: =====================================================================
:: CONFIGURATION
:: =====================================================================
set "REQUIRED_PACKAGES=pygame-ce pysdl2 pysdl2-dll requests colorama pillow pyserial hidapi"
set "LOG_FILE=%~dp0build_pyinstaller_log.txt"

:: Metadata for EXE
set "APP_NAME=Prometheus82"
set "APP_VERSION="
set "COMPANY_NAME=Gamepadla"
set "FILE_DESCRIPTION=Prometheus 82 - Gamepad Latency Tester"
set "PRODUCT_NAME=Prometheus82"
set "LEGAL_COPYRIGHT=2026 Ivan Panchenko"

:: Initialize Log
chcp 65001 >nul
call :Log "Build started at %DATE% %TIME%" force_new

:: Path variables setup
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
for %%F in ("%SCRIPT_DIR%") do set "OUTPUT_NAME=%%~nxF"
call :Log "Using OUTPUT_NAME: %OUTPUT_NAME%"
:: Log Application Name
call :Log "Using application name: %APP_NAME%"

set "PYTHON_SCRIPT=%SCRIPT_DIR%\Python.py"
set "ICON_PNG_PATH=%SCRIPT_DIR%\icon.png"
set "TEMP_DIR=%TEMP%\%OUTPUT_NAME%Build_PyInstaller_%RANDOM%"
set "ICON_ICO_PATH=%TEMP_DIR%\icon.ico"
set "DIST_DIR=%SCRIPT_DIR%\dist"
set "BUILD_DIR=%SCRIPT_DIR%\build"

:: Universal Python search
call :FindPython
if "%PYTHON%"=="" call :ExitWithError "Python not found! Make sure Python is installed and added to PATH." & exit /b 1
call :Log "Found Python executable: %PYTHON%"
call :ReadAppVersion
if not defined APP_VERSION call :ExitWithError "Failed to read VERSION from Python.py!" & exit /b 1
call :Log "Using APP_VERSION from Python.py: %APP_VERSION%"

:: Create temporary directory structure
call :Log "Creating temporary directory structure..."
mkdir "%TEMP_DIR%" 2>nul

:: Create and activate virtual environment
call :Log "Creating virtual environment..."
set "VENV_DIR=%TEMP_DIR%\venv"
%PYTHON% -m venv "%VENV_DIR%" >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% neq 0 call :ExitWithError "Failed to create virtual environment!" & exit /b 1
call "%VENV_DIR%\Scripts\activate.bat"

:: Install packages
call :Log "Installing packages: %REQUIRED_PACKAGES% pyinstaller"
pip install --upgrade pip >> "%LOG_FILE%" 2>&1
pip install %REQUIRED_PACKAGES% pyinstaller >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% neq 0 call :ExitWithError "Failed to install packages!" & exit /b 1

:: Convert PNG to ICO
if exist "%ICON_PNG_PATH%" (
    call :Log "Converting icon.png to icon.ico..."
    python -c "from PIL import Image; img = Image.open(r'%ICON_PNG_PATH%').convert('RGBA'); sizes = [(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)]; img.save(r'%ICON_ICO_PATH%', format='ICO', sizes=sizes)" >> "%LOG_FILE%" 2>&1
)

:: Create Version Info file
call :Log "Generating Version Info file..."
set "VERSION_INFO_PATH=%TEMP_DIR%\version_info.txt"
set "PYTHON_GEN_VERSION=import sys; version_tuple = tuple(map(int, '%APP_VERSION%'.split('.'))); print(f'''VSVersionInfo(ffi=FixedFileInfo(filevers={version_tuple}, prodvers={version_tuple}, mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)), kids=[StringFileInfo([StringTable(u'040904B0', [StringStruct(u'CompanyName', u'%COMPANY_NAME%'), StringStruct(u'FileDescription', u'%FILE_DESCRIPTION%'), StringStruct(u'FileVersion', u'%APP_VERSION%'), StringStruct(u'InternalName', u'%APP_NAME%'), StringStruct(u'LegalCopyright', u'%LEGAL_COPYRIGHT%'), StringStruct(u'OriginalFilename', u'%APP_NAME%.exe'), StringStruct(u'ProductName', u'%PRODUCT_NAME%'), StringStruct(u'ProductVersion', u'%APP_VERSION%')])]), VarFileInfo([VarStruct(u'Translation', [1033, 1200])])])''')"
python -c "%PYTHON_GEN_VERSION%" > "%VERSION_INFO_PATH%"
if %ERRORLEVEL% neq 0 echo Check %LOG_FILE% for details & call :ExitWithError "Failed to generate Version Info file!" & exit /b 1

:: Find sdl2dll dll path
for /f "delims=" %%i in ('python -c "import os, sdl2dll; print(os.path.join(os.path.dirname(sdl2dll.__file__), 'dll'))"') do set "SDL2DLL_BIN_DIR=%%i"

:: Build PyInstaller Command
set "PYINSTALLER_CMD=pyinstaller --noconfirm --clean --onedir"
set "PYINSTALLER_CMD=!PYINSTALLER_CMD! --name "%APP_NAME%""
set "PYINSTALLER_CMD=!PYINSTALLER_CMD! --version-file "%VERSION_INFO_PATH%""
set "PYINSTALLER_CMD=!PYINSTALLER_CMD! --hidden-import=sdl2 --hidden-import=requests --hidden-import=PIL --hidden-import=colorama --hidden-import=serial --hidden-import=serial.tools --hidden-import=serial.tools.list_ports"
set "PYINSTALLER_CMD=!PYINSTALLER_CMD! --hidden-import=hid --hidden-import=steam_hid"
set "PYINSTALLER_CMD=!PYINSTALLER_CMD! --hidden-import=uuid --hidden-import=json --hidden-import=platform --hidden-import=ctypes --hidden-import=webbrowser --hidden-import=collections --hidden-import=datetime --hidden-import=pathlib"
if exist "%ICON_ICO_PATH%" set "PYINSTALLER_CMD=!PYINSTALLER_CMD! --icon "%ICON_ICO_PATH%""
set "PYINSTALLER_CMD=!PYINSTALLER_CMD! --add-data "%ICON_PNG_PATH%;.""
if defined SDL2DLL_BIN_DIR (
    set "PYINSTALLER_CMD=!PYINSTALLER_CMD! --add-data "%SDL2DLL_BIN_DIR%\SDL2.dll;sdl2dll\dll""
    set "PYINSTALLER_CMD=!PYINSTALLER_CMD! --add-data "%SDL2DLL_BIN_DIR%\SDL2_ttf.dll;sdl2dll\dll""
)
set "PYINSTALLER_CMD=!PYINSTALLER_CMD! "%PYTHON_SCRIPT%""

:: Execute PyInstaller
call :LogHeader "Running PyInstaller compilation..."
echo Full command: !PYINSTALLER_CMD!
echo Full command: !PYINSTALLER_CMD! >> "%LOG_FILE%"
!PYINSTALLER_CMD! >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% neq 0 echo Check %LOG_FILE% for details & call :ExitWithError "PyInstaller compilation failed!" & exit /b 1

:: Move Directory to script directory
call :Log "Moving build directory..."
if exist "%DIST_DIR%\%APP_NAME%" (
    if exist "%SCRIPT_DIR%\%APP_NAME%_PyInstaller" rd /s /q "%SCRIPT_DIR%\%APP_NAME%_PyInstaller"
    move /Y "%DIST_DIR%\%APP_NAME%" "%SCRIPT_DIR%\%APP_NAME%_PyInstaller" >nul
    call :Log "Created: %SCRIPT_DIR%\%APP_NAME%_PyInstaller"
    
    call :SignExe
    if !ERRORLEVEL! neq 0 exit /b 1
) else (
    call :ExitWithError "Output directory not found in dist folder!" & exit /b 1
)

:: Cleanup
call :Log "Cleaning up..."
if exist "%TEMP_DIR%" rd /s /q "%TEMP_DIR%"
if exist "%DIST_DIR%" rd /s /q "%DIST_DIR%"
if exist "%BUILD_DIR%" rd /s /q "%BUILD_DIR%"
if exist "%APP_NAME%.spec" del "%APP_NAME%.spec"

call :LogHeader "Build finished successfully!"
call :Log "Executable: %APP_NAME%_PyInstaller.exe"
pause
exit /b 0

:: =====================================================================
:: SUBROUTINES
:: =====================================================================

:Log
echo %~1
if "%~2"=="force_new" (
    echo %~1 > "%LOG_FILE%"
) else (
    echo %~1 >> "%LOG_FILE%"
)
exit /b 0

:LogHeader
echo.
echo =====================================================================
echo %~1
echo =====================================================================
echo.
echo ===================================================================== >> "%LOG_FILE%"
echo %~1 >> "%LOG_FILE%"
echo ===================================================================== >> "%LOG_FILE%"
exit /b 0

:ExitWithError
echo.
echo =====================================================================
echo Error: %~1
echo =====================================================================
echo Error: %~1 >> "%LOG_FILE%"
pause
exit /b 1

:ReadAppVersion
set "APP_VERSION="
for /f "usebackq tokens=1,* delims==" %%A in (`findstr /b /c:"VERSION" "%PYTHON_SCRIPT%"`) do (
    set "APP_VERSION=%%~B"
    for /f "tokens=1 delims=#" %%V in ("!APP_VERSION!") do set "APP_VERSION=%%~V"
    set "APP_VERSION=!APP_VERSION: =!"
    set "APP_VERSION=!APP_VERSION:"=!"
    exit /b 0
)
exit /b 0

:FindPython
set "PYTHON="
where py >nul 2>nul && set "PYTHON=py" || where python >nul 2>nul && set "PYTHON=python"
exit /b 0

:SignExe
call :LogHeader "Checking code signing certificate..."

powershell -ExecutionPolicy Bypass -Command "$now = Get-Date; $cert = Get-ChildItem -Path Cert:\CurrentUser\My -CodeSigningCert | Where-Object { $_.Subject -like '*Ivan Panchenko*' -and $_.HasPrivateKey -and $_.NotBefore -le $now -and $_.NotAfter -gt $now } | Sort-Object NotAfter -Descending | Select-Object -First 1; if (-not $cert) { exit 2 }; exit 0" >> "%LOG_FILE%" 2>&1

if %ERRORLEVEL% equ 2 (
    call :Log "No valid code signing certificate found. Skipping EXE signing."
    exit /b 0
)

call :Log "Signing EXE with YubiKey (a prompt for your PIN will appear)..."
powershell -ExecutionPolicy Bypass -Command "$now = Get-Date; $cert = Get-ChildItem -Path Cert:\CurrentUser\My -CodeSigningCert | Where-Object { $_.Subject -like '*Ivan Panchenko*' -and $_.HasPrivateKey -and $_.NotBefore -le $now -and $_.NotAfter -gt $now } | Sort-Object NotAfter -Descending | Select-Object -First 1; Set-AuthenticodeSignature -FilePath '%SCRIPT_DIR%\%APP_NAME%_PyInstaller\%APP_NAME%.exe' -Certificate $cert -TimestampServer 'http://timestamp.digicert.com'" >> "%LOG_FILE%" 2>&1

if %ERRORLEVEL% neq 0 (
    call :ExitWithError "Failed to sign EXE file! Make sure YubiKey is connected and you entered the correct PIN."
    exit /b 1
)

call :Log "EXE file signed successfully."
exit /b 0


