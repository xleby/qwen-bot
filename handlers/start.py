"""
Обработчики команд /start и /help.
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from keyboards import get_main_keyboard, get_commands_keyboard

logger = logging.getLogger(__name__)

# Создаём роутер для этих обработчиков
router = Router()

# Глобальная переменная для БД
db = None


def init_start(database) -> None:
    """Инициализирует обработчик start, передавая зависимости"""
    global db
    db = database


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    """Обработчик команды /start"""
    user = message.from_user
    first_name = user.first_name or "Пользователь"

    # Регистрируем пользователя в БД
    if db:
        await db.add_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        logger.info(f"Пользователь {user.id} ({user.username}) зарегистрирован в БД")

    welcome_text = (
        f"👋 Привет, {first_name}!\n\n"
        f"Я бот для общения с локальной языковой моделью Qwen.\n"
        f"Вы можете задавать мне вопросы, и я постараюсь ответить.\n\n"
        f"📋 Нажмите кнопку ниже, чтобы увидеть доступные команды."
    )

    await message.answer(
        text=welcome_text,
        reply_markup=get_main_keyboard(),
        parse_mode=None
    )

    logger.info(f"Пользователь {user.id} ({user.username}) запустил бота")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Обработчик команды /help"""
    help_text = (
        "📖 Справка по боту\n\n"
        "🔹 Доступные команды:\n"
        "/start - Запустить бота\n"
        "/help - Показать эту справку\n"
        "/ask <текст> - Задать вопрос модели\n"
        "/test - Тест с загадкой (для всех)\n"
        "/commands - Показать кнопки команд\n"
        "/users - Список пользователей (владелец)\n"
        "/stats - Статистика бота (владелец)\n\n"
        "🔹 Как использовать:\n"
        "Просто отправьте сообщение боту, и он передаст его модели.\n"
        "Ответ будет приходить постепенно.\n\n"
        "🔹 Кнопки:\n"
        "• 📋 Команды - показать список команд\n"
        "• ❓ Помощь - вызвать справку"
    )

    await message.answer(text=help_text, parse_mode=None)
    logger.info(f"Пользователь {message.from_user.id} запросил справку")


@router.message(F.text == "❓ Помощь")
async def btn_help(message: Message) -> None:
    """Обработчик кнопки 'Помощь'"""
    await cmd_help(message)


@router.message(F.text == "📋 Команды")
async def btn_commands(message: Message) -> None:
    """Обработчик кнопки 'Команды'"""
    commands_text = (
        "📋 Доступные команды:\n\n"
        "/start - Запустить бота\n"
        "/help - Справочная информация\n"
        "/ask <текст> - Задать вопрос модели\n"
        "/test - Тест с загадкой (для всех)\n"
        "/commands - Показать эту клавиатуру\n"
        "/users - Список пользователей (владелец)\n"
        "/stats - Статистика (владелец)\n\n"
        "💡 Вы также можете просто написать сообщение - "
        "оно будет отправлено модели."
    )

    await message.answer(
        text=commands_text,
        parse_mode=None,
        reply_markup=get_commands_keyboard()
    )
