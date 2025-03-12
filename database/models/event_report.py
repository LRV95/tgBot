import logging
from datetime import datetime
from ..core import Database
from ..exceptions import DatabaseError

logger = logging.getLogger(__name__)

class EventReportModel(Database):
    def _format_report(self, row):
        return {
            "id": row[0],
            "event_id": row[1],
            "report_date": row[2],
            "actual_participants": row[3],
            "photos_links": row[4],
            "summary": row[5],
            "feedback": row[6]
        }

    def create_report(self, event_id: int, actual_participants: int, photos_links: str, summary: str, feedback: str = None):
        """Создает новый отчет о мероприятии."""
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                # Проверяем существование мероприятия
                cursor.execute("SELECT id FROM events WHERE id = ?", (event_id,))
                if not cursor.fetchone():
                    raise ValueError(f"Мероприятие с ID {event_id} не найдено")

                # Проверяем, не существует ли уже отчет для этого мероприятия
                cursor.execute("SELECT id FROM event_reports WHERE event_id = ?", (event_id,))
                if cursor.fetchone():
                    raise ValueError(f"Отчет для мероприятия с ID {event_id} уже существует")

                report_date = datetime.now().strftime("%d.%m.%Y")
                cursor.execute('''
                    INSERT INTO event_reports (
                        event_id, report_date, actual_participants,
                        photos_links, summary, feedback
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    event_id, report_date, actual_participants,
                    photos_links, summary, feedback
                ))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Ошибка при создании отчета: {e}")
            raise DatabaseError(f"Ошибка при создании отчета: {str(e)}")

    def get_report(self, event_id: int):
        """Получает отчет о мероприятии по ID мероприятия."""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM event_reports WHERE event_id = ?", (event_id,))
            report = cursor.fetchone()
            return self._format_report(report) if report else None

    def update_report(self, event_id: int, actual_participants: int = None, 
                     photos_links: str = None, summary: str = None, feedback: str = None):
        """Обновляет существующий отчет о мероприятии."""
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                # Проверяем существование отчета
                cursor.execute("SELECT * FROM event_reports WHERE event_id = ?", (event_id,))
                if not cursor.fetchone():
                    raise ValueError(f"Отчет для мероприятия с ID {event_id} не найден")

                # Формируем запрос на обновление только указанных полей
                update_fields = []
                params = []
                if actual_participants is not None:
                    update_fields.append("actual_participants = ?")
                    params.append(actual_participants)
                if photos_links is not None:
                    update_fields.append("photos_links = ?")
                    params.append(photos_links)
                if summary is not None:
                    update_fields.append("summary = ?")
                    params.append(summary)
                if feedback is not None:
                    update_fields.append("feedback = ?")
                    params.append(feedback)

                if update_fields:
                    query = f"UPDATE event_reports SET {', '.join(update_fields)} WHERE event_id = ?"
                    params.append(event_id)
                    cursor.execute(query, params)
                    conn.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"Ошибка при обновлении отчета: {e}")
            raise DatabaseError(f"Ошибка при обновлении отчета: {str(e)}")

    def delete_report(self, event_id: int):
        """Удаляет отчет о мероприятии."""
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM event_reports WHERE event_id = ?", (event_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при удалении отчета: {e}")
            raise DatabaseError(f"Ошибка при удалении отчета: {str(e)}")

    def get_all_reports(self):
        """Получает все отчеты о мероприятиях."""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM event_reports")
            rows = cursor.fetchall()
            return [self._format_report(row) for row in rows] 