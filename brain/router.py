import numpy as np
from openai import OpenAI
from core.settings import settings

class IntentRouter:
    """
    Version ADR-026 (Allégée).
    Ne fait plus de classification taxonomique rigide.
    Sert uniquement à :
    1. Générer les embeddings pour la mémoire vectorielle.
    2. Filtrer le bruit (phrases trop courtes).
    """
    def __init__(self):
        self.chat_client = OpenAI(base_url=settings.ROUTER_BASE_URL, api_key="ollama")

    def get_embedding(self, text: str):
        try:
            response = self.chat_client.embeddings.create(
                model=settings.EMBEDDING_MODEL_NAME,
                input=text
            )
            return np.array(response.data[0].embedding)
        except Exception as e:
            print(f"[Router] ❌ Erreur Embedding : {e}")
            return None

    def _precompute_taxonomy(self):
        # OBSOLÈTE avec ADR-026, mais gardé vide pour compatibilité si appelé par main.py
        pass

    def route(self, text: str) -> str:
        """
        Analyse l'intention de l'utilisateur.
        Retourne : [READ], [WRITE], [CMD] ou [CHAT].
        """
        if len(text.split()) < 2: return "[CHAT]"  # Trop court

        try:
            response = self.chat_client.chat.completions.create(
                model=settings.ROUTER_MODEL_NAME,  # mistral-nemo
                messages=[
                    {"role": "system", "content": settings.ROUTER_SYSTEM_PROMPT},
                    {"role": "user", "content": text}
                ],
                temperature=0.0  # Très déterministe
            )
            intent = response.choices[0].message.content.strip()

            # Sécurité si le LLM bavarde
            if "[READ]" in intent: return "[READ]"
            if "[WRITE]" in intent: return "[WRITE]"
            if "[CMD]" in intent: return "[CMD]"

            return "[CHAT]"  # Défaut

        except Exception as e:
            print(f"[Router] ⚠️ Erreur classification : {e}")
            return "[CHAT]"