from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.chains import RetrievalQA
from services.gigachat_llm import GigachatLLM
from database.connection import get_db_connection


def get_documents_from_db(db_path: str = "database.db"):
    """
    Извлекает документы из базы данных.
    Предполагается, что в таблице documents есть колонка content.
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT content FROM documents")
    rows = cursor.fetchall()
    conn.close()
    return [row["content"] for row in rows]


def initialize_rag(api_key: str, db_path: str = "database.db"):
    """
    Инициализирует механизм RAG, создавая цепочку для RetrievalQA.
    """
    # Получаем документы из базы данных
    documents = get_documents_from_db(db_path)

    # Инициализируем эмбеддинги. Можно использовать OpenAIEmbeddings,
    # либо другой провайдер, если Gigachat предоставляет свои эмбеддинги.
    embeddings = OpenAIEmbeddings(api_key=api_key)

    # Создаём векторное хранилище из текстов
    vectorstore = FAISS.from_texts(documents, embeddings)
    retriever = vectorstore.as_retriever()

    # Инициализируем Gigachat LLM
    llm = GigachatLLM(api_key=api_key)

    # Создаём цепочку QA
    qa_chain = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=retriever)
    return qa_chain


def get_answer(query: str, api_key: str, db_path: str = "database.db") -> str:
    """
    Обрабатывает запрос, используя RAG-цепочку, и возвращает ответ.
    """
    qa_chain = initialize_rag(api_key, db_path)
    result = qa_chain.run(query)
    return result
