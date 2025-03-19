from .base import AIAgent
from .rag import RAGAgent

class EventInfoAgent(AIAgent):
    def __init__(self):
        self.rag_agent = RAGAgent()

    def process_query(self, query: str, **kwargs) -> str:
        return self.rag_agent.process_query(query)