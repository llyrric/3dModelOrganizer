@echo off
title 3D Printing Library Organizer Server
cd /d "%~dp0"
echo =====================================================================
echo   Starting 3D Printing Library Organizer Live Server
echo   Allows instant 1-click file moving and category reassignments
echo =====================================================================
echo.
start http://localhost:8000
python server.py
pause
