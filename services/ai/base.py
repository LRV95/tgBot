from abc import ABC, abstractmethod

class AIAgent(ABC):
    @abstractmethod
    def process_query(self, query: str, **kwargs) -> str:
        """Обрабатывает запрос и возвращает ответ"""
        pass
