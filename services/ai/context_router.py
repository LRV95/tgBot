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
                f"Ты опытный специалист по классификации запросов пользователей. Из следующих тегов: {CONTEXT_TAGS}, "
                "выбери тот, который наиболее точно соответствует запросу пользователя.\n\n"
                "Правила классификации:\n"
                "- Тег 'информация': запросы о деталях конкретного мероприятия, времени, месте проведения, требованиях к участникам\n"
                "- Тег 'рекомендация': запросы о подборе мероприятий под интересы, опыт или предпочтения пользователя\n" 
                "- Тег 'случайные события': запросы на случайный выбор мероприятий, поиск необычных событий или общий список активностей\n"
                "- Тег 'обучение': запросы об обучении волонтерству, развитии навыков, тренингах\n"
                "- Тег 'организация': вопросы об организации мероприятий, координации волонтеров\n"
                "- Тег 'поддержка': эмоциональная поддержка, мотивация, решение конфликтов\n\n"
                "Анализируй контекст и намерение пользователя. Если запрос можно отнести к нескольким категориям, "
                "выбери наиболее подходящую по основной цели запроса.\n\n"
                "Ответ должен содержать только один тег без дополнительных слов.\n\n"   
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

        if "информация" in extracted_tags:
            return self.event_info_agent.process_query(query)
        elif "рекомендация" in extracted_tags:
            return self.recommendation_agent.process_query(query, user_id)
        elif "случайные события" in extracted_tags:
            return self.random_events_agent.process_query(query, user_id)
        else:
            return self.dialogue_agent.process_query(query, conversation_history)