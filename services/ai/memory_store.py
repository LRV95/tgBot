# services/ai/memory_store.py
import sqlite3
import json
import logging
import time
from contextlib import contextmanager
from typing import Dict, List, Any, Optional, Union

logger = logging.getLogger(__name__)


class MemoryStore:
    """
    Хранилище долгосрочной памяти для AI-агентов, использующее SQLite
    """

    def __init__(self, db_path: str = "./database/memory.db"):
        """
        Инициализация хранилища памяти

        Args:
            db_path: Путь к файлу базы данных SQLite
        """
        self.db_path = db_path
        self._create_tables()

    @contextmanager
    def _connect(self):
        """
        Контекстный менеджер для соединения с базой данных

        Yields:
            sqlite3.Connection: Соединение с базой данных
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            yield conn
        finally:
            if conn:
                conn.close()

    def _create_tables(self):
        """Создает таблицы в базе данных, если они еще не существуют"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()

                # Таблица для хранения общей памяти
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS memory (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        agent_id TEXT NOT NULL,
                        key TEXT NOT NULL,
                        value TEXT NOT NULL,
                        metadata TEXT,
                        created_at REAL NOT NULL,
                        updated_at REAL NOT NULL,
                        expires_at REAL
                    )
                ''')

                # Индекс для быстрого поиска по agent_id и key
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_memory_agent_key
                    ON memory (agent_id, key)
                ''')

                # Таблица для хранения истории разговоров
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS conversation_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        message TEXT NOT NULL,
                        role TEXT NOT NULL,
                        timestamp REAL NOT NULL
                    )
                ''')

                # Индекс для быстрого поиска по user_id
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_conversation_user
                    ON conversation_history (user_id)
                ''')

                # Таблица для хранения цепочек рассуждений
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS reasoning_chains (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        agent_id TEXT NOT NULL,
                        query TEXT NOT NULL,
                        reasoning_steps TEXT NOT NULL,
                        result TEXT,
                        timestamp REAL NOT NULL
                    )
                ''')

                conn.commit()
        except Exception as e:
            logger.error(f"Ошибка при создании таблиц: {e}")

    def store(
            self,
            agent_id: str,
            key: str,
            value: Any,
            metadata: Dict = None,
            expires_at: float = None
    ) -> bool:
        """
        Сохраняет информацию в памяти

        Args:
            agent_id: Идентификатор агента
            key: Ключ для доступа к информации
            value: Значение для сохранения (будет преобразовано в JSON)
            metadata: Метаданные (будут преобразованы в JSON)
            expires_at: Время истечения срока действия (timestamp)

        Returns:
            bool: True в случае успеха, False в случае ошибки
        """
        try:
            now = time.time()

            # Преобразуем значение и метаданные в JSON
            value_json = json.dumps(value, ensure_ascii=False)
            metadata_json = json.dumps(metadata if metadata else {}, ensure_ascii=False)

            with self._connect() as conn:
                cursor = conn.cursor()

                # Проверяем, существует ли уже запись с таким agent_id и key
                cursor.execute(
                    "SELECT id FROM memory WHERE agent_id = ? AND key = ?",
                    (agent_id, key)
                )
                result = cursor.fetchone()

                if result:
                    # Обновляем существующую запись
                    cursor.execute(
                        '''
                        UPDATE memory 
                        SET value = ?, metadata = ?, updated_at = ?, expires_at = ?
                        WHERE agent_id = ? AND key = ?
                        ''',
                        (value_json, metadata_json, now, expires_at, agent_id, key)
                    )
                else:
                    # Создаем новую запись
                    cursor.execute(
                        '''
                        INSERT INTO memory 
                        (agent_id, key, value, metadata, created_at, updated_at, expires_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''',
                        (agent_id, key, value_json, metadata_json, now, now, expires_at)
                    )

                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении в память: {e}")
            return False

    def retrieve(
            self,
            agent_id: str,
            key: str = None,
            include_expired: bool = False
    ) -> Optional[Union[Any, Dict[str, Any]]]:
        """
        Извлекает информацию из памяти

        Args:
            agent_id: Идентификатор агента
            key: Ключ для доступа к информации (если None, возвращает все записи для агента)
            include_expired: Включать ли истекшие записи

        Returns:
            Optional[Union[Any, Dict[str, Any]]]: Извлеченная информация или словарь всех записей
        """
        try:
            now = time.time()

            with self._connect() as conn:
                cursor = conn.cursor()

                if key is not None:
                    # Извлекаем конкретную запись
                    if include_expired:
                        cursor.execute(
                            "SELECT value, metadata FROM memory WHERE agent_id = ? AND key = ?",
                            (agent_id, key)
                        )
                    else:
                        cursor.execute(
                            "SELECT value, metadata FROM memory WHERE agent_id = ? AND key = ? AND (expires_at IS NULL OR expires_at > ?)",
                            (agent_id, key, now)
                        )

                    result = cursor.fetchone()

                    if result:
                        value = json.loads(result['value'])
                        return value
                    return None
                else:
                    # Извлекаем все записи для агента
                    if include_expired:
                        cursor.execute(
                            "SELECT key, value, metadata FROM memory WHERE agent_id = ?",
                            (agent_id,)
                        )
                    else:
                        cursor.execute(
                            "SELECT key, value, metadata FROM memory WHERE agent_id = ? AND (expires_at IS NULL OR expires_at > ?)",
                            (agent_id, now)
                        )

                    results = cursor.fetchall()

                    if results:
                        memory_data = {}
                        for row in results:
                            memory_data[row['key']] = json.loads(row['value'])
                        return memory_data
                    return {}
        except Exception as e:
            logger.error(f"Ошибка при извлечении из памяти: {e}")
            return None

    def delete(self, agent_id: str, key: str = None) -> bool:
        """
        Удаляет информацию из памяти

        Args:
            agent_id: Идентификатор агента
            key: Ключ для доступа к информации (если None, удаляет все записи для агента)

        Returns:
            bool: True в случае успеха, False в случае ошибки
        """
        try:
            with self._connect() as conn:
                cursor = conn.cursor()

                if key is not None:
                    # Удаляем конкретную запись
                    cursor.execute(
                        "DELETE FROM memory WHERE agent_id = ? AND key = ?",
                        (agent_id, key)
                    )
                else:
                    # Удаляем все записи для агента
                    cursor.execute(
                        "DELETE FROM memory WHERE agent_id = ?",
                        (agent_id,)
                    )

                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при удалении из памяти: {e}")
            return False

    def store_conversation(self, user_id: int, message: str, role: str) -> bool:
        """
        Сохраняет сообщение из разговора в историю

        Args:
            user_id: ID пользователя
            message: Текст сообщения
            role: Роль отправителя ('user' или 'assistant')

        Returns:
            bool: True в случае успеха, False в случае ошибки
        """
        try:
            now = time.time()

            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''
                    INSERT INTO conversation_history 
                    (user_id, message, role, timestamp)
                    VALUES (?, ?, ?, ?)
                    ''',
                    (user_id, message, role, now)
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении разговора: {e}")
            return False

    def get_conversation_history(self, user_id: int, limit: int = 10) -> List[Dict]:
        """
        Получает историю разговора с пользователем

        Args:
            user_id: ID пользователя
            limit: Максимальное количество сообщений

        Returns:
            List[Dict]: История сообщений в формате [{role, content, timestamp}, ...]
        """
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''
                    SELECT message, role, timestamp 
                    FROM conversation_history 
                    WHERE user_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                    ''',
                    (user_id, limit)
                )

                results = cursor.fetchall()

                if results:
                    # Преобразуем результаты в подходящий формат и сортируем по времени
                    history = [
                        {
                            "role": row['role'],
                            "content": row['message'],
                            "timestamp": row['timestamp']
                        }
                        for row in results
                    ]
                    history.sort(key=lambda x: x["timestamp"])

                    # Удаляем timestamp, так как он не нужен для дальнейшей обработки
                    for item in history:
                        del item["timestamp"]

                    return history
                return []
        except Exception as e:
            logger.error(f"Ошибка при получении истории разговора: {e}")
            return []

    def store_reasoning_chain(self, agent_id: str, query: str, reasoning_steps: List[str], result: str = None) -> bool:
        """
        Сохраняет цепочку рассуждений агента

        Args:
            agent_id: Идентификатор агента
            query: Запрос пользователя
            reasoning_steps: Шаги рассуждения
            result: Результат рассуждения

        Returns:
            bool: True в случае успеха, False в случае ошибки
        """
        try:
            now = time.time()
            reasoning_json = json.dumps(reasoning_steps, ensure_ascii=False)

            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''
                    INSERT INTO reasoning_chains 
                    (agent_id, query, reasoning_steps, result, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                    ''',
                    (agent_id, query, reasoning_json, result, now)
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении цепочки рассуждений: {e}")
            return False

    def get_reasoning_chains(self, agent_id: str, limit: int = 5) -> List[Dict]:
        """
        Получает последние цепочки рассуждений агента

        Args:
            agent_id: Идентификатор агента
            limit: Максимальное количество цепочек

        Returns:
            List[Dict]: Цепочки рассуждений
        """
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''
                    SELECT query, reasoning_steps, result, timestamp 
                    FROM reasoning_chains 
                    WHERE agent_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                    ''',
                    (agent_id, limit)
                )

                results = cursor.fetchall()

                if results:
                    chains = [
                        {
                            "query": row['query'],
                            "reasoning_steps": json.loads(row['reasoning_steps']),
                            "result": row['result'],
                            "timestamp": row['timestamp']
                        }
                        for row in results
                    ]
                    return chains
                return []
        except Exception as e:
            logger.error(f"Ошибка при получении цепочек рассуждений: {e}")
            return []

    def get_conversation(self, user_id: int) -> List[Dict]:
        """
        Получает историю разговора с пользователем в формате, совместимом с UnifiedRAGAgent
        
        Args:
            user_id: ID пользователя
            
        Returns:
            List[Dict]: История сообщений в формате [{role, content}, ...]
        """
        try:
            return self.get_conversation_history(user_id, limit=20)
        except Exception as e:
            logger.error(f"Ошибка при получении истории разговора: {e}")
            return []
            
    def save_conversation(self, user_id: int, conversation: List[Dict]) -> bool:
        """
        Сохраняет историю разговора с пользователем
        
        Args:
            user_id: ID пользователя
            conversation: Список сообщений в формате [{role, content}, ...]
            
        Returns:
            bool: True в случае успеха, False в случае ошибки
        """
        try:
            # Очищаем старую историю
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM conversation_history WHERE user_id = ?",
                    (user_id,)
                )
                conn.commit()
                
            # Сохраняем новую историю
            for message in conversation:
                if "role" in message and "content" in message:
                    self.store_conversation(user_id, message["content"], message["role"])
                    
            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении истории разговора: {e}")
            return False