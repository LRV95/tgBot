import logging
from .base import AIAgent
from .gigachat_llm import GigaChatLLM
from .recommendation import RecommendationAgent
from .dialogue import DialogueAgent
from .event_info import EventInfoAgent
from .random_events import RandomEventsAgent
from bot.constants import TAGS, CONTEXT_TAGS

logger = logging.getLogger(__name__)

class ContextRouterAgent(AIAgent):
    def __init__(self):
        self.recommendation_agent = RecommendationAgent()
        self.dialogue_agent = DialogueAgent()
        self.event_info_agent = EventInfoAgent()
        self.random_events_agent = RandomEventsAgent()
        self.llm = GigaChatLLM()  # Для извлечения тегов из запроса
        self.context_tags = CONTEXT_TAGS

    def extract_tags(self, query: str) -> list:
        """
        Отправляет запрос к GigaChat для извлечения тегов из текста запроса.
        Возвращает список тегов (из уже известных TAGS), разделённых запятыми.
        """
        prompt = (
            "Определи, какие из следующих тегов относятся к запросу пользователя. "
            "Верни только один тег без лишних слов.\n\n"
            "Теги: " + ", ".join(CONTEXT_TAGS) + "\n\n"
            "Запрос: " + query
        )
        try:
            response = self.llm.generate(prompt)
            # Предполагаем, что ответ будет вида: "Социальное, Экологическое"
            tags = [tag.strip() for tag in response.split(",") if tag.strip() in TAGS]
            logger.info(f"Извлеченные теги: {tags}")
            return tags
        except Exception as e:
            logger.error(f"Ошибка при извлечении тегов: {e}")
            return []

    def process_query(self, query: str, user_id: int = None, conversation_history: list = None, **kwargs) -> str:
        extracted_tags = self.extract_tags(query)
        lower_query = query.lower()

        if "информация" in lower_query or extracted_tags:
            return self.event_info_agent.process_query(query)
        elif "рекомендация" in lower_query:
            return self.recommendation_agent.process_query(query, user_id)
        elif "случайные события" in lower_query:
            return self.random_events_agent.process_query(query)
        else:
            return self.dialogue_agent.process_query(query, conversation_history)
