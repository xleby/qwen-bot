"""
Модуль конфигурации бота.
Загружает настройки из файла .env с использованием python-dotenv.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Определяем путь к директории с файлом .env
BASE_DIR = Path(__file__).parent

# Загружаем переменные окружения из файла .env
load_dotenv(BASE_DIR / ".env")


class Config:
    """Класс конфигурации бота с настройками из .env"""
    
    # Токен Telegram-бота (обязательный параметр)
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    
    # URL llama-server для OpenAI-compatible API
    LLAMA_SERVER_URL = os.getenv(
        "LLAMA_SERVER_URL", 
        "http://127.0.0.1:8080/v1/chat/completions"
    )
    
    # Telegram ID владельца бота (для админ-команд)
    OWNER_ID = int(os.getenv("OWNER_ID", "0"))
    
    # Режим обработки обычных сообщений как запросов к модели
    DEFAULT_MODE = os.getenv("DEFAULT_MODE", "true").lower() == "true"
    
    # Размер чанка для стриминга (символов)
    STREAM_CHUNK_SIZE = int(os.getenv("STREAM_CHUNK_SIZE", "50"))
    
    # Таймаут запроса к llama-server (секунды)
    # Для медленных локальных моделей с thinking рекомендуется 600-1200 секунд
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "600"))

    # Максимальное количество токенов в ответе
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", "8192"))

    # Режим thinking-модели (размышления)
    # true - показывать размышления модели
    # false - скрывать размышления
    SHOW_THINKING = os.getenv("SHOW_THINKING", "true").lower() == "true"

    # Rate limiting: максимум запросов в минуту от одного пользователя
    RATE_LIMIT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "10"))

    # Rate limiting: окно времени в минутах
    RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "1"))

    # Путь к файлу базы данных SQLite
    DATABASE_PATH = BASE_DIR / "bot_database.db"

    # Путь к файлу логов
    LOG_FILE = BASE_DIR / "bot.log"
    
    @classmethod
    def validate(cls) -> bool:
        """
        Проверяет наличие обязательных настроек.
        
        Returns:
            bool: True если все обязательные настройки присутствуют
        """
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN не найден в .env файле!")
        if cls.OWNER_ID == 0:
            raise ValueError("OWNER_ID не настроен! Укажите ваш Telegram ID.")
        return True
