"""
Точка входа Telegram-бота.
Инициализирует все компоненты и запускает поллинг.
"""

import asyncio
import logging
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart

from config import Config
from database import Database
from llama_client import LlamaClient
from handlers import start, chat, admin
from handlers.chat import init_handlers
from handlers.admin import init_admin
from handlers.start import init_start


# Настраиваем логирование
def setup_logging() -> None:
    """Настраивает логирование в файл и консоль"""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Создаём обработчики
    file_handler = logging.FileHandler(Config.LOG_FILE, encoding="utf-8")
    console_handler = logging.StreamHandler()

    # Устанавливаем формат
    formatter = logging.Formatter(log_format)
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Настраиваем корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


async def on_startup(bot: Bot) -> None:
    """
    Выполняется при запуске бота.
    Регистрирует пользователя в БД.
    """
    logger = logging.getLogger(__name__)
    logger.info("Бот запущен")

    # Получаем информацию о боте
    bot_info = await bot.get_me()
    logger.info(f"Бот @{bot_info.username} готов к работе")


async def on_shutdown() -> None:
    """Выполняется при остановке бота"""
    logger = logging.getLogger(__name__)
    logger.info("Бот остановлен")


async def main() -> None:
    """Основная функция запуска бота"""

    # Настройка логирования
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        # Валидация конфигурации
        Config.validate()
        logger.info("Конфигурация загружена успешно")

    except ValueError as e:
        logger.error(f"Ошибка конфигурации: {e}")
        print(f"\n❌ Ошибка: {e}")
        print("\nСкопируйте .env.example в .env и заполните его:")
        print("  cp .env.example .env")
        sys.exit(1)

    # Инициализация базы данных
    db = Database()
    await db.connect()
    logger.info("База данных подключена")

    # Инициализация клиента llama-server
    llama_client = LlamaClient()
    logger.info(f"Подключение к llama-server: {Config.LLAMA_SERVER_URL}")

    # Создаём бота и диспетчер
    bot = Bot(
        token=Config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # Передаём зависимости в обработчики
    init_handlers(llama_client, db)
    init_admin(db)
    init_start(db)

    # Подключаем роутеры обработчиков
    # ВАЖНО: admin и start должны быть ПЕРЕД chat, иначе chat перехватит команды
    dp.include_router(admin.router)
    dp.include_router(start.router)
    dp.include_router(chat.router)

    # Регистрируем обработчики старта/остановки
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Сохраняем db в данные диспетчера для доступа из middleware
    dp["db"] = db

    # Проверяем сервер при запуске
    logger.info("Проверка доступности llama-server...")
    await llama_client.check_server()
    if llama_client.is_server_available:
        logger.info("llama-server доступен")
    else:
        logger.warning("llama-server недоступен, бот будет отвечать заглушкой")

    # Запускаем поллинг
    logger.info("Запуск поллинга...")

    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки (KeyboardInterrupt)")
    finally:
        # Graceful shutdown
        logger.info("Завершение работы...")
        await db.close()
        await llama_client.close()
        await bot.session.close()
        logger.info("Работа завершена")


if __name__ == "__main__":
    # Запуск с обработкой сигналов
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        sys.exit(1)
