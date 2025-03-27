import logging
from typing import List, Dict, Any
from .embeddings_store import EmbeddingsStore

logger = logging.getLogger(__name__)

class SharedEmbeddings:
    """
    Синглтон для централизованного доступа к embeddings.
    """
    _instance = None
    _store = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SharedEmbeddings, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._store is None:
            self._store = EmbeddingsStore()

    def get_store(self) -> EmbeddingsStore:
        return self._store

    def search_events(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Поиск релевантных мероприятий
        
        Args:
            query: Текст запроса
            k: Количество результатов
            
        Returns:
            Список релевантных мероприятий
        """
        return self._store.search(query, k)

    def add_event(self, event_data: Dict[str, Any]):
        """
        Добавление нового мероприятия
        
        Args:
            event_data: Данные мероприятия
        """
        self._store.add_event(event_data)

    def update_event(self, event_id: int, event_data: Dict[str, Any]):
        """
        Обновление существующего мероприятия
        
        Args:
            event_id: ID мероприятия
            event_data: Новые данные мероприятия
        """
        self._store.update_event(event_id, event_data)

    def delete_event(self, event_id: int):
        """
        Удаление мероприятия
        
        Args:
            event_id: ID мероприятия
        """
        self._store.delete_event(event_id) 