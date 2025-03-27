# services/ai/context_router.py
import logging
import json
from typing import List, Dict, Any
import time

from .base import AIAgent
from .gigachat_llm import GigaChatLLM
from .recommendation import RecommendationAgent
from .dialogue import DialogueAgent
from .event_info import EventInfoAgent
from .random_events import RandomEventsAgent
from .memory_store import MemoryStore
from .shared_embeddings import SharedEmbeddings
from bot.constants import TAGS, CONTEXT_TAGS, CITIES

logger = logging.getLogger(__name__)


class ContextRouterAgent(AIAgent):
    """
    Агент маршрутизации контекста, который определяет намерение пользователя
    и перенаправляет запрос соответствующему агенту с использованием семантического поиска.
    """

    def __init__(self):
        super().__init__(name="ContextRouterAgent", autonomy_level=3)
        self.recommendation_agent = RecommendationAgent()
        self.dialogue_agent = DialogueAgent()
        self.event_info_agent = EventInfoAgent()
        self.random_events_agent = RandomEventsAgent()
        self.llm = GigaChatLLM()
        self.memory_store = MemoryStore()
        self.embeddings = SharedEmbeddings()
        self.context_tags = CONTEXT_TAGS

        # Регистрация инструментов
        self.register_tool(
            "extract_tags_from_query",
            self.extract_tags,
            "Извлекает теги из запроса пользователя"
        )

        self.register_tool(
            "extract_location_from_query",
            self._extract_location,
            "Извлекает географическую информацию из запроса"
        )

        self.register_tool(
            "detect_query_type",
            self._detect_query_type,
            "Определяет тип запроса пользователя"
        )

    def _extract_location(self, query: str) -> Dict:
        """
        Извлекает географическую информацию из запроса
        
        Args:
            query: Запрос пользователя
            
        Returns:
            Словарь с информацией о местоположении
        """
        try:
            prompt = f"""
            Проанализируй запрос пользователя и определи географическую информацию:
            "{query}"
            
            Верни JSON-объект с полями:
            - city: название города (если есть)
            - region: название региона (если есть)
            - confidence: уверенность в определении (0-1)
            """
            
            response = self.llm.generate(prompt)
            location_info = json.loads(response)
            return location_info
            
        except Exception as e:
            logger.error(f"Error extracting location: {e}")
            return {"city": None, "region": None, "confidence": 0}

    def _detect_query_type(self, query: str) -> Dict:
        """
        Определяет тип запроса пользователя
        
        Args:
            query: Запрос пользователя
            
        Returns:
            Словарь с информацией о типе запроса
        """
        try:
            prompt = f"""
            Проанализируй запрос пользователя и определи его тип:
            "{query}"
            
            Возможные типы:
            - recommendation: запрос на рекомендации мероприятий
            - event_info: запрос информации о конкретном мероприятии
            - random_events: запрос случайных мероприятий
            - dialogue: общий диалог или вопросы
            
            Верни JSON-объект с полями:
            - type: тип запроса
            - confidence: уверенность в определении (0-1)
            - context: дополнительный контекст
            """
            
            response = self.llm.generate(prompt)
            query_type = json.loads(response)
            return query_type
            
        except Exception as e:
            logger.error(f"Error detecting query type: {e}")
            return {"type": "dialogue", "confidence": 0, "context": {}}

    def extract_tags(self, query: str) -> list:
        """
        Извлекает теги из запроса пользователя
        
        Args:
            query: Запрос пользователя
            
        Returns:
            Список тегов
        """
        try:
            prompt = f"""
            Проанализируй запрос пользователя и определи релевантные теги:
            "{query}"
            
            Доступные теги:
            {', '.join(TAGS)}
            
            Верни список тегов в формате JSON-массива строк.
            """
            
            response = self.llm.generate(prompt)
            tags = json.loads(response)
            return tags
            
        except Exception as e:
            logger.error(f"Error extracting tags: {e}")
            return []

    def reason(self, query: str, context: Dict = None) -> List[str]:
        """
        Построение цепочки рассуждений для маршрутизации запроса
        
        Args:
            query: Запрос пользователя
            context: Контекстная информация
            
        Returns:
            Список шагов рассуждения
        """
        reasoning_steps = []
        
        # 1. Анализ запроса
        reasoning_steps.append(f"Анализирую запрос пользователя: {query}")
        
        # 2. Определение типа запроса
        reasoning_steps.append("Определяю тип запроса")
        query_type = self._detect_query_type(query)
        reasoning_steps.append(f"Тип запроса: {query_type['type']}")
        
        # 3. Извлечение тегов
        reasoning_steps.append("Извлекаю релевантные теги")
        tags = self.extract_tags(query)
        reasoning_steps.append(f"Найдены теги: {', '.join(tags)}")
        
        # 4. Извлечение географической информации
        reasoning_steps.append("Определяю географическую информацию")
        location = self._extract_location(query)
        reasoning_steps.append(f"Местоположение: {location['city']}")
        
        # 5. Определение агента для обработки
        reasoning_steps.append("Определяю подходящего агента для обработки запроса")
        
        return reasoning_steps

    def process_query(self, query: str, user_id: int = None, conversation_history: list = None, **kwargs) -> str:
        """
        Обработка запроса пользователя и маршрутизация к соответствующему агенту
        
        Args:
            query: Запрос пользователя
            user_id: ID пользователя
            conversation_history: История диалога
            **kwargs: Дополнительные параметры
            
        Returns:
            Ответ на запрос
        """
        try:
            # 1. Определяем тип запроса
            query_type = self._detect_query_type(query)
            
            # 2. Извлекаем теги и местоположение
            tags = self.extract_tags(query)
            location = self._extract_location(query)
            
            # 3. Маршрутизируем запрос к соответствующему агенту
            if query_type['type'] == 'recommendation':
                return self.recommendation_agent.process_query(
                    query,
                    user_id=user_id,
                    city=location['city']
                )
            elif query_type['type'] == 'event_info':
                return self.event_info_agent.process_query(query)
            elif query_type['type'] == 'random_events':
                return self.random_events_agent.process_query(query)
            else:
                return self.dialogue_agent.process_query(
                    query,
                    user_id=user_id,
                    conversation_history=conversation_history
                )
            
        except Exception as e:
            logger.error(f"Error processing query in ContextRouter: {e}")
            return "Извините, произошла ошибка при обработке вашего запроса."