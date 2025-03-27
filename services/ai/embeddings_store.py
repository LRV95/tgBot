import logging
from typing import List, Dict, Any
import json
from langchain_gigachat import GigaChatEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from database.core import Database
import config

logger = logging.getLogger(__name__)


class EmbeddingsStore:
    """
    Класс для работы с embeddings и векторным хранилищем.
    Использует GigaChat для генерации embeddings и FAISS для хранения.
    """

    def __init__(self):
        self.db = Database()
        self.embeddings = GigaChatEmbeddings(
            credentials=config.AUTHORIZATION_KEY,
            model="Embeddings",
            verify_ssl_certs=False
        )
        self.vector_store = None
        self._initialize_store()

    def _initialize_store(self):
        """
        Инициализация векторного хранилища
        """
        try:
            # Получаем все мероприятия из базы данных
            events = self.db.get_all_events()
            
            if not events:
                logger.warning("No events found in database")
                return
                
            # Подготавливаем тексты для embeddings
            texts = []
            metadatas = []
            
            for event in events:
                # Создаем текст для embeddings
                text = f"""
                Название: {event['name']}
                Описание: {event['description']}
                Дата: {event['date']}
                Время: {event['time']}
                Город: {event['city']}
                Теги: {event['tags']}
                """
                
                # Создаем метаданные
                metadata = {
                    "id": event['id'],
                    "name": event['name'],
                    "date": event['date'],
                    "time": event['time'],
                    "city": event['city'],
                    "tags": event['tags']
                }
                
                texts.append(text)
                metadatas.append(metadata)
            
            # Создаем документы
            documents = [
                Document(page_content=text, metadata=metadata)
                for text, metadata in zip(texts, metadatas)
            ]
            
            # Инициализируем векторное хранилище
            self.vector_store = FAISS.from_documents(documents, self.embeddings)
            logger.info(f"Initialized embeddings store with {len(events)} events")
            
        except Exception as e:
            logger.error(f"Error initializing embeddings store: {e}")
            raise

    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Поиск релевантных мероприятий
        
        Args:
            query: Текст запроса
            k: Количество результатов
            
        Returns:
            Список релевантных мероприятий
        """
        try:
            if not self.vector_store:
                logger.warning("Vector store not initialized")
                return []
                
            # Поиск релевантных документов
            results = self.vector_store.similarity_search_with_score(query, k=k)
            
            # Преобразуем результаты в формат мероприятий
            events = []
            for doc, score in results:
                metadata = doc.metadata
                event = {
                    "id": metadata["id"],
                    "name": metadata["name"],
                    "date": metadata["date"],
                    "time": metadata["time"],
                    "city": metadata["city"],
                    "tags": metadata["tags"],
                    "relevance_score": float(score)
                }
                events.append(event)
            
            return events
            
        except Exception as e:
            logger.error(f"Error searching events: {e}")
            return []

    def add_event(self, event_data: Dict[str, Any]):
        """
        Добавление нового мероприятия
        
        Args:
            event_data: Данные мероприятия
        """
        try:
            # Добавляем мероприятие в базу данных
            event_id = self.db.add_event(event_data)
            
            # Создаем текст для embeddings
            text = f"""
            Название: {event_data['name']}
            Описание: {event_data['description']}
            Дата: {event_data['date']}
            Время: {event_data['time']}
            Город: {event_data['city']}
            Теги: {event_data['tags']}
            """
            
            # Создаем метаданные
            metadata = {
                "id": event_id,
                "name": event_data["name"],
                "date": event_data["date"],
                "time": event_data["time"],
                "city": event_data["city"],
                "tags": event_data["tags"]
            }
            
            # Создаем документ
            document = Document(page_content=text, metadata=metadata)
            
            # Добавляем в векторное хранилище
            if self.vector_store:
                self.vector_store.add_documents([document])
            else:
                self.vector_store = FAISS.from_documents([document], self.embeddings)
                
            logger.info(f"Added event {event_id} to embeddings store")
            
        except Exception as e:
            logger.error(f"Error adding event to embeddings store: {e}")
            raise

    def update_event(self, event_id: int, event_data: Dict[str, Any]):
        """
        Обновление существующего мероприятия
        
        Args:
            event_id: ID мероприятия
            event_data: Новые данные мероприятия
        """
        try:
            # Обновляем мероприятие в базе данных
            self.db.update_event(event_id, event_data)
            
            # Создаем новый текст для embeddings
            text = f"""
            Название: {event_data['name']}
            Описание: {event_data['description']}
            Дата: {event_data['date']}
            Время: {event_data['time']}
            Город: {event_data['city']}
            Теги: {event_data['tags']}
            """
            
            # Создаем новые метаданные
            metadata = {
                "id": event_id,
                "name": event_data["name"],
                "date": event_data["date"],
                "time": event_data["time"],
                "city": event_data["city"],
                "tags": event_data["tags"]
            }
            
            # Создаем новый документ
            document = Document(page_content=text, metadata=metadata)
            
            # Обновляем в векторном хранилище
            if self.vector_store:
                # Удаляем старый документ
                self.vector_store.delete([{"id": event_id}])
                # Добавляем новый
                self.vector_store.add_documents([document])
                
            logger.info(f"Updated event {event_id} in embeddings store")
            
        except Exception as e:
            logger.error(f"Error updating event in embeddings store: {e}")
            raise

    def delete_event(self, event_id: int):
        """
        Удаление мероприятия
        
        Args:
            event_id: ID мероприятия
        """
        try:
            # Удаляем мероприятие из базы данных
            self.db.delete_event(event_id)
            
            # Удаляем из векторного хранилища
            if self.vector_store:
                self.vector_store.delete([{"id": event_id}])
                
            logger.info(f"Deleted event {event_id} from embeddings store")
            
        except Exception as e:
            logger.error(f"Error deleting event from embeddings store: {e}")
            raise 