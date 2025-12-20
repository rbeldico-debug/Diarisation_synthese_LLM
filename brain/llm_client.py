import re
from openai import OpenAI
from config import Config


class LLMClient:
    def __init__(self):
        print(f"Connexion au LLM sur {Config.LLM_BASE_URL} (Modèle: {Config.LLM_MODEL_NAME})...")
        try:
            # On utilise le client OpenAI compatible avec Ollama
            self.client = OpenAI(
                base_url=Config.LLM_BASE_URL,
                api_key=Config.LLM_API_KEY
            )
            print("✅ Client LLM initialisé.")
        except Exception as e:
            print(f"❌ Erreur init LLM : {e}")
            self.client = None

    def query(self, context_history: str, current_input: str) -> str:
        """
        Envoie le contexte au LLM et nettoie la réponse (suppression du CoT).
        """
        if not self.client:
            return "Erreur: LLM non connecté."

        messages = [
            {"role": "system", "content": Config.SYSTEM_PROMPT},
            {"role": "user", "content": f"Voici l'historique :\n{context_history}"}
        ]

        try:
            # Appel API
            response = self.client.chat.completions.create(
                model=Config.LLM_MODEL_NAME,
                messages=messages,
                temperature=0.6,  # Un peu plus bas pour éviter qu'il divague
                max_tokens=200,  # On limite la réponse pour le vocal
                stream=False
            )

            raw_content = response.choices[0].message.content.strip()

            # NETTOYAGE CRITIQUE : Suppression des balises de pensée <think>...</think>
            clean_content = self._clean_thought_tags(raw_content)

            return clean_content

        except Exception as e:
            print(f"❌ Erreur appel LLM : {e}")
            return "[Pas de réponse]"

    def _clean_thought_tags(self, text: str) -> str:
        """
        Supprime les blocs de pensée du type <think>...</think>
        ou les réflexions entre parenthèses si le modèle en fait.
        """
        if not text:
            return ""

        # 1. Supprimer le contenu entre balises <think> et </think> (multiligne inclus)
        # Le flag re.DOTALL permet au . de matcher aussi les retours à la ligne
        cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)

        # 2. Nettoyage de sécurité (espaces en trop créés par la suppression)
        cleaned = cleaned.strip()

        # 3. Si le modèle a tout supprimé (cas rare), on garde le brut au cas où
        if not cleaned and text:
            return text

        return cleaned