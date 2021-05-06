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
pip install --upgrade pdfplumber pandas requests pyperclip bs4 pdf2docx comtypes autopep8 flake8
echo.
echo All Packages Downloaded!
echo.
echo ==============================================
echo.
echo Running Python File...
echo.
python ./main.py
echo.
pause
exit