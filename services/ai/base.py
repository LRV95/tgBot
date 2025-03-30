# services/ai/base.py
from abc import ABC, abstractmethod
import logging
from typing import Dict, List, Any, Optional
import json
import time

logger = logging.getLogger(__name__)


class AIAgent(ABC):
    """
    Усовершенствованный базовый класс для AI-агентов с поддержкой
    рассуждений, автономности, рефлексии и памяти.
    """

    def __init__(self, name: str = "BaseAgent", autonomy_level: int = 1):
        """
        Инициализация агента

        Args:
            name: Имя агента
            autonomy_level: Уровень автономности (0-3)
                0 - требуется подтверждение каждого действия
                1 - не требуется подтверждение для некоторых действий
                2 - требуется подтверждение только критичных действий
                3 - полная автономность в рамках полномочий
        """
        self.name = name
        self.autonomy_level = autonomy_level
        self.memory = {
            "short_term": [],  # Краткосрочная память (текущий диалог)
            "long_term": {}  # Долгосрочная память (сохраняется между сессиями)
        }
        self.action_history = []  # История действий для рефлексии
        self.current_reasoning = []  # Текущая цепочка рассуждений
        self.available_tools = {}  # Доступные инструменты

    @abstractmethod
    def process_query(self, query: str, **kwargs) -> str:
        """Обрабатывает запрос и возвращает ответ"""
        pass

    def reason(self, query: str, context: Dict = None) -> List[str]:
        """
        Построение цепочки рассуждений для достижения цели

        Args:
            query: Запрос пользователя
            context: Контекстная информация

        Returns:
            List[str]: Цепочка рассуждений
        """
        # Базовая реализация рассуждений, должна быть переопределена
        reasoning_steps = [
            f"Получен запрос: '{query}'",
            "Анализ контекста и истории взаимодействий",
            "Формирование ответа на основе доступной информации"
        ]

        self.current_reasoning = reasoning_steps
        return reasoning_steps

    def add_to_memory(self, key: str, value: Any, memory_type: str = "short_term") -> None:
        """
        Добавляет информацию в память агента

        Args:
            key: Ключ для доступа к информации
            value: Значение для сохранения
            memory_type: Тип памяти ("short_term" или "long_term")
        """
        if memory_type == "short_term":
            self.memory["short_term"].append({key: value, "timestamp": time.time()})
            # Ограничиваем размер краткосрочной памяти
            if len(self.memory["short_term"]) > 100:
                self.memory["short_term"] = self.memory["short_term"][-100:]
        else:
            self.memory["long_term"][key] = {"value": value, "timestamp": time.time()}

        logger.debug(f"Агент {self.name} добавил в {memory_type} память: {key}")

    def retrieve_from_memory(self, key: str = None, memory_type: str = "short_term") -> Any:
        """
        Извлекает информацию из памяти агента

        Args:
            key: Ключ для доступа к информации (если None, возвращает всю память)
            memory_type: Тип памяти ("short_term" или "long_term")

        Returns:
            Any: Извлеченная информация
        """
        if memory_type == "short_term":
            if key is None:
                return self.memory["short_term"]

            # Поиск в краткосрочной памяти
            for item in reversed(self.memory["short_term"]):
                if key in item:
                    return item[key]
            return None
        else:
            if key is None:
                return self.memory["long_term"]

            # Поиск в долгосрочной памяти
            if key in self.memory["long_term"]:
                return self.memory["long_term"][key]["value"]
            return None

    def safe_response(self, query: str, error_message: str = None) -> str:
        """
        Создает безопасный ответ в случае ошибки

        Args:
            query: Исходный запрос пользователя
            error_message: Пользовательское сообщение об ошибке

        Returns:
            str: Безопасный ответ
        """
        if not error_message:
            error_message = ("Приношу извинения, но я специализируюсь на вопросах волонтерства "
                             "и могу помочь вам найти подходящие мероприятия или ответить на вопросы в этой сфере. "
                             "Чем я могу вам помочь в контексте волонтерской деятельности? 😊")

        # Анализируем запрос для определения, связан ли он с волонтерством
        volunteering_keywords = [
            "волонтер", "волонтёр", "помощь", "благотворительность", "мероприятие",
            "добровольчество", "социальный", "поддержка", "помогать", "общественный",
            "бесплатно", "вклад", "содействие", "событие"
        ]

        # Проверяем, содержит ли запрос ключевые слова о волонтерстве
        contains_volunteering_terms = any(keyword in query.lower() for keyword in volunteering_keywords)

        if contains_volunteering_terms:
            return ("Извините, произошла ошибка при обработке вашего запроса о волонтерстве. "
                    "Пожалуйста, попробуйте сформулировать его иначе или задайте другой вопрос.")
        else:
            return error_message

    def register_tool(self, tool_name: str, tool_function: callable, description: str) -> None:
        """
        Регистрирует новый инструмент для использования агентом

        Args:
            tool_name: Название инструмента
            tool_function: Функция, реализующая инструмент
            description: Описание инструмента
        """
        self.available_tools[tool_name] = {
            "function": tool_function,
            "description": description
        }
        logger.info(f"Агент {self.name} зарегистрировал инструмент: {tool_name}")

    def use_tool(self, tool_name: str, *args, **kwargs) -> Any:
        """
        Использует зарегистрированный инструмент

        Args:
            tool_name: Название инструмента
            *args, **kwargs: Аргументы для инструмента

        Returns:
            Any: Результат работы инструмента

        Raises:
            ValueError: Если инструмент не найден
        """
        if tool_name not in self.available_tools:
            raise ValueError(f"Инструмент {tool_name} не найден")

        action = f"Использование инструмента {tool_name} с аргументами: {args}, {kwargs}"
        self.action_history.append({
            "action": action,
            "timestamp": time.time()
        })

        logger.debug(f"Агент {self.name} {action}")
        
        return self.available_tools[tool_name]["function"](*args, **kwargs)

    def can_perform_autonomously(self, action: str, criticality: int = 1) -> bool:
        """
        Проверяет, может ли агент выполнить действие автономно

        Args:
            action: Действие для проверки
            criticality: Критичность действия (0-3, где 3 - самое критичное)

        Returns:
            bool: True, если действие может быть выполнено автономно
        """
        # Если уровень автономности выше критичности, действие выполняется автономно
        if self.autonomy_level >= criticality:
            logger.info(f"Агент {self.name} автономно выполняет действие: {action}")
            return True

        # Иначе требуется подтверждение
        logger.info(f"Агент {self.name} требует подтверждения для действия: {action}")
        return False