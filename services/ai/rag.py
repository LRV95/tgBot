import difflib
import random
from database.core import Database
from langchain.prompts import PromptTemplate
import logging
from .gigachat_llm import GigaChatLLM

logger = logging.getLogger(__name__)


class RAGAgent:
    """
    Агент, использующий RetrievalQA-подход, который сам определяет, о каком мероприятии идет речь.
    Он извлекает список названий мероприятий из базы, запрашивает у LLM наиболее релевантное название,
    затем формирует окончательный промпт с подробностями по выбранному мероприятию.

    Дополнительно реализована функция process_random_events, которая возвращает подробные описания
    нескольких случайных мероприятий.
    """

    def __init__(self):
        self.db = Database()
        self.llm = GigaChatLLM()

    def process_query(self, query: str) -> str:
        with self.db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, event_date, start_time, city, description FROM events")
            rows = cursor.fetchall()

        if not rows:
            return "Нет релевантной информации о мероприятиях."

        event_names = [row[0] for row in rows]

        event_list_str = "\n".join([f"- {name}" for name in event_names])
        prompt_event = (
                "Дан список названий мероприятий:\n"
                f"{event_list_str}\n\n"
                "Пользовательский запрос: \"" + query + "\"\n\n"
                                                        "Определи, о каком из указанных мероприятий идёт речь. "
                                                        "Верни только название мероприятия, которое есть в списке, без лишних слов и знаков препинания."
        )

        try:
            selected_event_name = self.llm.generate(prompt_event).strip()
            logger.info(f"LLM определил мероприятие: {selected_event_name}")
        except Exception as e:
            logger.error(f"Ошибка при определении названия мероприятия: {e}")
            return "Произошла ошибка при обработке запроса."

        if selected_event_name not in event_names:
            best_match = difflib.get_close_matches(selected_event_name, event_names, n=1)
            if best_match:
                selected_event_name = best_match[0]
            else:
                return "Не удалось определить, о каком мероприятии идёт речь."

        event_details = None
        for row in rows:
            if row[0] == selected_event_name:
                event_details = {
                    "name": row[0],
                    "event_date": row[1],
                    "start_time": row[2],
                    "city": row[3],
                    "description": row[4]
                }
                break

        if not event_details:
            return "Мероприятие не найдено в базе данных."

        prompt_final = (
            f"Информация о мероприятии:\n"
            f"Название: {event_details['name']}\n"
            f"Дата: {event_details['event_date']}\n"
            f"Время: {event_details['start_time']}\n"
            f"Город: {event_details['city']}\n"
            f"Описание: {event_details['description']}\n\n"
            f"Пользовательский запрос: \"{query}\"\n\n"
            "Сформируй подробный ответ на основе данной информации о мероприятии. "
            "Опиши его доброжелательно, используя эмодзи."
        )

        try:
            response = self.llm.generate(prompt_final)
        except Exception as e:
            logger.error(f"Ошибка при генерации окончательного ответа: {e}")
            response = "Произошла ошибка при обработке запроса."

        return response

    def process_random_events(self, num_events: int = 5) -> str:
        """
        Дополнительная функция для генерации описаний случайных мероприятий.
        Из базы выбирается num_events случайных мероприятий, для каждого формируется подробное описание.
        """
        with self.db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, event_date, start_time, city, description FROM events")
            rows = cursor.fetchall()

        if not rows:
            return "Нет релевантной информации о мероприятиях."

        # Выбираем случайные мероприятия
        if len(rows) > num_events:
            selected_events = random.sample(rows, num_events)
        else:
            selected_events = rows

        descriptions = []
        for event in selected_events:
            name, event_date, start_time, city, description = event
            prompt = (
                f"Опиши мероприятие, основываясь на следующей информации:\n"
                f"Название: {name}\n"
                f"Дата: {event_date}\n"
                f"Время: {start_time}\n"
                f"Город: {city}\n"
                f"Описание: {description}\n\n"
                "Сформируй интересное и подробное описание этого мероприятия, которое поможет пользователю понять, что это за событие. Используй эмодзи для придания дружелюбного тона."
            )
            try:
                event_desc = self.llm.generate(prompt)
            except Exception as e:
                logger.error(f"Ошибка при генерации описания для мероприятия '{name}': {e}")
                event_desc = f"Описание для мероприятия '{name}' не удалось сгенерировать."
            descriptions.append(event_desc)

        final_output = "\n\n".join(descriptions)
        return final_output