import sqlite3
import os
import logging
from contextlib import contextmanager
from .exceptions import DatabaseError

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_name='./database/database.db'):
        self.db_name = db_name
        self._ensure_db_directory()
        self.create_tables()

    def _ensure_db_directory(self):
        """Проверяет и создает директорию для базы данных."""
        db_dir = os.path.dirname(self.db_name)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.db_name, check_same_thread=False, timeout=20)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        except sqlite3.Error as e:
            logger.error(f"Ошибка при подключении к базе данных: {e}")
            raise DatabaseError(f"Ошибка при подключении к базе данных: {e}")
        finally:
            if conn:
                conn.close()
    def create_tables(self):
        """Создает таблицы в базе данных."""
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY,
                        first_name TEXT,
                        telegram_tag TEXT DEFAULT '',
                        employee_number INTEGER,
                        role TEXT DEFAULT 'user',
                        score INTEGER DEFAULT 0,
                        registered_events TEXT DEFAULT '',
                        tags TEXT DEFAULT '',
                        city TEXT DEFAULT ''
                    )
                ''')

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS completed_events (
                        user_id INTEGER NOT NULL,
                        event_id INTEGER NOT NULL,
                        completed_date TEXT DEFAULT (datetime('now')),
                        PRIMARY KEY (user_id, event_id)
                    )
                ''')

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS projects (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL UNIQUE,
                        description TEXT,
                        responsible TEXT
                    )
                ''')

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        event_date TEXT NOT NULL,
                        start_time TEXT NOT NULL,
                        city TEXT NOT NULL,
                        creator TEXT NOT NULL,
                        description NOT NULL,
                        participation_points INTEGER DEFAULT 5 NOT NULL,
                        participants_count INTEGER DEFAULT 0 NOT NULL,
                        tags TEXT NOT NULL,
                        code TEXT NOT NULL,
                        owner TEXT NOT NULL,
                        project_id INTEGER DEFAULT NULL,
                        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL
                    )
                ''')

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS event_reports (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_id INTEGER NOT NULL,
                        report_date TEXT NOT NULL,
                        actual_participants INTEGER NOT NULL,
                        photos_links TEXT,
                        summary TEXT NOT NULL,
                        feedback TEXT,
                        FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
                    )
                ''')

                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Ошибка при создании таблиц: {e}")
            raise DatabaseError(f"Ошибка при создании таблиц: {e}")

    def get_all_events(self):
        """
        Получает все мероприятия из базы данных
        
        Returns:
            Список мероприятий
        """
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, name, description, event_date, start_time,
                           city, creator, participation_points, participants_count,
                           tags, code, owner
                    FROM events
                """)
                return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Ошибка при получении мероприятий: {e}")
            raise DatabaseError(f"Ошибка при получении мероприятий: {e}")

    def add_event(self, event_data: dict) -> int:
        """
        Добавляет новое мероприятие
        
        Args:
            event_data: Данные мероприятия
            
        Returns:
            ID созданного мероприятия
        """
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO events (
                        name, event_date, start_time, city, description,
                        tags, creator, code, owner
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event_data['name'],
                    event_data['date'],
                    event_data['time'],
                    event_data['city'],
                    event_data['description'],
                    event_data['tags'],
                    event_data.get('creator', 'system'),
                    event_data.get('code', ''),
                    event_data.get('owner', 'system')
                ))
                conn.commit()
                return cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"Ошибка при добавлении мероприятия: {e}")
            raise DatabaseError(f"Ошибка при добавлении мероприятия: {e}")

    def update_event(self, event_id: int, event_data: dict):
        """
        Обновляет существующее мероприятие
        
        Args:
            event_id: ID мероприятия
            event_data: Новые данные мероприятия
        """
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE events SET
                        name = ?,
                        event_date = ?,
                        start_time = ?,
                        city = ?,
                        description = ?,
                        tags = ?
                    WHERE id = ?
                """, (
                    event_data['name'],
                    event_data['date'],
                    event_data['time'],
                    event_data['city'],
                    event_data['description'],
                    event_data['tags'],
                    event_id
                ))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Ошибка при обновлении мероприятия: {e}")
            raise DatabaseError(f"Ошибка при обновлении мероприятия: {e}")

    def delete_event(self, event_id: int):
        """
        Удаляет мероприятие
        
        Args:
            event_id: ID мероприятия
        """
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Ошибка при удалении мероприятия: {e}")
            raise DatabaseError(f"Ошибка при удалении мероприятия: {e}") 