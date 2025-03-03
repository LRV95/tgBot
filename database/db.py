import sqlite3
import os
import logging
from contextlib import contextmanager
from datetime import datetime

logger = logging.getLogger(__name__)

class DatabaseError(Exception):
    """Базовый класс для ошибок базы данных."""
    pass

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
        """Контекстный менеджер для соединения с базой данных."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_name, check_same_thread=False, timeout=20)
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
                        owner TEXT NOT NULL
                    )
                ''')

                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Ошибка при создании таблиц: {e}")
            raise DatabaseError(f"Ошибка при создании таблиц: {e}")

    def _format_event(self, row):
        return {
            "id": row[0],
            "name": row[1],
            "event_date": row[2],
            "start_time": row[3],
            "city": row[4],
            "creator": row[5],
            "description": row[6],
            "participation_points": row[7],
            "participants_count": row[8],
            "tags": row[9],
            "code": row[10],
            "owner": row[11]
        }

    def get_all_events(self):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM events")
            rows = cursor.fetchall()
            return [self._format_event(row) for row in rows]

    def add_event(self, name, event_date, start_time, city, creator, description, participation_points, tags, code, owner=""):
        """Добавляет новое мероприятие в базу данных."""
        # Валидация обязательных полей
        if not all([name, event_date, start_time, city, creator, description, participation_points, tags, code, owner]):
            raise ValueError("Отсутствуют обязательные поля")

        # Валидация даты и времени
        try:
            datetime.strptime(event_date, "%Y-%m-%d")
            datetime.strptime(start_time, "%H:%M")
        except ValueError as e:
            raise ValueError(f"Неверный формат даты или времени: {str(e)}")

        # Валидация числовых значений
        if int(participation_points) < 0:
            raise ValueError("Баллы должны быть неотрицательными")

        with self.connect() as conn:
            cursor = conn.cursor()
            try:
                # Проверяем уникальность кода мероприятия, если он указан
                if code:
                    cursor.execute("SELECT id FROM events WHERE code = ?", (code,))
                    if cursor.fetchone():
                        raise sqlite3.IntegrityError("Мероприятие с таким кодом уже существует")

                participants_count = 0
                cursor.execute('''
                    INSERT INTO events (
                        name, event_date, start_time, city, creator, 
                        description, participation_points, participants_count, 
                        tags, code, owner
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    name, event_date, start_time, city, creator,
                    description, participation_points, participants_count,
                    tags, code, owner
                ))
                conn.commit()
                return cursor.lastrowid
            except sqlite3.IntegrityError as e:
                conn.rollback()
                raise DatabaseError(f"Ошибка при добавлении мероприятия: {str(e)}")
            except Exception as e:
                conn.rollback()
                logger.error(f"Неожиданная ошибка при добавлении мероприятия: {e}")
                raise DatabaseError(f"Неожиданная ошибка при добавлении мероприятия: {str(e)}")

    def get_user(self, user_id):
        """Получает информацию о пользователе."""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, first_name, role, score, registered_events, tags, city FROM users WHERE id = ?', (user_id,))
            user = cursor.fetchone()
            if user:
                logger.info(f"Получен пользователь из БД: id={user[0]}, first_name={user[1]}, role={user[2]}")
                return {
                    "id": user[0],
                    "first_name": user[1],
                    "role": user[2],
                    "score": user[3],
                    "registered_events": user[4],
                    "tags": user[5],
                    "city": user[6]
                }
            logger.info(f"Пользователь с id={user_id} не найден в БД")
            return None

    def save_user(self, user_id, first_name=None, role="user", telegram_tag="", employee_number=None):
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                existing_user = self.get_user(user_id)
                if existing_user:
                    cursor.execute('''
                        UPDATE users 
                        SET first_name = ?,
                            role = ?,
                            telegram_tag = ?,
                            employee_number = ?
                        WHERE id = ?
                    ''', (first_name, role, telegram_tag, employee_number, user_id))
                else:
                    cursor.execute('''
                        INSERT INTO users 
                        (id, first_name, telegram_tag, employee_number, role, score, registered_events, tags, city)
                        VALUES (?, ?, ?, ?, ?, 0, '', '', '')
                    ''', (user_id, first_name, telegram_tag, employee_number, role))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Ошибка при сохранении пользователя: {e}")
            raise DatabaseError(f"Ошибка при сохранении пользователя: {e}")

    def update_user_role(self, user_id, new_role):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET role = ? WHERE id = ?', (new_role, user_id))
            conn.commit()

    def delete_user(self, user_id):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
            conn.commit()

    def find_user_by_id(self, user_id):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            user = cursor.fetchone()
            if user:
                return {
                    "id": user[0],
                    "first_name": user[1],
                    "role": user[2],
                    "score": user[3],
                    "registered_events": user[4],
                    "tags": user[5],
                    "city": user[6]
                }
            return None

    def find_users_by_name(self, name):
        pattern = f"%{name}%"
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE first_name LIKE ?', (pattern,))
            rows = cursor.fetchall()
            return [
                {
                    "id": row[0],
                    "first_name": row[1],
                    "role": row[2],
                    "score": row[3],
                    "registered_events": row[4],
                    "tags": row[5],
                    "city": row[6]
                }
                for row in rows
            ]

    def search_events_by_tag(self, tag):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM events WHERE tags LIKE ? LIMIT 5", (f"%{tag}%",))
            rows = cursor.fetchall()
            return [self._format_event(row) for row in rows]

    def update_first_name(self, user_id, new_first_name):
        logger.info(f"Обновление имени пользователя: id={user_id}, new_first_name={new_first_name}")
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET first_name = ? WHERE id = ?', (new_first_name, user_id))
            conn.commit()
            updated_user = self.get_user(user_id)
            logger.info(f"Проверка обновления имени: {updated_user}")

    def update_user_city(self, user_id, new_city):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET city = ? WHERE id = ?', (new_city, user_id))
            conn.commit()

    def update_user_tags(self, user_id, tags):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET tags = ? WHERE id = ?', (tags, user_id))
            conn.commit()

    def get_events_by_city(self, city, limit=5, offset=0):
        """Возвращает список мероприятий для указанного города с постраничной выборкой."""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM events WHERE city = ? LIMIT ? OFFSET ?", (city, limit, offset))
            rows = cursor.fetchall()
            return [self._format_event(row) for row in rows]

    def get_events_count_by_city(self, city):
        """Возвращает общее количество мероприятий для указанного города."""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM events WHERE city = ?", (city,))
            count = cursor.fetchone()[0]
            return count

    def update_user_registered_events(self, user_id, registered_events):
        """Обновляет список зарегистрированных мероприятий для пользователя."""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET registered_events = ? WHERE id = ?", (registered_events, user_id))
            conn.commit()

    def get_events(self, limit=5, offset=0):
        """Возвращает список всех мероприятий с постраничной выборкой."""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM events LIMIT ? OFFSET ?", (limit, offset))
            rows = cursor.fetchall()
            return [self._format_event(row) for row in rows]

    def get_events_count(self):
        """Возвращает общее количество мероприятий во всех городах."""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM events")
            count = cursor.fetchone()[0]
            return count

    def get_event_by_id(self, event_id: int):
        """Получает информацию о мероприятии по его ID."""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
            event = cursor.fetchone()
            if event:
                return {
                    "id": event[0],
                    "name": event[1],
                    "event_date": event[2],
                    "start_time": event[3],
                    "city": event[4],
                    "creator": event[5],
                    "description": event[6],
                    "participation_points": event[7],
                    "participants_count": event[8],
                    "tags": event[9],
                    "code": event[10],
                    "owner": event[11]
                }
            return None

    def get_upcoming_events(self, limit=3):
        """Получает список ближайших мероприятий."""
        with self.connect() as conn:
            cursor = conn.cursor()
            # Сортируем по дате и времени (предполагается, что формат даты позволяет сортировку)
            cursor.execute("""
                SELECT * FROM events 
                ORDER BY event_date, start_time 
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [self._format_event(row) for row in rows]

    def get_events_by_tag(self, tag, limit=5, offset=0):
        """Возвращает список мероприятий по тегу с постраничной выборкой."""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM events WHERE tags LIKE ? LIMIT ? OFFSET ?", (f"%{tag}%", limit, offset))
            rows = cursor.fetchall()
            return [self._format_event(row) for row in rows]

    def get_events_count_by_tag(self, tag):
        """Возвращает общее количество мероприятий по тегу."""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM events WHERE tags LIKE ?", (f"%{tag}%",))
            count = cursor.fetchone()[0]
            return count

    def is_user_registered_for_event(self, user_id: int, event_id: str) -> bool:
        """Проверяет, зарегистрирован ли пользователь на мероприятие."""
        user = self.get_user(user_id)
        if not user:
            return False
        registered_events = user.get("registered_events", "")
        events_list = [e.strip() for e in registered_events.split(",") if e.strip()]
        return str(event_id) in events_list

    def increment_event_participants_count(self, event_id: int) -> bool:
        """Увеличивает счетчик участников мероприятия на 1."""
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE events SET participants_count = participants_count + 1 WHERE id = ?", 
                    (event_id,)
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при увеличении счетчика участников: {e}")
            return False

    def decrement_event_participants_count(self, event_id: int) -> bool:
        """Уменьшает счетчик участников мероприятия на 1."""
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE events SET participants_count = MAX(0, participants_count - 1) WHERE id = ?", 
                    (event_id,)
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при уменьшении счетчика участников: {e}")
            return False

    def get_users_for_event(self, event_id):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, first_name, registered_events FROM users")
            users = []
            for row in cursor.fetchall():
                user_id, first_name, registered_events = row
                if registered_events:
                    events_list = [e.strip() for e in registered_events.split(",") if e.strip()]
                    if str(event_id) in events_list:
                        users.append({"id": user_id, "first_name": first_name})
            return users

    def delete_event(self, event_id):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
            conn.commit()
