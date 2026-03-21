"""
Админ-команды для владельца бота.
Включает: /users, /test, /stats
"""

import logging
import time
import random
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from config import Config
from database import Database

logger = logging.getLogger(__name__)

router = Router()

# Глобальный экземпляр БД
db: Database = None

# Загадки для команды /test
RIDDLES = [
    {
        "question": "Зимой и летом одним цветом?",
        "answer": "Ёлка"
    },
    {
        "question": "Сидит дед, во сто шуб одет. Кто его раздевает, тот слёзы проливает?",
        "answer": "Лук"
    },
    {
        "question": "Висит груша, нельзя скушать?",
        "answer": "Лампочка"
    },
    {
        "question": "Не лает, не кусает, а в дом не пускает?",
        "answer": "Замок"
    },
    {
        "question": "Сначала вода, потом стекло, потом упало и исчезло?",
        "answer": "Сосулька"
    },
    {
        "question": "Красна девица сидит в темнице, а коса на улице?",
        "answer": "Морковь"
    },
    {
        "question": "Два конца, два кольца, посредине гвоздик?",
        "answer": "Ножницы"
    },
    {
        "question": "Маленький, серенький, на слона похож?",
        "answer": "Щенок"
    }
]


def init_admin(database: Database) -> None:
    """Инициализирует админ-команды"""
    global db
    db = database


def is_owner(user_id: int) -> bool:
    """Проверяет, является ли пользователь владельцем"""
    return user_id == Config.OWNER_ID


@router.message(Command("users"))
async def cmd_users(message: Message) -> None:
    """Показывает список всех пользователей (только для владельца)"""
    user_id = message.from_user.id

    if not is_owner(user_id):
        await message.answer("❌ Эта команда доступна только владельцу бота.", parse_mode=None)
        return

    if not db:
        await message.answer("❌ База данных не подключена.", parse_mode=None)
        return

    users = await db.get_all_users()
    count = len(users)

    if count == 0:
        await message.answer("📊 Пользователей пока нет.", parse_mode=None)
        return

    text = f"📊 Пользователи бота ({count})\n\n"

    for i, user in enumerate(users[:50], 1):
        username = user.get("username", "нет")
        first_name = user.get("first_name", "???")
        registered = user.get("registered_at", "???")
        last_active = user.get("last_active", "???")

        if registered and hasattr(registered, 'strftime'):
            registered = registered.strftime('%d.%m.%Y %H:%M')
        if last_active and hasattr(last_active, 'strftime'):
            last_active = last_active.strftime('%d.%m.%Y %H:%M')

        text += (
            f"{i}. {first_name} "
            f"(@{username}, ID: {user.get('user_id')})\n"
            f"   Зарегистрирован: {registered}\n"
            f"   Активен: {last_active}\n\n"
        )

    if count > 50:
        text += f"... и ещё {count - 50} пользователей."

    await message.answer(text, parse_mode=None)


@router.message(Command("test"))
async def cmd_test(message: Message) -> None:
    """
    Тестовый запрос для всех пользователей.
    Загадывает случайную загадку и проверяет ответ модели.
    """
    user_id = message.from_user.id

    # Выбираем случайную загадку
    riddle = random.choice(RIDDLES)
    
    await message.answer(
        f"🧪 <b>Тестирование бота</b>\n\n"
        f"📝 <b>Загадка:</b>\n"
        f"<i>{riddle['question']}</i>\n\n"
        f"Спрашиваю у модели... ⏱️",
        parse_mode="HTML"
    )

    from llama_client import LlamaClient

    test_client = LlamaClient()
    await test_client._get_session()

    # Проверяем сервер
    server_ok = await test_client.check_server()
    if not server_ok:
        await message.answer(
            "❌ llama-server недоступен.\n"
            "Проверьте, что сервер запущен.",
            parse_mode=None
        )
        await test_client.close()
        return

    # Тестовый запрос с загадкой
    test_query = f"Загадка: {riddle['question']}. Дай краткий ответ, что это?"
    messages = [
        {"role": "system", "content": "Ты полезный ассистент. Отвечай кратко."},
        {"role": "user", "content": test_query}
    ]

    start_time = time.time()
    first_token_time = None
    tokens_count = 0
    full_response = ""

    try:
        async for chunk in test_client.chat_completion(messages, user_id=user_id, stream=True):
            if isinstance(chunk, str) and chunk.startswith("CONTENT:"):
                content = chunk[8:]
                tokens_count += 1
                full_response += content

                if first_token_time is None:
                    first_token_time = time.time()

        end_time = time.time()
        total_time = end_time - start_time
        time_to_first_token = (first_token_time - start_time) if first_token_time else 0
        tokens_per_second = tokens_count / total_time if total_time > 0 else 0

        # Правильный ответ
        correct_answer = riddle['answer']

        stats_text = (
            f"✅ <b>Тест завершён!</b>\n\n"
            f"📊 <b>Результаты:</b>\n"
            f"• Время до первого токена: {time_to_first_token:.2f} сек\n"
            f"• Общее время: {total_time:.2f} сек\n"
            f"• Токенов сгенерировано: {tokens_count}\n"
            f"• Скорость: {tokens_per_second:.2f} ток/сек\n\n"
            f"📝 <b>Загадка:</b> {riddle['question']}\n"
            f"💡 <b>Правильный ответ:</b> {correct_answer}\n\n"
            f"🤖 <b>Ответ модели:</b>\n"
            f"{full_response}"
        )

        await message.answer(stats_text, parse_mode="HTML")

    except Exception as e:
        await message.answer(f"❌ Ошибка теста:\n\n{str(e)}", parse_mode=None)

    finally:
        await test_client.close()


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    """Показывает статистику бота (только для владельца)"""
    user_id = message.from_user.id

    if not is_owner(user_id):
        await message.answer("❌ Эта команда доступна только владельцу бота.", parse_mode=None)
        return

    if not db:
        await message.answer("❌ База данных не подключена.", parse_mode=None)
        return

    total_users = await db.get_user_count()
    from llama_client import LlamaClient

    stats_text = (
        f"📊 Статистика бота\n\n"
        f"👥 Пользователей: {total_users}\n"
        f"🔗 Статус сервера: {'✅ Доступен' if LlamaClient().is_server_available else '❌ Недоступен'}\n"
        f"⏳ Очередь: {LlamaClient().get_queue_size()} запросов\n\n"
        f"🔧 Настройки:\n"
        f"• Таймаут: {Config.REQUEST_TIMEOUT} сек\n"
        f"• Rate limit: {Config.RATE_LIMIT_MAX_REQUESTS} запросов в {Config.RATE_LIMIT_WINDOW} мин\n"
        f"• Thinking: {'включён' if Config.SHOW_THINKING else 'выключен'}"
    )

    await message.answer(stats_text, parse_mode=None)
