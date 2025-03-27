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

        logger.info(f"Агент {self.name} использует инструмент: {tool_name}")
        result = self.available_tools[tool_name]["function"](*args, **kwargs)

        # Добавляем результат в историю действий для рефлексии
        self.action_history[-1]["result"] = result

        return result

    def reflect(self, action_index: int = None) -> Dict:
        """
        Выполняет рефлексию над действиями

        Args:
            action_index: Индекс конкретного действия для рефлексии
                         (None для рефлексии над всей цепочкой)

        Returns:
            Dict: Результат рефлексии
        """
        if action_index is not None and action_index < len(self.action_history):
            # Рефлексия над конкретным действием
            action = self.action_history[action_index]
            result = {
                "action": action["action"],
                "success": "result" in action,
                "evaluation": "Действие выполнено успешно" if "result" in action else "Действие не выполнено"
            }
        else:
            # Рефлексия над всей цепочкой действий
            successful_actions = sum(1 for action in self.action_history if "result" in action)
            result = {
                "total_actions": len(self.action_history),
                "successful_actions": successful_actions,
                "success_rate": successful_actions / max(1, len(self.action_history)),
                "evaluation": "Цепочка действий выполнена успешно"
                if successful_actions == len(self.action_history)
                else "Не все действия в цепочке выполнены успешно"
            }

        logger.info(f"Агент {self.name} выполнил рефлексию: {result}")
        return result

    def adapt_role(self, new_role: str) -> None:
        """
        Адаптирует роль агента в зависимости от контекста

        Args:
            new_role: Новая роль агента
        """
        logger.info(f"Агент {self.name} меняет роль на {new_role}")
        self.name = f"{new_role}Agent"
        # Дополнительная логика адаптации роли может быть добавлена здесь

    def create_dynamic_tool(self, tool_code: str, tool_name: str, description: str) -> bool:
        """
        Создает новый инструмент на основе кода

        Args:
            tool_code: Код инструмента
            tool_name: Название инструмента
            description: Описание инструмента

        Returns:
            bool: True в случае успеха, False в случае ошибки
        """
        try:
            # ВНИМАНИЕ: exec потенциально небезопасен, используйте с осторожностью
            # В реальном приложении следует использовать более безопасные механизмы
            namespace = {}
            exec(tool_code, namespace)

            if "tool_function" not in namespace:
                logger.error(f"Ошибка при создании инструмента {tool_name}: функция tool_function не найдена")
                return False

            self.register_tool(tool_name, namespace["tool_function"], description)
            logger.info(f"Успешно зарегистрирован инструмент: {tool_name}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при создании инструмента {tool_name}: {e}")
            return False

    def save_state(self) -> Dict:
        """
        Сохраняет состояние агента

        Returns:
            Dict: Состояние агента
        """
        return {
            "name": self.name,
            "autonomy_level": self.autonomy_level,
            "memory": self.memory,
            "action_history": self.action_history,
            "current_reasoning": self.current_reasoning
        }

    def load_state(self, state: Dict) -> None:
        """
        Загружает состояние агента

        Args:
            state: Состояние агента
        """
        self.name = state.get("name", self.name)
        self.autonomy_level = state.get("autonomy_level", self.autonomy_level)
        self.memory = state.get("memory", self.memory)
        self.action_history = state.get("action_history", self.action_history)
        self.current_reasoning = state.get("current_reasoning", self.current_reasoning)