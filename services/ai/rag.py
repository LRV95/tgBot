# services/ai/rag.py
import difflib
import random
import logging
from typing import List, Dict, Any, Optional
import json
import re

from database.core import Database
from .base import AIAgent
from .gigachat_llm import GigaChatLLM
from .memory_store import MemoryStore
from .embeddings_store import EmbeddingsStore

logger = logging.getLogger(__name__)


class RAGAgent(AIAgent):
    """
    Улучшенный агент, использующий embeddings для семантического поиска
    информации о мероприятиях с элементами рассуждения и рефлексии.
    """

    def __init__(self):
        super().__init__(name="RAGAgent", autonomy_level=2)
        self.db = Database()
        self.llm = GigaChatLLM(temperature=0.5)
        self.memory_store = MemoryStore()
        self.embeddings_store = EmbeddingsStore()

        # Регистрация инструментов
        self.register_tool(
            "find_event_by_name",
            self._find_event_by_name,
            "Находит мероприятие по названию"
        )

        self.register_tool(
            "get_all_event_names",
            self._get_all_event_names,
            "Получает список всех названий мероприятий"
        )

        self.register_tool(
            "determine_event_from_query",
            self._determine_event_from_query,
            "Определяет, о каком мероприятии идет речь в запросе"
        )

        self.register_tool(
            "semantic_event_search",
            self._semantic_event_search,
            "Поиск мероприятий с использованием embeddings"
        )

        self.register_tool(
            "generate_event_response",
            self._generate_event_response,
            "Генерация ответа на основе информации о мероприятии"
        )

    def _semantic_event_search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Поиск релевантных мероприятий с использованием embeddings
        
        Args:
            query: Текст запроса
            k: Количество результатов для возврата
            
        Returns:
            Список релевантных мероприятий с их метаданными
        """
        try:
            results = self.embeddings_store.search(query, k)
            return results
        except Exception as e:
            logger.error(f"Error in semantic event search: {e}")
            return []

    def _get_all_event_names(self) -> List[str]:
        """
        Получает список всех названий мероприятий

        Returns:
            List[str]: Список названий мероприятий
        """
        with self.db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM events")
            rows = cursor.fetchall()

        return [row[0] for row in rows]

    def _find_event_by_name(self, event_name: str) -> Optional[Dict]:
        """
        Находит мероприятие по названию

        Args:
            event_name: Название мероприятия

        Returns:
            Optional[Dict]: Информация о мероприятии или None, если не найдено
        """
        with self.db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name, event_date, start_time, city, description, tags, id FROM events WHERE name = ?",
                (event_name,)
            )
            row = cursor.fetchone()

        if row:
            return {
                "name": row[0],
                "event_date": row[1],
                "start_time": row[2],
                "city": row[3],
                "description": row[4],
                "tags": row[5],
                "id": row[6]
            }

        return None

    def _determine_event_from_query(self, query: str, event_names: List[str]) -> Dict:
        """
        Определяет, о каком мероприятии идет речь в запросе

        Args:
            query: Запрос пользователя
            event_names: Список названий мероприятий

        Returns:
            Dict: Информация о найденном мероприятии
        """
        prompt = (
                "Дан список названий мероприятий:\n"
                f"{', '.join(event_names)}\n\n"
                "Пользовательский запрос: \"" + query + "\"\n\n"
                                                        "Определи, о каком из указанных мероприятий идёт речь. "
                                                        "Верни только название мероприятия, которое есть в списке, без лишних слов и знаков препинания."
        )

        # Добавляем информацию в память
        self.add_to_memory("query", query)
        self.add_to_memory("prompt_for_event_detection", prompt)

        try:
            llm_response = self.llm.generate(prompt).strip()

            # Добавляем результат в память
            self.add_to_memory("llm_event_response", llm_response)

            # Проверяем, есть ли выбранное мероприятие в списке
            if llm_response in event_names:
                logger.info(f"LLM определил мероприятие: {llm_response}")
                return {
                    "found": True,
                    "event_name": llm_response,
                    "method": "llm_direct_match",
                    "confidence": 0.9
                }

            # Если прямого совпадения нет, ищем ближайшее
            best_match = difflib.get_close_matches(llm_response, event_names, n=1)
            if best_match:
                logger.info(f"Найдено ближайшее совпадение: {best_match[0]}")
                return {
                    "found": True,
                    "event_name": best_match[0],
                    "method": "difflib_match",
                    "confidence": 0.7
                }

            # Если и так не нашли, возвращаем отрицательный результат
            return {
                "found": False,
                "method": "no_match",
                "confidence": 0
            }
        except Exception as e:
            logger.error(f"Ошибка при определении названия мероприятия: {e}")
            return {
                "found": False,
                "method": "error",
                "confidence": 0
            }

    def _generate_event_response(self, event_details: Dict, query: str) -> str:
        """
        Генерация ответа на основе информации о мероприятии
        
        Args:
            event_details: Информация о мероприятии
            query: Исходный запрос пользователя
            
        Returns:
            Сгенерированный ответ
        """
        try:
            context = {
                "event": event_details,
                "query": query
            }
            
            prompt = f"""
            На основе следующей информации о мероприятии ответьте на запрос пользователя:
            
            Название: {event_details['name']}
            Описание: {event_details['description']}
            Дата: {event_details['date']}
            Место: {event_details['location']}
            
            Запрос пользователя: {query}
            
            Пожалуйста, предоставьте информативный и полезный ответ, основываясь на имеющейся информации.
            """
            
            response = self.llm.generate(prompt)
            return response
            
        except Exception as e:
            logger.error(f"Error generating event response: {e}")
            return "Извините, произошла ошибка при генерации ответа."

    def reason(self, query: str, context: Dict = None) -> List[str]:
        """
        Построение цепочки рассуждений для достижения цели
        
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
        reasoning_steps.append("Выполняю семантический поиск релевантных мероприятий")
        events = self._semantic_event_search(query)
        
        if not events:
            reasoning_steps.append("Не найдено релевантных мероприятий")
            return reasoning_steps
            
        # 3. Анализ результатов
        reasoning_steps.append(f"Найдено {len(events)} релевантных мероприятий")
        
        # 4. Генерация ответа
        reasoning_steps.append("Генерирую ответ на основе найденной информации")
        
        return reasoning_steps

    def process_query(self, query: str, **kwargs) -> str:
        """
        Обработка запроса пользователя
        
        Args:
            query: Запрос пользователя
            **kwargs: Дополнительные параметры
            
        Returns:
            Ответ на запрос
        """
        try:
            # 1. Поиск релевантных мероприятий
            events = self._semantic_event_search(query)
            
            if not events:
                return "Извините, я не смог найти информацию по вашему запросу. Попробуйте переформулировать вопрос."
            
            # 2. Генерация ответа на основе наиболее релевантного мероприятия
            best_event = events[0]  # Берем наиболее релевантное мероприятие
            response = self._generate_event_response(best_event, query)
            
            # 3. Если есть дополнительные релевантные мероприятия, добавляем информацию о них
            if len(events) > 1:
                response += "\n\nТакже вас могут заинтересовать следующие мероприятия:\n"
                for event in events[1:3]:  # Добавляем еще 2 мероприятия
                    response += f"- {event['name']} ({event['date']})\n"
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return "Извините, произошла ошибка при обработке вашего запроса."