import logging
import sqlite3
from ..core import Database
from ..exceptions import DatabaseError

logger = logging.getLogger(__name__)

class UserModel(Database):
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

    def save_user(self, id, first_name=None, telegram_tag=None, role="user"):
        """Сохраняет первичную информацию о пользователе в базу данных."""
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                existing_user = self.get_user(id)
                if existing_user:
                    raise ValueError("Пользователь уже существует")
                else:
                    cursor.execute('''
                        INSERT INTO users 
                        (id, first_name, telegram_tag, employee_number, role, score, registered_events, tags, city)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (id, first_name, telegram_tag, "", role, 0, "", "", ""))
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

    def update_first_name(self, user_id, new_first_name):
        logger.info(f"Обновление имени пользователя: id={user_id}, new_first_name={new_first_name}")
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET first_name = ? WHERE id = ?', (new_first_name, user_id))
            conn.commit()
            updated_user = self.get_user(user_id)
            logger.info(f"Проверка обновления имени: {updated_user}")

    def update_user_employee_number(self, user_id, employee_number):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET employee_number = ? WHERE id = ?', (employee_number, user_id))
            conn.commit()

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

    def update_user_score(self, user_id, score):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET score = ? WHERE id = ?', (score, user_id))
            conn.commit()

    def update_user_registered_events(self, user_id, registered_events):
        """Обновляет список зарегистрированных мероприятий для пользователя."""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET registered_events = ? WHERE id = ?", (registered_events, user_id))
            conn.commit()

    def unregister_user_from_event(self, user_id, event_id):
        with self.connect() as conn:
            cursor = conn.cursor()
            # Получаем текущий список зарегистрированных мероприятий
            cursor.execute('SELECT registered_events FROM users WHERE id = ?', (user_id,))
            result = cursor.fetchone()
            if result and result[0]:
                # Преобразуем строку в список
                registered_events = result[0].split(',')
                # Удаляем event_id из списка, если он там есть
                if event_id in registered_events:
                    registered_events.remove(event_id)
                    # Преобразуем список обратно в строку
                    new_registered_events = ','.join(registered_events) if registered_events else None
                    # Обновляем запись в базе данных
                    cursor.execute('UPDATE users SET registered_events = ? WHERE id = ?', 
                                 (new_registered_events, user_id))
                    conn.commit() 