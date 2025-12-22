import json
import os
from datetime import datetime
from openai import OpenAI
from config import Config
from memory.vector_manager import VectorManager
from brain.router import IntentRouter


class Synthesizer:
    def __init__(self):
        self.client = OpenAI(base_url=Config.LLM_BASE_URL, api_key="ollama")
        self.vector_db = VectorManager()
        self.router = IntentRouter()
        # On utilise un fichier d'historique pour la session
        self.history_path = Config.LOGS_DIR / f"briefings_{Config.SESSION_ID}.md"

    def generate_summary(self) -> str:
        if not Config.JOURNAL_PATH.exists():
            return "En attente de données..."

        # 1. Collecte des logs récents
        current_events = []
        recent_text_blob = ""
        display_logs = []
        with open(Config.JOURNAL_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in lines[-40:]:
                data = json.loads(line)
                current_events.append(f"- **{data['intent_tag']}**: {data['text']}")
                recent_text_blob += data['text'] + " "
            for line in lines[-10:]:
                data = json.loads(line)
                display_logs.append(f"| {data['timestamp'][11:16]} | {data['intent_tag']} | {data['text']} |")

        # 2. RAG (Souvenirs)
        past_memories = "Aucun souvenir connexe."
        query_emb = self.router.get_embedding(recent_text_blob[:500])
        if query_emb is not None:
            results = self.vector_db.search_similar(query_emb, n_results=3)
            if results and results['documents'] and results['documents'][0]:
                past_memories = "\n".join([f"- {doc}" for doc in results['documents'][0]])

        # 3. Récupération de l'historique des briefings de la session
        vocal_history = "*(Aucun briefing vocal pour le moment)*"
        if self.history_path.exists():
            with open(self.history_path, "r", encoding="utf-8") as f:
                vocal_history = f.read()

        # 4. Synthèse LLM
        try:
            response = self.client.chat.completions.create(
                model=Config.ANALYST_MODEL_NAME,
                messages=[
                    {"role": "system", "content": Config.ANALYST_PROMPT},
                    {"role": "user", "content": f"Logs:\n{chr(10).join(current_events)}\n\nPassé:\n{past_memories}"}
                ],
                temperature=0.3
            )
            synthesis = response.choices[0].message.content
        except Exception as e:
            synthesis = f"⚠️ Erreur LLM : {e}"

        # 5. Assemblage du Dashboard
        final_md = synthesis + "\n\n"
        final_md += "### 🏛️ Connexions avec le Passé (RAG)\n" + past_memories + "\n\n"
        final_md += "### 📜 Journal de Session\n"
        final_md += "| Heure | Tags | Transcription |\n| :--- | :--- | :--- |\n" + "\n".join(display_logs) + "\n\n"
        final_md += "---\n\n### 🎙️ Historique des Briefings d'Océane\n" + vocal_history

        return final_md

    def generate_vocal_brief(self, markdown_content: str) -> str:
        """Génère le texte vocal et l'ajoute à l'historique."""
        try:
            response = self.client.chat.completions.create(
                model=Config.ANALYST_MODEL_NAME,
                messages=[
                    {"role": "system", "content": Config.SYSTEM_PROMPT},
                    {"role": "user", "content": f"Dashboard actuel :\n{markdown_content}"}
                ],
                temperature=0.7
            )
            brief_text = response.choices[0].message.content

            # On ajoute le briefing à l'historique avec l'heure
            timestamp = datetime.now().strftime("%H:%M")
            with open(self.history_path, "a", encoding="utf-8") as f:
                f.write(f"**[{timestamp}]** : {brief_text}\n\n")

            return brief_text
        except Exception as e:
            print(f"[Analyste] ❌ Erreur Briefing : {e}")
            return ""