"""
Middleware для rate limiting (защита от DOS/спама).
Ограничивает количество запросов от одного пользователя в единицу времени.
"""

import logging
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable
from config import Config

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseMiddleware):
    """Middleware для ограничения частоты запросов"""

    def __init__(self):
        super().__init__()
        self.requests: Dict[int, list] = {}

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        """
        Проверяет rate limiting перед обработкой события.

        Args:
            handler: Обработчик события
            event: Событие (сообщение или callback)
            data: Данные события

        Returns:
            Результат работы обработчика или None если превышен лимит
        """
        # Получаем ID пользователя
        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id

        if user_id is None:
            return await handler(event, data)

        # Для владельца (OWNER_ID) лимиты не действуют
        from config import Config
        if user_id == Config.OWNER_ID:
            return await handler(event, data)

        # Проверяем лимит
        allowed, wait_time = self._check_rate_limit(user_id)

        if not allowed:
            logger.warning(f"Rate limit превышен для пользователя {user_id}. Ждать {wait_time} сек")
            # Пропускаем запрос, но не вызываем ошибку
            return None

        return await handler(event, data)

    def _check_rate_limit(self, user_id: int) -> tuple[bool, int]:
        """
        Проверяет, не превышен ли лимит запросов.

        Args:
            user_id: ID пользователя

        Returns:
            tuple[bool, int]: (можно ли делать запрос, сколько секунд ждать)
        """
        import time
        now = time.time()
        window_seconds = Config.RATE_LIMIT_WINDOW * 60

        if user_id not in self.requests:
            self.requests[user_id] = []

        # Удаляем старые запросы
        self.requests[user_id] = [
            ts for ts in self.requests[user_id]
            if now - ts < window_seconds
        ]

        # Проверяем лимит
        if len(self.requests[user_id]) >= Config.RATE_LIMIT_MAX_REQUESTS:
            oldest = min(self.requests[user_id])
            wait_time = int(window_seconds - (now - oldest))
            return False, max(1, wait_time)

        # Добавляем текущий запрос
        self.requests[user_id].append(now)
        return True, 0

    def clear(self) -> None:
        """Очищает все данные о запросах"""
        self.requests.clear()
