"""
Обработчики запросов к языковой модели.
"""

import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from llama_client import LlamaClient
from database import Database
from config import Config

logger = logging.getLogger(__name__)

router = Router()

# Глобальные экземпляры
llama_client: LlamaClient = None
db: Database = None


def init_handlers(client: LlamaClient, database: Database) -> None:
    """Инициализирует обработчики"""
    global llama_client, db
    llama_client = client
    db = database


async def process_query(message: Message, query: str, use_history: bool = True) -> None:
    """Обрабатывает запрос. Выводит токены пачками раз в 0.5 сек."""
    import asyncio
    user_id = message.from_user.id

    if db:
        await db.add_user(user_id=user_id, username=message.from_user.username,
            first_name=message.from_user.first_name, last_name=message.from_user.last_name)
        await db.update_last_active(user_id)

    logger.info(f"Запрос от пользователя {user_id}: {query[:50]}...")

    allowed, wait_time = llama_client.check_rate_limit(user_id)
    if not allowed:
        await message.answer(f"⏳ Много запросов! Ждите {wait_time} сек.")
        return

    # Проверяем, не генерирует ли бот уже для этого пользователя
    if llama_client.is_busy() and llama_client.get_current_user_id() == user_id:
        await message.answer("⏳ Ваш запрос ещё обрабатывается!")
        return

    status_msg = await message.answer("⏳ Обрабатываю...")
    thinking_msg = None
    answer_msg = None
    thinking_text = ""
    answer_text = ""
    last_update = 0

    # Проверяем очередь
    queue_position = llama_client.get_queue_size()
    if queue_position > 0:
        await status_msg.edit_text(f"⏳ Очередь. Позиция: #{queue_position + 1}")

    # Формируем сообщения с историей
    system_message = {"role": "system", "content": "Ты полезный ассистент."}
    user_message = {"role": "user", "content": query}

    # Получаем последние 3 сообщения из истории
    history = llama_client.get_user_history(user_id, limit=3) if use_history else []
    messages = [system_message] + history + [user_message]

    try:
        async for chunk in llama_client.chat_completion(messages, user_id=user_id, stream=True):
            if not isinstance(chunk, str):
                continue

            if chunk.startswith("QUEUE:"):
                pos = int(chunk.split(":")[1])
                if pos > 1:
                    await status_msg.edit_text(f"⏳ Очередь. Позиция: #{pos}")
                continue

            if chunk == "PROCESSING_START":
                await status_msg.edit_text("🔄 Обрабатываю...")
                continue

            if chunk == "THINKING_START":
                if Config.SHOW_THINKING:
                    thinking_msg = await message.answer("🤔 <b>Размышления...</b>\n\n<i>...</i>", parse_mode="HTML")
                continue

            if chunk.startswith("THINKING:"):
                thinking_text += chunk[9:]
                if Config.SHOW_THINKING and thinking_msg:
                    try:
                        await thinking_msg.edit_text(f"🤔 <b>Размышления...</b>\n\n<i>{thinking_text}</i>", parse_mode="HTML")
                    except:
                        pass
                continue

            if chunk == "THINKING_END":
                if Config.SHOW_THINKING and thinking_msg:
                    try:
                        await thinking_msg.edit_text(f"🤔 <b>Готово!</b>\n\n<i>{thinking_text}</i>\n\n📝 Ответ:", parse_mode="HTML")
                    except:
                        pass
                continue

            if chunk.startswith("CONTENT:"):
                answer_text += chunk[8:]
                now = asyncio.get_event_loop().time()
                # Выводим каждые 0.5 сек или если прошло много токенов
                if now - last_update >= 0.5 or len(chunk) >= 50:
                    if answer_msg is None:
                        if thinking_msg:
                            answer_msg = await message.answer(answer_text)
                        else:
                            await status_msg.edit_text(answer_text)
                            answer_msg = status_msg
                    else:
                        try:
                            await answer_msg.edit_text(answer_text)
                        except:
                            pass
                    last_update = now
                continue

        # Финальный вывод
        if answer_text:
            if answer_msg is None:
                await status_msg.edit_text(answer_text)
            elif answer_msg.text != answer_text:
                try:
                    await answer_msg.edit_text(answer_text)
                except:
                    pass
            
            # Сохраняем в историю
            llama_client.add_to_history(user_id, "user", query)
            llama_client.add_to_history(user_id, "assistant", answer_text)
        else:
            await status_msg.edit_text("⚠️ Пустой ответ.")

    except Exception as e:
        logger.error(f"Ошибка: {e}")
        error_text = f"❌ Ошибка: {str(e)}\n\nПопробуйте ещё раз! 🤗"
        if answer_msg:
            await answer_msg.edit_text(error_text)
        else:
            await status_msg.edit_text(error_text)


@router.message(Command("ask"))
async def cmd_ask(message: Message) -> None:
    """Команда /ask"""
    query = message.text.strip()
    if query.lower().startswith("/ask"):
        query = query[4:].strip()
    if not query:
        await message.answer("❌ Укажите вопрос после /ask")
        return
    await process_query(message, query)


@router.message(Command("clear"))
async def cmd_clear(message: Message) -> None:
    """Команда /clear — очистка истории переписки"""
    user_id = message.from_user.id
    await llama_client.clear_history(user_id)
    await message.answer("🗑️ История переписки очищена!")


@router.message(F.text & ~F.text.startswith("/"))
async def handle_message(message: Message) -> None:
    """Обычные сообщения"""
    if not Config.DEFAULT_MODE:
        return
    if message.from_user.is_bot:
        return
    await process_query(message, message.text)
