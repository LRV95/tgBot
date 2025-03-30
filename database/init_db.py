import logging
import os
import sys

# Добавляем корневую директорию проекта в PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.core import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database():
    """Инициализация базы данных с тестовыми данными"""
    try:
        # Создаем экземпляр базы данных
        db = Database()
        
        # Подключаемся к базе данных
        with db.connect() as conn:
            cursor = conn.cursor()
            
            # Добавляем теговые мероприятия
            test_events = [
                {
                    "name": "Волонтерская акция по уборке парка",
                    "event_date": "2024-03-30",
                    "start_time": "10:00",
                    "city": "Москва",
                    "creator": "admin",
                    "description": "Приглашаем всех желающих принять участие в уборке городского парка. Будем собирать мусор, сажать деревья и обустраивать клумбы.",
                    "participation_points": 10,
                    "participants_count": 0,
                    "tags": "экология,город,парк,уборка",
                    "code": "CLEAN2024",
                    "owner": "admin"
                },
                {
                    "name": "Помощь в приюте для животных",
                    "event_date": "2024-04-01",
                    "start_time": "14:00",
                    "city": "Санкт-Петербург",
                    "creator": "admin",
                    "description": "Помощь в уходе за животными в приюте. Кормление, выгул, уборка помещений и общение с животными.",
                    "participation_points": 15,
                    "participants_count": 0,
                    "tags": "животные,помощь,приют",
                    "code": "PETS2024",
                    "owner": "admin"
                },
                {
                    "name": "Сбор макулатуры",
                    "event_date": "2024-04-05",
                    "start_time": "11:00",
                    "city": "Москва",
                    "creator": "admin",
                    "description": "Организация сбора макулатуры в офисе. Сортировка, взвешивание и отправка на переработку.",
                    "participation_points": 5,
                    "participants_count": 0,
                    "tags": "экология,переработка,офис",
                    "code": "PAPER2024",
                    "owner": "admin"
                }
            ]
            
            # Очищаем таблицу events
            cursor.execute("DELETE FROM events")
            
            # Добавляем мероприятия в базу данных
            for event in test_events:
                cursor.execute("""
                    INSERT INTO events (
                        name, event_date, start_time, city, creator,
                        description, participation_points, participants_count,
                        tags, code, owner
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event["name"], event["event_date"], event["start_time"],
                    event["city"], event["creator"], event["description"],
                    event["participation_points"], event["participants_count"],
                    event["tags"], event["code"], event["owner"]
                ))
            
            conn.commit()
            logger.info("Test events added successfully")
            
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

if __name__ == "__main__":
    init_database() 