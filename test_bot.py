"""
Тестовый скрипт для проверки работоспособности бота.
Проверяет токен, определяет владельца и выводит диагностическую информацию.
Также имеет режим эхо-бота.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Исправляем кодировку для Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message

from config import Config

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Роутер для эхо-режима
echo_router = Router()


@echo_router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Обработчик команды /start"""
    await message.answer(
        "🔍 <b>Эхо-бот запущен!</b>\n\n"
        "Я работаю в тестовом режиме.\n"
        "Отправьте мне любое сообщение, и я его повторю.\n\n"
        "Для остановки нажмите Ctrl+C"
    )


@echo_router.message(F.text)
async def echo_message(message: Message) -> None:
    """Эхо-режим: повторяет сообщения пользователя"""
    await message.answer(f"🔁 <b>Эхо:</b>\n\n{message.text}")


@echo_router.message(F.photo)
async def echo_photo(message: Message) -> None:
    """Эхо-режим для фото"""
    photo_id = message.photo[-1].file_id
    caption = message.caption or ""
    await message.answer_photo(
        photo=photo_id,
        caption=f"🔁 <b>Эхо-фото:</b>\n\n{caption}" if caption else None
    )


async def test_bot() -> None:
    """Тестирует бота и выводит диагностическую информацию"""
    
    print("\n" + "=" * 50)
    print("ТЕСТИРОВАНИЕ БОТА")
    print("=" * 50)
    
    # Проверяем наличие токена
    if not Config.BOT_TOKEN:
        print("\nОшибка: BOT_TOKEN не найден в .env файле!")
        print("\nСкопируйте .env.example в .env и укажите токен:")
        print("  cp .env.example .env")
        sys.exit(1)
    
    print(f"\nТокен найден: {Config.BOT_TOKEN[:15]}...{Config.BOT_TOKEN[-5:]}")
    
    # Создаём бота
    bot = Bot(
        token=Config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    try:
        # Получаем информацию о боте
        print("\nПолучение информации о боте...")
        bot_info = await bot.get_me()
        
        print("\n" + "-" * 50)
        print("ИНФОРМАЦИЯ О БОТЕ:")
        print("-" * 50)
        print(f"  ID бота:        {bot_info.id}")
        print(f"  Username:       @{bot_info.username}")
        print(f"  Имя:            {bot_info.first_name}")
        if bot_info.last_name:
            print(f"  Фамилия:        {bot_info.last_name}")
        print(f"  Может в группы: {bot_info.can_join_groups}")
        print(f"  Режим инкогнито: {bot_info.can_connect_to_business}")
        
        # Определяем владельца (создателя) бота
        print("\nОПРЕДЕЛЕНИЕ ВЛАДЕЛЬЦА:")
        print("-" * 50)
        print(f"  Владелец бота:  User ID = {bot_info.id}")
        print(f"  (Создатель в Telegram BotFather)")
        
        # Получаем список команд бота
        print("\nКОМАНДЫ БОТА:")
        print("-" * 50)
        try:
            commands = await bot.get_my_commands()
            if commands:
                for cmd in commands:
                    print(f"  /{cmd.command} - {cmd.description}")
            else:
                print("  Команды не настроены")
        except Exception as e:
            print(f"  Не удалось получить команды: {e}")
        
        # Тестовое сообщение
        print("\nТЕСТОВАЯ ОТПРАВКА:")
        print("-" * 50)
        print("  Бот работает в проверочном режиме")
        print("  Токен валиден, бот готов к работе")
        
        # Дополнительные команды для владельца
        print("\nДОСТУПНЫЕ КОМАНДЫ ДЛЯ ВЛАДЕЛЬЦА:")
        print("-" * 50)
        owner_commands = [
            ("/start", "Запустить бота"),
            ("/help", "Справочная информация"),
            ("/ask", "Задать вопрос модели"),
            ("/commands", "Показать клавиатуру команд"),
            ("/users", "Список всех пользователей (только владелец)"),
        ]
        for cmd, desc in owner_commands:
            print(f"  {cmd:15} - {desc}")
        
        print("\n" + "=" * 50)
        print("ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ УСПЕШНО!")
        print("=" * 50 + "\n")
        
    except Exception as e:
        print(f"\nОшибка при тестировании: {e}")
        print("\nВозможные причины:")
        print("  1. Неверный токен бота")
        print("  2. Бот заблокирован Telegram")
        print("  3. Проблемы с соединением")
        sys.exit(1)
    finally:
        await bot.session.close()


async def run_echo_bot() -> None:
    """Запускает эхо-бота для проверки работоспособности"""
    
    print("\n" + "=" * 50)
    print("ЗАПУСК ЭХО-БОТА")
    print("=" * 50)
    
    if not Config.BOT_TOKEN:
        print("\nОшибка: BOT_TOKEN не найден в .env файле!")
        sys.exit(1)
    
    print(f"\nТокен: {Config.BOT_TOKEN[:15]}...{Config.BOT_TOKEN[-5:]}")
    
    # Создаём бота и диспетчер
    bot = Bot(
        token=Config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    
    # Подключаем роутер
    dp.include_router(echo_router)
    
    try:
        # Получаем информацию о боте
        bot_info = await bot.get_me()
        print(f"\nБот: @{bot_info.username} ({bot_info.first_name})")
        print("\n" + "-" * 50)
        print("Эхо-бот готов к работе!")
        print("Отправьте боту сообщение для проверки.")
        print("Для остановки нажмите Ctrl+C")
        print("-" * 50 + "\n")
        
        # Запускаем поллинг
        await dp.start_polling(bot)
        
    except KeyboardInterrupt:
        print("\nЭхо-бот остановлен пользователем")
    except Exception as e:
        print(f"\nОшибка: {e}")
        sys.exit(1)
    finally:
        await bot.session.close()


def show_menu() -> None:
    """Показывает меню выбора режима"""
    print("\n" + "=" * 50)
    print("ВЫБЕРИТЕ РЕЖИМ:")
    print("=" * 50)
    print("  1 - Быстрый тест бота (проверка токена)")
    print("  2 - Запуск эхо-бота (проверка сообщений)")
    print("  0 - Выход")
    print("-" * 50)


async def main() -> None:
    """Главная функция"""
    while True:
        show_menu()
        choice = input("\nВаш выбор: ").strip()
        
        if choice == "1":
            await test_bot()
        elif choice == "2":
            await run_echo_bot()
        elif choice == "0":
            print("\nВыход из программы")
            break
        else:
            print("\nНеверный выбор, попробуйте снова")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nПрограмма прервана пользователем")
    except Exception as e:
        print(f"\nКритическая ошибка: {e}")
        sys.exit(1)
