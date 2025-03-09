import logging
import sqlite3
from ..core import Database
from ..exceptions import DatabaseError

logger = logging.getLogger(__name__)


class UserModel:
    def __init__(self):
        self.db = Database()  # Инициализируем объект для работы с базой данных

    def get_all_users(self):
        """Возвращает список всех пользователей из таблицы users в виде списка словарей."""
        with self.db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users")
            rows = cursor.fetchall()
            # Получаем список имён столбцов из описания курсора
            columns = [description[0] for description in cursor.description]
            # Формируем список словарей, где ключи — имена столбцов, а значения — данные из строки
            users = [dict(zip(columns, row)) for row in rows]
            return users

    def get_user(self, user_id):
        """Возвращает данные пользователя по его ID, или None, если пользователь не найден."""
        with self.db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            if not row:
                return None
            columns = [description[0] for description in cursor.description]
            return dict(zip(columns, row))

    def save_user(self, id, first_name, telegram_tag, role):
        """Сохраняет нового пользователя с указанными данными."""
        with self.db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (id, first_name, telegram_tag, role) VALUES (?, ?, ?, ?)",
                (id, first_name, telegram_tag, role)
            )
            conn.commit()

    def update_user_city(self, user_id, city):
        """Обновляет город пользователя."""
        with self.db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET city = ? WHERE id = ?", (city, user_id))
            conn.commit()

    def update_user_tags(self, user_id, tags):
        """Обновляет теги пользователя."""
        with self.db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET tags = ? WHERE id = ?", (tags, user_id))
            conn.commit()

    def update_user_role(self, user_id, role):
        """Обновляет роль пользователя."""
        with self.db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
            conn.commit()

    def update_first_name(self, user_id, new_first_name):
        """Обновляет имя пользователя."""
        with self.db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET first_name = ? WHERE id = ?", (new_first_name, user_id))
            conn.commit()

    def update_user_employee_number(self, user_id, employee_number):
        """Обновляет табельный номер пользователя."""
        with self.db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET employee_number = ? WHERE id = ?", (employee_number, user_id))
            conn.commit()

    def update_user_score(self, user_id, score):
        """Обновляет количество баллов пользователя."""
        with self.db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET score = ? WHERE id = ?", (score, user_id))
            conn.commit()

    def update_user_registered_events(self, user_id, registered_events):
        """Обновляет список зарегистрированных мероприятий пользователя."""
        with self.db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET registered_events = ? WHERE id = ?", (registered_events, user_id))
            conn.commit()

    def delete_user(self, user_id):
        """Удаляет пользователя по его ID."""
        with self.db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()

    def find_user_by_id(self, user_id):
        """Находит пользователя по ID."""
        return self.get_user(user_id)

    def find_users_by_name(self, name):
        """Находит пользователей, имя которых содержит подстроку name."""
        with self.db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE first_name LIKE ?", (f"%{name}%",))
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            users = [dict(zip(columns, row)) for row in rows]
            return users