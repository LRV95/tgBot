# services/ai/event_info.py
import logging
from typing import List, Dict, Any
from .base import AIAgent
from .gigachat_llm import GigaChatLLM
from .memory_store import MemoryStore
from .shared_embeddings import SharedEmbeddings

logger = logging.getLogger(__name__)


class EventInfoAgent(AIAgent):
    """
    Агент для предоставления подробной информации о мероприятиях
    с использованием семантического поиска.
    """

    def __init__(self):
        super().__init__(name="EventInfoAgent", autonomy_level=2)
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
            "generate_event_info",
            self._generate_event_info,
            "Генерация подробной информации о мероприятии"
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

    def _generate_event_info(self, event: Dict[str, Any], query: str) -> str:
        """
        Генерация подробной информации о мероприятии
        
        Args:
            event: Информация о мероприятии
            query: Запрос пользователя
            
        Returns:
            Подробное описание мероприятия
        """
        try:
            prompt = f"""
            На основе следующей информации о мероприятии и запроса пользователя,
            сгенерируй подробное и информативное описание:
            
            Запрос пользователя: {query}
            
            Информация о мероприятии:
            Название: {event['name']}
            Дата: {event['date']}
            Время: {event['time']}
            Город: {event['city']}
            Теги: {event['tags']}
            Описание: {event['description']}
            
            Пожалуйста, сделай описание информативным и релевантным запросу пользователя.
            """
            
            response = self.llm.generate(prompt)
            return response
            
        except Exception as e:
            logger.error(f"Error generating event info: {e}")
            return event['description']

    def reason(self, query: str, context: Dict = None) -> List[str]:
        """
        Построение цепочки рассуждений для предоставления информации о мероприятии
        
        Args:
            query: Запрос пользователя
            context: Контекстная информация
            
        Returns:
            Список шагов рассуждения
        """
        reasoning_steps = []
        
        # 1. Анализ запроса
        reasoning_steps.append(f"Анализирую запрос пользователя: {query}")
        
        # 2. Поиск релевантных мероприятий
        reasoning_steps.append("Выполняю семантический поиск мероприятий")
        events = self._semantic_event_search(query)
        
        if not events:
            reasoning_steps.append("Мероприятия не найдены")
            return reasoning_steps
            
        # 3. Анализ результатов
        reasoning_steps.append(f"Найдено {len(events)} мероприятий")
        
        # 4. Генерация информации
        reasoning_steps.append("Генерирую подробную информацию о мероприятии")
        
        return reasoning_steps

    def process_query(self, query: str, **kwargs) -> str:
        """
        Обработка запроса пользователя
        
        Args:
            query: Запрос пользователя
            **kwargs: Дополнительные параметры
            
        Returns:
            Ответ с информацией о мероприятии
        """
        try:
            # 1. Поиск релевантных мероприятий
            events = self._semantic_event_search(query, k=3)
            
            if not events:
                return "Извините, я не смог найти подходящие мероприятия. Попробуйте переформулировать запрос."
            
            # 2. Генерируем ответ для самого релевантного мероприятия
            event = events[0]
            response = self._generate_event_info(event, query)
            
            # 3. Если есть другие релевантные мероприятия, добавляем их в конец
            if len(events) > 1:
                response += "\n\nДругие релевантные мероприятия:\n"
                for other_event in events[1:]:
                    response += f"\n✨ **{other_event['name']}**\n"
                    response += f"📅 Дата: {other_event['date']}\n"
                    response += f"🕒 Время: {other_event['time']}\n"
                    response += f"📍 Город: {other_event['city']}\n"
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing event info query: {e}")
            return "Извините, произошла ошибка при поиске информации о мероприятии."