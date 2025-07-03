@ECHO off
:repeat
cd ..
cd ..
.venv\Scripts\python.exe source/scripts/importer.py
set /p repeat="Do you want to repeat this? (y/n): "
if /i "%repeat%"=="y" goto repeat
pause
exit /b