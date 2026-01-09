import re
from openai import OpenAI
from core.settings import settings

class LLMClient:
    def __init__(self):
        self.client = OpenAI(base_url=settings.LLM_BASE_URL, api_key="ollama")

    def query(self, context_history: str, user_input: str) -> str:
        messages = [
            {"role": "system", "content": settings.SYSTEM_PROMPT},
            {"role": "user", "content": f"Historique:\n{context_history}\n\nUtilisateur: {user_input}"}
        ]

        try:
            response = self.client.chat.completions.create(
                model=settings.LLM_MODEL_NAME,
                messages=messages,
                temperature=settings.TEMP_CHAT
            )
            return self._strip_thinking(response.choices[0].message.content)
        except Exception as e:
            return f"Désolé, j'ai un souci technique : {e}"

    @staticmethod
    def _strip_thinking(text: str) -> str:
        """Supprime les balises de réflexion (DeepSeek/R1)."""
        if not text: return ""
        return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()