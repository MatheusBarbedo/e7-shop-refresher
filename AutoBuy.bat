@echo off
cd /d "%~dp0"

set "PYW=C:\Users\mathe\AppData\Local\Python\pythoncore-3.14-64\pythonw.exe"
if not exist "%PYW%" set "PYW=pythonw"

start "" "%PYW%" autobuy_gui.py
