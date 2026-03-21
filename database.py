"""
Модуль работы с базой данных SQLite.
Использует aiosqlite для асинхронной работы с БД.
"""

import aiosqlite
from datetime import datetime
from typing import Optional, List
from config import Config


class Database:
    """Класс для асинхронной работы с базой данных пользователей"""
    
    def __init__(self, db_path: str = None):
        """
        Инициализация подключения к БД.
        
        Args:
            db_path: Путь к файлу базы данных
        """
        self.db_path = str(db_path) if db_path else str(Config.DATABASE_PATH)
        self._connection: Optional[aiosqlite.Connection] = None
    
    async def connect(self) -> None:
        """Устанавливает соединение с базой данных и создаёт таблицы"""
        self._connection = await aiosqlite.connect(self.db_path)
        await self._create_tables()
    
    async def _create_tables(self) -> None:
        """Создаёт таблицу users если она не существует"""
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT NOT NULL,
                last_name TEXT,
                registered_at TIMESTAMP NOT NULL,
                last_active TIMESTAMP NOT NULL
            )
        """)
        await self._connection.commit()
    
    async def add_user(
        self,
        user_id: int,
        username: str,
        first_name: str,
        last_name: Optional[str] = None
    ) -> bool:
        """
        Добавляет нового пользователя или обновляет данные существующего.
        Использует INSERT OR REPLACE для избежания конфликтов UNIQUE.

        Args:
            user_id: Telegram ID пользователя
            username: Имя пользователя (username)
            first_name: Имя
            last_name: Фамилия (опционально)

        Returns:
            bool: True если пользователь новый, False если обновлён
        """
        now = datetime.now()

        # Проверяем существование пользователя
        cursor = await self._connection.execute(
            "SELECT user_id FROM users WHERE user_id = ?",
            (user_id,)
        )
        exists = await cursor.fetchone()
        await cursor.close()

        if exists:
            # Обновляем данные существующего пользователя
            await self._connection.execute("""
                UPDATE users SET
                    username = ?,
                    first_name = ?,
                    last_name = ?,
                    last_active = ?
                WHERE user_id = ?
            """, (username, first_name, last_name, now, user_id))
            await self._connection.commit()
            return False
        else:
            # Добавляем нового пользователя
            try:
                await self._connection.execute("""
                    INSERT INTO users (user_id, username, first_name, last_name, registered_at, last_active)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, username, first_name, last_name, now, now))
                await self._connection.commit()
                return True
            except aiosqlite.IntegrityError:
                # Если возник конфликт UNIQUE, обновляем вместо вставки
                await self._connection.execute("""
                    UPDATE users SET
                        username = ?,
                        first_name = ?,
                        last_name = ?,
                        last_active = ?
                    WHERE user_id = ?
                """, (username, first_name, last_name, now, user_id))
                await self._connection.commit()
                return False
    
    async def update_last_active(self, user_id: int) -> None:
        """
        Обновляет время последней активности пользователя.
        
        Args:
            user_id: Telegram ID пользователя
        """
        await self._connection.execute(
            "UPDATE users SET last_active = ? WHERE user_id = ?",
            (datetime.now(), user_id)
        )
        await self._connection.commit()
    
    async def get_all_users(self) -> List[dict]:
        """
        Получает список всех пользователей.
        
        Returns:
            List[dict]: Список словарей с данными пользователей
        """
        self._connection.row_factory = aiosqlite.Row
        cursor = await self._connection.execute(
            "SELECT * FROM users ORDER BY registered_at DESC"
        )
        rows = await cursor.fetchall()
        await cursor.close()
        
        users = []
        for row in rows:
            users.append({
                "user_id": row["user_id"],
                "username": row["username"],
                "first_name": row["first_name"],
                "last_name": row["last_name"],
                "registered_at": row["registered_at"],
                "last_active": row["last_active"]
            })
        
        self._connection.row_factory = None
        return users
    
    async def get_user_count(self) -> int:
        """
        Получает общее количество пользователей.
        
        Returns:
            int: Количество пользователей
        """
        cursor = await self._connection.execute("SELECT COUNT(*) FROM users")
        result = await cursor.fetchone()
        await cursor.close()
        return result[0]
    
    async def close(self) -> None:
        """Закрывает соединение с базой данных"""
        if self._connection:
            await self._connection.close()
