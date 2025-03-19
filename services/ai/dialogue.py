from .base import AIAgent
from .gigachat_llm import GigaChatLLM

class DialogueAgent(AIAgent):
    def __init__(self):
        self.llm = GigaChatLLM()

    def process_query(self, query: str, conversation_history: list = None, **kwargs) -> str:
        if conversation_history is None:
            conversation_history = []
        system_prompt = "Ты — эксперт в волонтёрстве, помогай пользователям обсуждать вопросы волонтёрства дружелюбно и информативно."
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": query})
        # Формируем единый текстовый prompt из истории
        prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
        return self.llm.generate(prompt)