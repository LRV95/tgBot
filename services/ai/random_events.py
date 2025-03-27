# services/ai/random_events.py
import random
import logging
from typing import List, Dict, Any
import json
import re

from .base import AIAgent
from database.core import Database
from .gigachat_llm import GigaChatLLM
from .memory_store import MemoryStore
from bot.constants import TAGS, CITIES
from .shared_embeddings import SharedEmbeddings

logger = logging.getLogger(__name__)


class RandomEventsAgent(AIAgent):
    """
    Агент для предоставления случайных мероприятий
    с использованием семантического поиска.
    """

    def __init__(self):
        super().__init__(name="RandomEventsAgent", autonomy_level=2)
        self.db = Database()
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
            "generate_event_description",
            self._generate_event_description,
            "Генерация описания мероприятия"
        )

    def _semantic_event_search(self, query: str, k: int = 10) -> List[Dict[str, Any]]:
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

    def _generate_event_description(self, event: Dict[str, Any]) -> str:
        """
        Генерация описания мероприятия
        
        Args:
            event: Информация о мероприятии
            
        Returns:
            Сгенерированное описание
        """
        try:
            prompt = f"""
            Создай интересное и привлекательное описание для следующего мероприятия:
            
            Название: {event['name']}
            Описание: {event['description']}
            Дата: {event['date']}
            Время: {event['time']}
            Город: {event['city']}
            Теги: {event['tags']}
            
            Пожалуйста, сделай описание ярким и информативным, подчеркивая уникальные особенности мероприятия.
            """
            
            response = self.llm.generate(prompt)
            return response
            
        except Exception as e:
            logger.error(f"Error generating event description: {e}")
            return event['description']

    def reason(self, query: str, context: Dict = None) -> List[str]:
        """
        Построение цепочки рассуждений для предоставления случайных мероприятий
        
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
            reasoning_steps.append("Не найдено релевантных мероприятий")
            return reasoning_steps
            
        # 3. Анализ результатов
        reasoning_steps.append(f"Найдено {len(events)} мероприятий")
        
        # 4. Выбор случайных мероприятий
        reasoning_steps.append("Выбираю случайные мероприятия из найденных")
        
        return reasoning_steps

    def process_query(self, query: str, **kwargs) -> str:
        """
        Обработка запроса пользователя
        
        Args:
            query: Запрос пользователя
            **kwargs: Дополнительные параметры
            
        Returns:
            Ответ со случайными мероприятиями
        """
        try:
            # 1. Поиск релевантных мероприятий
            events = self._semantic_event_search(query, k=10)
            
            if not events:
                return "Извините, я не смог найти подходящие мероприятия. Попробуйте переформулировать запрос."
            
            # 2. Выбираем случайные мероприятия
            num_events = min(3, len(events))
            selected_events = random.sample(events, num_events)
            
            # 3. Генерируем ответ
            response = "Вот несколько интересных мероприятий, которые могут вас заинтересовать:\n\n"
            
            for event in selected_events:
                description = self._generate_event_description(event)
                response += f"✨ **{event['name']}**\n"
                response += f"📅 Дата: {event['date']}\n"
                response += f"🕒 Время: {event['time']}\n"
                response += f"📍 Город: {event['city']}\n"
                response += f"🏷 Теги: {event['tags']}\n"
                response += f"📝 {description}\n\n"
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing random events query: {e}")
            return "Извините, произошла ошибка при поиске мероприятий."