@echo off
setlocal

rem ============================================================
rem WallpaperGenerator - PyInstaller onedir build
rem ============================================================

cd /d "%~dp0"

echo.
echo [1/3] Checking PyInstaller...
python -m PyInstaller --version
if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller is not available in this Python environment.
    echo Install it with:
    echo     python -m pip install pyinstaller
    exit /b 1
)

echo.
echo [2/3] Cleaning previous build...
if exist "build" rmdir /s /q "build"
if exist "dist\WallpaperGenerator" rmdir /s /q "dist\WallpaperGenerator"

echo.
echo [3/3] Building WallpaperGenerator...
python -m PyInstaller --clean --noconfirm "WallpaperGenerator.spec"
if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller build failed.
    exit /b 1
)

echo.
echo ============================================================
echo Build completed.
echo.
echo Executable:
echo     %~dp0dist\WallpaperGenerator\WallpaperGenerator.exe
echo ============================================================
echo.

robocopy "plugins" "dist\plugins" /E > NUL
robocopy "samples" "dist\samples" /E > NUL

endlocal
