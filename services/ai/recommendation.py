# services/ai/recommendation.py
import logging
from typing import List, Dict, Any
from .base import AIAgent
from .gigachat_llm import GigaChatLLM
from .memory_store import MemoryStore
from .shared_embeddings import SharedEmbeddings

logger = logging.getLogger(__name__)


class RecommendationAgent(AIAgent):
    """
    Агент для рекомендации мероприятий на основе интересов пользователя
    с использованием семантического поиска.
    """

    def __init__(self):
        super().__init__(name="RecommendationAgent", autonomy_level=2)
        self.llm = GigaChatLLM(temperature=0.7)
        self.memory_store = MemoryStore()
        self.embeddings = SharedEmbeddings()

        # Регистрация инструментов
        self.register_tool(
            "semantic_event_search",
            self._semantic_event_search,
            "Поиск мероприятий с использованием embeddings"
        )

        self.register_tool(
            "extract_interests",
            self._extract_interests_from_query,
            "Извлечение интересов из запроса пользователя"
        )

        self.register_tool(
            "extract_profession",
            self._extract_profession_from_query,
            "Извлечение профессии из запроса пользователя"
        )

    def _semantic_event_search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Поиск релевантных мероприятий с использованием embeddings
        
        Args:
            query: Текст запроса
            k: Количество результатов
            
        Returns:
            Список релевантных мероприятий
        """
        try:
            results = self.embeddings.search_events(query, k)
            return results
        except Exception as e:
            logger.error(f"Error in semantic event search: {e}")
            return []

    def _extract_interests_from_query(self, query: str) -> List[str]:
        """
        Извлечение интересов из запроса пользователя
        
        Args:
            query: Запрос пользователя
            
        Returns:
            Список интересов
        """
        try:
            prompt = f"""
            Проанализируй запрос пользователя и извлеки из него интересы и предпочтения.
            Запрос: {query}
            
            Ответ должен быть в формате JSON:
            {{
                "interests": ["интерес1", "интерес2", ...]
            }}
            """
            
            response = self.llm.generate(prompt)
            # Парсим JSON из ответа
            import json
            result = json.loads(response)
            return result.get("interests", [])
            
        except Exception as e:
            logger.error(f"Error extracting interests: {e}")
            return []

    def _extract_profession_from_query(self, query: str) -> str:
        """
        Извлечение профессии из запроса пользователя
        
        Args:
            query: Запрос пользователя
            
        Returns:
            Профессия пользователя
        """
        try:
            prompt = f"""
            Проанализируй запрос пользователя и извлеки из него профессию.
            Запрос: {query}
            
            Ответ должен быть в формате JSON:
            {{
                "profession": "профессия"
            }}
            """
            
            response = self.llm.generate(prompt)
            # Парсим JSON из ответа
            import json
            result = json.loads(response)
            return result.get("profession", "")
            
        except Exception as e:
            logger.error(f"Error extracting profession: {e}")
            return ""

    def reason(self, query: str, context: Dict = None) -> List[str]:
        """
        Построение цепочки рассуждений для рекомендации мероприятий
        
        Args:
            query: Запрос пользователя
            context: Контекстная информация
            
        Returns:
            Список шагов рассуждения
        """
        reasoning_steps = []
        
        # 1. Анализ запроса
        reasoning_steps.append(f"Анализирую запрос пользователя: {query}")
        
        # 2. Извлечение интересов
        reasoning_steps.append("Извлекаю интересы из запроса")
        interests = self._extract_interests_from_query(query)
        if interests:
            reasoning_steps.append(f"Найдены интересы: {', '.join(interests)}")
        
        # 3. Извлечение профессии
        reasoning_steps.append("Извлекаю профессию из запроса")
        profession = self._extract_profession_from_query(query)
        if profession:
            reasoning_steps.append(f"Найдена профессия: {profession}")
        
        # 4. Поиск релевантных мероприятий
        reasoning_steps.append("Выполняю семантический поиск мероприятий")
        events = self._semantic_event_search(query)
        if events:
            reasoning_steps.append(f"Найдено {len(events)} релевантных мероприятий")
        else:
            reasoning_steps.append("Мероприятия не найдены")
        
        return reasoning_steps

    def process_query(self, query: str, **kwargs) -> str:
        """
        Обработка запроса пользователя
        
        Args:
            query: Запрос пользователя
            **kwargs: Дополнительные параметры
            
        Returns:
            Ответ с рекомендациями
        """
        try:
            # 1. Извлекаем интересы и профессию
            interests = self._extract_interests_from_query(query)
            profession = self._extract_profession_from_query(query)
            
            # 2. Ищем релевантные мероприятия
            events = self._semantic_event_search(query, k=3)
            
            if not events:
                return "Извините, я не смог найти подходящие мероприятия. Попробуйте переформулировать запрос."
            
            # 3. Формируем ответ
            response = "Вот мероприятия, которые могут вас заинтересовать:\n\n"
            
            for event in events:
                response += f"✨ **{event['name']}**\n"
                response += f"📅 Дата: {event['date']}\n"
                response += f"🕒 Время: {event['time']}\n"
                response += f"📍 Город: {event['city']}\n"
                response += f"🏷 Теги: {event['tags']}\n"
                response += f"📝 {event['description']}\n\n"
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing recommendation query: {e}")
            return "Извините, произошла ошибка при поиске рекомендаций."