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
        prompt = (
                f"Ты специалист по классификации запросов. Из следующих тегов: {CONTEXT_TAGS}, "
                "выбери тот, который лучше всего соответствует запросу пользователя. "
                "Если запрос связан с получением подробной информации о мероприятии, выбери информация. "
                "Если запрос требует совета или рекомендаций по выбору мероприятия, выбери рекомендация. "
                "Если запрос подразумевает случайный выбор или поиск неожиданных событий, выбери случайные события. "
                "Если в запросе просьба предложить набор мероприятий, выбери случайные события."
                "Ответ должен содержать только один из этих тегов без лишних слов или знаков препинания.\n\n"
                "Запрос: " + query
        )
        try:
            response = self.llm.generate(prompt).strip().lower()
            if response in self.context_tags:
                logger.info(f"Извлечённый тег: {response}")
                return [response]
            else:
                logger.info(f"Не удалось извлечь корректный тег, получен ответ: {response}")
                return []
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
