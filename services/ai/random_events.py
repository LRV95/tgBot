import random
import logging
from .base import AIAgent
from database.core import Database
from .gigachat_llm import GigaChatLLM
from bot.constants import TAGS, CITIES

logger = logging.getLogger(__name__)

class RandomEventsAgent(AIAgent):
    def __init__(self):
        self.db = Database()
        self.llm = GigaChatLLM()

    def process_query(self, query: str, user_id: int, **kwargs) -> str:
        prompt_filters = (
            "Извлеки из следующего запроса указанные теги и города. "
            "Известные теги: " + ", ".join(TAGS) + ". "
            "Известные города: " + ", ".join(CITIES) + ".\n\n"
            "Запрос: " + query + "\n\n"
            "Ответ должен быть в формате:\n"
            "Теги: [тег1, тег2, ...]\n"
            "Города: [город1, город2, ...]"
        )
        try:
            filters_response = self.llm.generate(prompt_filters).strip()
            logger.info(f"Извлечены фильтры: {filters_response}")
        except Exception as e:
            logger.error(f"Ошибка при извлечении фильтров: {e}")
            filters_response = "Теги: []\nГорода: []"

        extracted_tags = []
        extracted_cities = []
        try:
            for line in filters_response.splitlines():
                if line.lower().startswith("теги:"):
                    tags_part = line.split(":", 1)[1].strip()
                    tags_part = tags_part.strip(" []")
                    if tags_part:
                        extracted_tags = [t.strip() for t in tags_part.split(",") if t.strip()]
                elif line.lower().startswith("города:"):
                    cities_part = line.split(":", 1)[1].strip()
                    cities_part = cities_part.strip(" []")
                    if cities_part:
                        extracted_cities = [c.strip() for c in cities_part.split(",") if c.strip()]
        except Exception as e:
            logger.error(f"Ошибка при парсинге фильтров: {e}")

        logger.info(f"Полученные теги: {extracted_tags}, города: {extracted_cities}")

        base_query = "SELECT name, event_date, start_time, city, description FROM events"
        conditions = []
        params = []

        if extracted_tags:
            tag_conditions = []
            for tag in extracted_tags:
                tag_conditions.append("LOWER(tags) LIKE ?")
                params.append(f"%{tag.lower()}%")
            conditions.append("(" + " OR ".join(tag_conditions) + ")")

        if extracted_cities:
            city_conditions = []
            for city in extracted_cities:
                city_conditions.append("LOWER(city) = ?")
                params.append(city.lower())
            conditions.append("(" + " OR ".join(city_conditions) + ")")

        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)

        base_query += " ORDER BY event_date, start_time"

        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(base_query, tuple(params))
                events = cursor.fetchall()
        except Exception as e:
            logger.error(f"Ошибка при выполнении запроса к БД: {e}")
            events = []

        if not events:
            logger.info("Подходящих мероприятий по фильтрам не найдено, выбираем случайные.")
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name, event_date, start_time, city, description FROM events")
                all_events = cursor.fetchall()
            if not all_events:
                return "На данный момент нет доступных мероприятий."
            events = random.sample(all_events, min(4, len(all_events)))
        else:
            if len(events) > 4:
                events = random.sample(events, 4)

        descriptions = []
        for event in events:
            name, event_date, start_time, city, description = event
            prompt = (
                f"Опиши мероприятие, основываясь на следующей информации:\n"
                f"Название: {name}\n"
                f"Дата: {event_date}\n"
                f"Время: {start_time}\n"
                f"Город: {city}\n"
                f"Описание: {description}\n\n"
                "Сформируй интересное, подробное и завершённое описание этого мероприятия. "
                "Пожалуйста, не обрывай ответ на полуслове, а дай полное описание, включая все важные детали. "
                "При этом используй эмодзи и markdown."
            )
            try:
                event_desc = self.llm.generate(prompt)
            except Exception as e:
                logger.error(f"Ошибка при генерации описания для мероприятия '{name}': {e}")
                event_desc = f"Описание для мероприятия '{name}' не удалось сгенерировать."
            descriptions.append(event_desc)

        final_output = "\n\n".join(descriptions)
        return final_output
