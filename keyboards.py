"""
Модуль с клавиатурами для бота.
Содержит ReplyKeyboardMarkup и InlineKeyboardMarkup.
"""

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_commands_keyboard() -> ReplyKeyboardMarkup:
    """
    Создаёт клавиатуру с кнопкой "Команды".
    
    Returns:
        ReplyKeyboardMarkup: Клавиатура с кнопкой команд
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Команды")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    return keyboard


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """
    Создаёт основную клавиатуру с доступными командами.
    
    Returns:
        ReplyKeyboardMarkup: Основная клавиатура
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❓ Помощь")],
            [KeyboardButton(text="📋 Команды")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    return keyboard
