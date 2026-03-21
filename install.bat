@echo off
chcp 65001 >nul
echo ============================================
echo   Установка Telegram-бота Qwen
echo ============================================
echo.

REM Проверка наличия Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python не найден! Установите Python 3.9+
    pause
    exit /b 1
)
echo [OK] Python найден

REM Создание виртуального окружения
if not exist venv (
    echo [INFO] Создание виртуального окружения...
    python -m venv venv
) else (
    echo [OK] Виртуальное окружение уже существует
)

REM Активация и установка зависимостей
echo [INFO] Установка зависимостей...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

REM Создание файла .env
if not exist .env (
    echo [INFO] Создание .env из шаблона...
    copy .env.example .env >nul
    echo.
    echo ============================================
    echo   ВНИМАНИЕ! Настройте .env перед запуском
    echo ============================================
    echo.
    echo Откройте .env и заполните:
    echo   1. BOT_TOKEN - токен от @BotFather
    echo   2. OWNER_ID - ваш Telegram ID (узнать в @userinfobot)
    echo.
) else (
    echo [OK] .env уже существует
)

echo.
echo ============================================
echo   Установка завершена!
echo ============================================
echo.
echo Для запуска:
echo   venv\Scripts\activate
echo   python main.py
echo.
pause
