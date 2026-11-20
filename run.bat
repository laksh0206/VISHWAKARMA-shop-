@echo off
title VISHWAKARMA HARDWARE & SANITARY - Pathankot, Punjab
color 0b
echo =========================================================================
echo   VISHWAKARMA HARDWARE & SANITARY - STOREFRONT & ADMIN PORTAL
echo   Owner: Yuvraj Saini  ^|  WhatsApp: 9855016374
echo   Location: Main Road, Adda Parmanand, Pathankot, Punjab
echo =========================================================================
echo.
echo Starting web server on http://localhost:8080 ...
echo Customer Storefront: http://localhost:8080
echo Admin Portal:        http://localhost:8080/admin
echo Admin PIN:           0206
echo.
echo Press Ctrl+C in this window anytime to stop the server.
echo.

start http://localhost:8080

python server.py 8080

pause
