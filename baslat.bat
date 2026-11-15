@echo off
title PC Guvenlik ve Nobetci Botu (Sentinel Pro)
cd /d "%~dp0"
python app.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ========================================================
    echo [HATA] Uygulama calisirken bir sorun ile karsilasildi.
    echo ========================================================
    echo.
    pause
)
