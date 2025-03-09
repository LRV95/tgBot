from langchain.prompts import PromptTemplate
from database.core import Database
import logging
from .gigachat_llm import GigaChatLLM

logger = logging.getLogger(__name__)

class EventRetriever:
    """
    Простой поиск по событиям в базе данных с использованием SQL LIKE.
    """
    def __init__(self, db: Database):
        self.db = db

    def retrieve(self, query: str, top_k: int = 3) -> str:
        events = []
        with self.db.connect() as conn:
            cursor = conn.cursor()
            sql_query = """
                SELECT name, event_date, start_time, city, description 
                FROM events 
                WHERE name LIKE ? OR description LIKE ? 
                LIMIT ?
            """
            like_query = f"%{query}%"
            cursor.execute(sql_query, (like_query, like_query, top_k))
            rows = cursor.fetchall()
            for row in rows:
                event_text = (
                    f"Название: {row[0]}, Дата: {row[1]}, "
                    f"Время: {row[2]}, Город: {row[3]}, Описание: {row[4]}"
                )
                events.append(event_text)
        context = "\n".join(events) if events else "Нет релевантной информации о мероприятиях."
        return context

class RAGAgent:
    """
    Агент, использующий RetrievalQA-подход. Он получает контекст из БД и генерирует ответ с помощью GigaChat.
    """
    def __init__(self):
        self.db = Database()
        self.retriever = EventRetriever(self.db)
        self.llm = GigaChatLLM()
        self.prompt_template = PromptTemplate(
            input_variables=["context", "question"],
            template=(
                "Информация из базы данных:\n{context}\n\n"
                "Вопрос: {question}\n\nОтвет:"
            )
        )

    def process_query(self, query: str) -> str:
        context = self.retriever.retrieve(query)
        prompt = self.prompt_template.format(context=context, question=query)
        try:
            response = self.llm.generate(prompt)
        except Exception as e:
            logger.error(f"Ошибка при генерации ответа в RAGAgent: {e}")
            response = "Произошла ошибка при обработке запроса."
        return response
