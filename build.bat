@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo  E7 Shop Refresher - Build
echo ============================================

echo.
echo [1/3] Gerando icone...
python assets\gen_icon.py || (echo ERRO no icone & pause & exit /b 1)

echo.
echo [2/3] Empacotando o app com PyInstaller...
python -m PyInstaller --noconfirm --clean --windowed --name "E7ShopRefresher" ^
    --icon "assets\icon.ico" autobuy_gui.py || (echo ERRO no PyInstaller & pause & exit /b 1)

echo.
echo [3/3] Compilando o instalador com Inno Setup...
set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
"%ISCC%" installer.iss || (echo ERRO no Inno Setup & pause & exit /b 1)

echo.
echo ============================================
echo  OK! Instalador em: installer_output\
echo ============================================
pause
