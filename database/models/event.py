import logging
import sqlite3
from datetime import datetime
from ..core import Database
from ..exceptions import DatabaseError

logger = logging.getLogger(__name__)

class EventModel(Database):
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
            datetime.strptime(event_date, "%d.%m.%Y")
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

    def search_events_by_tag(self, tag):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM events WHERE tags LIKE ? LIMIT 5", (f"%{tag}%",))
            rows = cursor.fetchall()
            return [self._format_event(row) for row in rows]

    def get_events_by_city(self, city, limit=5, offset=0):
        """Возвращает список мероприятий для указанного региона с постраничной выборкой."""
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
                return self._format_event(event)
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
        try:
            from .user import UserModel
            user_model = UserModel(self.db_name)
            user = user_model.get_user(user_id)
            if not user:
                return False
            registered_events = user.get("registered_events", "")
            events_list = [e.strip() for e in registered_events.split(",") if e.strip()]
            return bool(str(event_id) in events_list)
        except:
            return False

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
        """Удаляет мероприятие из базы данных."""
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                
                # Сначала удаляем все ссылки на мероприятие из registered_events пользователей
                cursor.execute("SELECT id, registered_events FROM users WHERE registered_events LIKE ?", (f"%{event_id}%",))
                users = cursor.fetchall()
                
                for user_id, registered_events in users:
                    # Разбиваем строку с мероприятиями и удаляем нужное
                    events_list = [e.strip() for e in registered_events.split(",") if e.strip()]
                    if str(event_id) in events_list:
                        events_list.remove(str(event_id))
                        new_registered_events = ",".join(events_list)
                        cursor.execute(
                            "UPDATE users SET registered_events = ? WHERE id = ?",
                            (new_registered_events, user_id)
                        )
                
                # Затем удаляем само мероприятие
                cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
                conn.commit()
                
                if cursor.rowcount == 0:
                    logger.warning(f"Мероприятие с ID {event_id} не найдено при попытке удаления")
                    return False
                    
                logger.info(f"Мероприятие с ID {event_id} успешно удалено")
                return True

        except sqlite3.Error as e:
            logger.error(f"Ошибка при удалении мероприятия: {e}")
            raise DatabaseError(f"Ошибка при удалении мероприятия: {e}")

    def has_completed_event(self, user_id, event_id):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM completed_events WHERE user_id = ? AND event_id = ?",
                (user_id, event_id)
            )
            return cursor.fetchone() is not None

    def mark_event_completed(self, user_id, event_id):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO completed_events (user_id, event_id) VALUES (?, ?)",
                (user_id, event_id)
            )
            conn.commit()

    def update_event_field(self, event_id, field, new_value):
        with self.connect() as conn:
            cursor = conn.cursor()
            query = f"UPDATE events SET {field} = ? WHERE id = ?"
            cursor.execute(query, (new_value, event_id))
            conn.commit()
