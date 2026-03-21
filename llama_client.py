"""
Асинхронный клиент для llama-server с поддержкой стриминга и thinking-модели.
"""

import asyncio
import json
import logging
import time
from typing import AsyncGenerator, Optional
from aiohttp import ClientSession, ClientTimeout, ClientError
from config import Config

logger = logging.getLogger(__name__)


class LlamaClient:
    """Клиент для взаимодействия с llama-server"""

    def __init__(self):
        self.base_url = Config.LLAMA_SERVER_URL
        self.timeout = Config.REQUEST_TIMEOUT
        self._session: Optional[ClientSession] = None
        self._server_available: bool = False
        self._is_generating: bool = False
        self._request_queue: list[int] = []
        self._queue_lock = asyncio.Lock()
        self._rate_limits: dict[int, list] = {}
        self._current_user_id: Optional[int] = None
        self._user_histories: dict[int, list[dict]] = {}

    async def _get_session(self) -> ClientSession:
        if self._session is None or self._session.closed:
            # Таймаут устанавливается非常大ный — запрос может идти долго
            self._session = ClientSession(
                timeout=ClientTimeout(total=None, sock_read=None, sock_connect=30)
            )
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    def is_busy(self) -> bool:
        return self._is_generating

    def get_queue_size(self) -> int:
        return len(self._request_queue)

    def get_current_user_id(self) -> Optional[int]:
        return self._current_user_id

    def check_rate_limit(self, user_id: int) -> tuple[bool, int]:
        now = time.time()
        window_seconds = Config.RATE_LIMIT_WINDOW * 60

        if user_id not in self._rate_limits:
            self._rate_limits[user_id] = []

        self._rate_limits[user_id] = [
            ts for ts in self._rate_limits[user_id]
            if now - ts < window_seconds
        ]

        if len(self._rate_limits[user_id]) >= Config.RATE_LIMIT_MAX_REQUESTS:
            oldest = min(self._rate_limits[user_id])
            wait_time = int(window_seconds - (now - oldest))
            return False, max(1, wait_time)

        self._rate_limits[user_id].append(now)
        return True, 0

    async def add_to_queue(self, user_id: int) -> int:
        async with self._queue_lock:
            self._request_queue.append(user_id)
            position = len(self._request_queue)
            logger.info(f"Пользователь {user_id} добавлен в очередь, позиция: {position}")
            return position

    async def remove_from_queue(self, user_id: int) -> None:
        async with self._queue_lock:
            if user_id in self._request_queue:
                self._request_queue.remove(user_id)
                logger.info(f"Пользователь {user_id} удалён из очереди")

    def get_user_history(self, user_id: int, limit: int = 3) -> list[dict]:
        """Получает последние N сообщений пользователя из истории"""
        if user_id not in self._user_histories:
            self._user_histories[user_id] = []
        history = self._user_histories[user_id]
        return history[-limit:] if len(history) > limit else history

    def add_to_history(self, user_id: int, role: str, content: str) -> None:
        """Добавляет сообщение в историю пользователя"""
        if user_id not in self._user_histories:
            self._user_histories[user_id] = []
        self._user_histories[user_id].append({"role": role, "content": content})
        # Храним не более 20 сообщений на пользователя
        if len(self._user_histories[user_id]) > 20:
            self._user_histories[user_id] = self._user_histories[user_id][-20:]

    async def clear_history(self, user_id: int) -> None:
        """Очищает историю пользователя"""
        self._user_histories[user_id] = []
        logger.info(f"История пользователя {user_id} очищена")

    async def chat_completion(
        self,
        messages: list[dict],
        user_id: int,
        stream: bool = True
    ) -> AsyncGenerator[str, None]:
        """Отправляет запрос к llama-server"""
        async with self._queue_lock:
            self._request_queue.append(user_id)
            position = len(self._request_queue)
            logger.info(f"Пользователь {user_id} добавлен в очередь, позиция: {position}")

        # Отправляем позицию в очереди
        yield f"QUEUE:{position}"

        # Ждём очереди — пока не станем первыми и сервер не освободится
        last_position = position
        while True:
            async with self._queue_lock:
                is_first = len(self._request_queue) > 0 and self._request_queue[0] == user_id
                current_position = self._request_queue.index(user_id) + 1 if user_id in self._request_queue else position
            if is_first and not self._is_generating:
                break
            # Отправляем обновление позиции если изменилось
            if current_position != last_position:
                yield f"QUEUE:{current_position}"
                last_position = current_position
            await asyncio.sleep(0.5)

        # Начинаем генерацию
        self._is_generating = True
        self._current_user_id = user_id
        logger.info(f"Начало генерации для пользователя {user_id}")

        yield "PROCESSING_START"

        session = await self._get_session()
        payload = {
            "model": "default",
            "messages": messages,
            "stream": stream,
            "temperature": 0.7,
            "max_tokens": Config.MAX_TOKENS
        }

        try:
            async with session.post(
                self.base_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Ошибка сервера: {response.status} - {error_text}")
                    raise Exception(f"Ошибка сервера: {response.status}")

                logger.info(f"Получен ответ от сервера, статус: {response.status}")
                
                if stream:
                    async for chunk in self._parse_sse(response):
                        yield chunk
                else:
                    data = await response.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    if content:
                        yield f"CONTENT:{content}"

        except asyncio.CancelledError:
            logger.warning("Запрос отменён пользователем")
            raise Exception("Запрос отменён")
        except asyncio.TimeoutError:
            logger.error("Таймаут соединения")
            raise Exception("Сервер не отвечает... Проверьте llama-server")
        except ClientError as e:
            logger.error(f"Ошибка соединения: {e}")
            raise Exception("Не удалось подключиться к серверу...")
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            raise
        finally:
            self._is_generating = False
            self._current_user_id = None
            await self.remove_from_queue(user_id)
            logger.info(f"Генерация для пользователя {user_id} завершена")

    async def _parse_sse(self, response) -> AsyncGenerator[str, None]:
        """Парсит Server-Sent Events. Выводит токены сразу."""
        in_thinking = False
        chunk_count = 0
        
        async for line in response.content:
            try:
                line = line.decode("utf-8").strip()
            except UnicodeDecodeError:
                continue

            if not line or not line.startswith("data: "):
                continue

            data_str = line[6:]
            if data_str.strip() == "[DONE]":
                if in_thinking:
                    yield "THINKING_END"
                break

            try:
                data = json.loads(data_str)
                choices = data.get("choices", [])
                if not choices:
                    continue
                    
                delta = choices[0].get("delta", {})
                chunk_count += 1
                
                # Логируем первые 10 чанков для отладки
                if chunk_count <= 10:
                    logger.debug(f"Chunk {chunk_count}: {delta}")
                
                # Проверяем явный thinking_content
                thinking_content = delta.get("thinking_content")
                if thinking_content:
                    if not in_thinking:
                        in_thinking = True
                        yield "THINKING_START"
                    yield f"THINKING:{thinking_content}"
                    continue

                # Проверяем content
                content = delta.get("content")
                if content:
                    # Проверяем теги thinking в content
                    if "<think>" in content and not in_thinking:
                        in_thinking = True
                        yield "THINKING_START"
                        parts = content.split("<think>", 1)
                        if parts[0]:
                            yield f"CONTENT:{parts[0]}"
                        if "</think>" in parts[1]:
                            think, rest = parts[1].split("</think>", 1)
                            yield f"THINKING:{think}"
                            yield "THINKING_END"
                            in_thinking = False
                            if rest:
                                yield f"CONTENT:{rest}"
                        else:
                            yield f"THINKING:{parts[1]}"
                        continue
                    
                    if in_thinking:
                        # Проверяем окончание thinking
                        if "</think>" in content or "</thought>" in content.lower():
                            marker = "</think>" if "</think>" in content else "</thought>"
                            parts = content.split(marker, 1)
                            yield f"THINKING:{parts[0]}"
                            yield "THINKING_END"
                            in_thinking = False
                            if parts[1]:
                                yield f"CONTENT:{parts[1]}"
                        else:
                            yield f"THINKING:{content}"
                    else:
                        yield f"CONTENT:{content}"

            except json.JSONDecodeError as e:
                logger.debug(f"Ошибка JSON: {e}")
            except Exception as e:
                logger.error(f"Ошибка обработки: {e}")

        if in_thinking:
            yield "THINKING_END"

    async def check_server(self, force: bool = False) -> bool:
        """
        Проверяет доступность llama-server.
        
        Args:
            force: Если True, проверяет даже во время генерации
            
        Returns:
            bool: True если сервер доступен
        """
        if self._is_generating and not force:
            return True

        session = await self._get_session()
        try:
            base_url = self.base_url.replace("/v1/chat/completions", "")
            async with session.get(f"{base_url}/health", timeout=ClientTimeout(total=5)) as response:
                if response.status == 200:
                    self._server_available = True
                    return True
        except:
            pass

        try:
            base_url = self.base_url.replace("/v1/chat/completions", "")
            async with session.get(base_url, timeout=ClientTimeout(total=5)) as response:
                if response.status == 200:
                    self._server_available = True
                    return True
        except:
            pass

        self._server_available = False
        return False

    @property
    def is_server_available(self) -> bool:
        return self._server_available or self._is_generating
