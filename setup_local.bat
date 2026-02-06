@echo off
REM Скрипт для настройки локального окружения (Windows)

echo Создание виртуального окружения...
python -m venv venv

echo Активация виртуального окружения...
call venv\Scripts\activate.bat

echo Установка зависимостей...
pip install --upgrade pip
pip install -r requirements.txt

echo.
echo Готово! Для активации окружения выполните: venv\Scripts\activate.bat
pause
