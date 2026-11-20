@echo off
title VISHWAKARMA HARDWARE & SANITARY - Admin Portal
color 0e
echo =========================================================================
echo   OPENING OWNER ADMIN PORTAL
echo   VISHWAKARMA HARDWARE & SANITARY
echo   Admin PIN: 0206
echo =========================================================================
echo.
echo Launching Admin Portal in your browser...
start http://localhost:8080/admin

echo.
echo Starting server (if not already running)...
python server.py 8080

pause
