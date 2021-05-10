@echo off
rem UTF-8 で読み込む
chcp 65001
cls
title Update Support System for COVID-19 Ibaraki
echo Update Support System for COVID-19 Ibaraki
echo.
echo.
echo Downloading Python Packages...
echo.
echo ==============================================
echo.
python -m pip install --upgrade pip
pip install --upgrade -r requirements.txt
pip freeze > requirements.lock
echo.
echo All Packages Downloaded!
echo.
echo ==============================================
echo.
echo Running patients.py...
echo.
python ./patients.py
echo.
pause
echo ==============================================
echo.
echo Running summary.py...
echo.
python ./summary.py
echo.
pause
exit