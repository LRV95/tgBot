import sqlite3
import os
import logging
from contextlib import contextmanager

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
                        role TEXT DEFAULT 'user',
                        score INTEGER DEFAULT 0,
                        registered_events TEXT DEFAULT '',
                        tags TEXT DEFAULT '',
                        city TEXT DEFAULT ''
                    )
                ''')

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS projects (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        curator TEXT,
                        phone_number TEXT,
                        email TEXT,
                        description TEXT,
                        tags TEXT
                    )
                ''')

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        project_id INTEGER,
                        event_date TEXT,
                        start_time TEXT,
                        location TEXT DEFAULT '',
                        creator TEXT,
                        participants_count INTEGER DEFAULT 0,
                        participation_points INTEGER DEFAULT 5,
                        tags TEXT,
                        FOREIGN KEY (project_id) REFERENCES projects(id)
                    )
                ''')

                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Ошибка при создании таблиц: {e}")
            raise DatabaseError(f"Ошибка при создании таблиц: {e}")

    def _format_project(self, row):
        return {
            "id": row[0],
            "name": row[1],
            "curator": row[2],
            "phone_number": row[3],
            "email": row[4],
            "description": row[5],
            "tags": row[6]
        }

    def _format_event(self, row):
        return {
            "id": row[0],
            "project_id": row[1],
            "event_date": row[2],
            "start_time": row[3],
            "location": row[4],
            "creator": row[5],
            "participants_count": row[6],
            "participation_points": row[7],
            "tags": row[8]
        }

    def get_all_projects(self):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects")
            rows = cursor.fetchall()
            return [self._format_project(row) for row in rows]

    def get_all_events(self):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM events")
            rows = cursor.fetchall()
            return [self._format_event(row) for row in rows]

    def add_project(self, name, curator, phone_number, email, description, tags=""):
        with self.connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO projects (name, curator, phone_number, email, description, tags)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (name, curator, phone_number, email, description, tags))
                conn.commit()
            except sqlite3.IntegrityError as e:
                conn.rollback()
                raise e

    def add_event(self, name, curator, phone_number, email, description, tags=""):
        self.add_project(name, curator, phone_number, email, description, tags)

    def add_event_detail(self, project_id, event_date, start_time, participants_count, participation_points, creator,
                         tags="", location=""):
        with self.connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO events (project_id, event_date, start_time, location, creator, participants_count, participation_points, tags)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (project_id, event_date, start_time, location, creator, participants_count, participation_points, tags))
                conn.commit()
            except sqlite3.IntegrityError as e:
                conn.rollback()
                raise e

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

    def save_user(self, user_id, first_name=None, role="user"):
        """Сохраняет информацию о пользователе."""
        try:
            logger.info(f"Попытка сохранения пользователя: id={user_id}, first_name={first_name}, role={role}")
            with self.connect() as conn:
                cursor = conn.cursor()
                existing_user = self.get_user(user_id)
                if existing_user:
                    logger.info(f"Обновляем существующего пользователя: id={user_id}")
                    cursor.execute('''
                        UPDATE users 
                        SET first_name = ?,
                            role = ?
                        WHERE id = ?
                    ''', (first_name, role, user_id))
                else:
                    logger.info(f"Создаем нового пользователя: id={user_id}")
                    cursor.execute('''
                        INSERT INTO users 
                        (id, first_name, role, score, registered_events, tags, city)
                        VALUES (?, ?, ?, 0, '', '', '')
                    ''', (user_id, first_name, role))
                conn.commit()
                saved_user = self.get_user(user_id)
                logger.info(f"Проверка сохраненных данных: {saved_user}")
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

    def search_projects_by_tag(self, tag):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects WHERE tags LIKE ? LIMIT 5", (f"%{tag}%",))
            rows = cursor.fetchall()
            return [self._format_project(row) for row in rows]

    def search_projects_by_name(self, name):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects WHERE name LIKE ? LIMIT 5", (f"%{name}%",))
            rows = cursor.fetchall()
            return [self._format_project(row) for row in rows]

    def search_events_by_tag(self, tag):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM events WHERE tags LIKE ? LIMIT 5", (f"%{tag}%",))
            rows = cursor.fetchall()
            return [self._format_event(row) for row in rows]

    def search_events_by_project_name(self, project_name):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT e.* FROM events e
                JOIN projects p ON e.project_id = p.id
                WHERE p.name LIKE ? LIMIT 5
            ''', (f"%{project_name}%",))
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
                    "project_id": event[1],
                    "event_date": event[2],
                    "start_time": event[3],
                    "city": event[4],
                    "participants_count": event[5],
                    "participation_points": event[6],
                    "creator": event[7],
                    "tags": event[8]
                }
            return None
