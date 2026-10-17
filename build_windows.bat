@echo off
REM HP Browser - сборка портативного EXE для Windows (PyInstaller)
REM Автор: hypermarket

setlocal
cd /d "%~dp0"

echo === HP Browser: сборка Windows EXE ===
echo.

pyinstaller --version >nul 2>&1
if errorlevel 1 (
    echo PyInstaller не найден, устанавливаю...
    python -m pip install --upgrade pyinstaller
)

echo Устанавливаю зависимости...
python -m pip install -r requirements.txt

echo.
echo Собираю HP-Browser.exe ...
pyinstaller --noconfirm --clean --windowed --name HP-Browser ^
    --collect-all PyQt6 main.py

if errorlevel 1 (
    echo [ОШИБКА] Сборка не удалась.
    pause
    exit /b 1
)

echo.
echo Готово: dist\HP-Browser\HP-Browser.exe
echo.
pause
endlocal
