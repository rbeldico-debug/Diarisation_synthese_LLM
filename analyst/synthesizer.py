# Remplacer le fichier analyst/synthesizer.py par :
import json
from openai import OpenAI
from config import Config

class Synthesizer:
    def __init__(self):
        self.client = OpenAI(base_url=Config.LLM_BASE_URL, api_key="ollama")

    def warm_up(self):
        """Méthode de préchauffage pour éviter le crash au démarrage."""
        print("[Analyste] Préchauffage du modèle...")
        # Optionnel : faire un micro-appel ici pour charger le modèle en VRAM

    def generate_summary(self) -> str:
        if not Config.JOURNAL_PATH.exists():
            return "En attente de données pour la session..."

        # Lecture des dernières entrées (Focus Zettelkasten : on veut de la structure)
        events = []
        with open(Config.JOURNAL_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in lines[-50:]: # On prend les 50 derniers événements
                data = json.loads(line)
                events.append(f"- **{data['intent_tag']}** ({data['source']}): {data['text']}")

        logs_context = "\n".join(events)

        try:
            response = self.client.chat.completions.create(
                model=Config.ANALYST_MODEL_NAME,
                messages=[
                    {"role": "system", "content": Config.ANALYST_PROMPT},
                    {"role": "user", "content": f"Voici les logs de la session :\n{logs_context}"}
                ],
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"⚠️ Erreur de synthèse : {e}"

    def generate_vocal_brief(self, markdown_content: str) -> str:
        prompt = (
            "Tu es Océane, l'assistante personnelle de l'utilisateur. "
            "En te basant sur le dashboard de session, fais une synthèse orale élégante. "
            "Parle à la première personne. Ne cite jamais de balises markdown. "
            "Commence par : 'Ici Océane. Voici un point sur vos dernières réflexions.' "
            "Sois synthétique (4 phrases max) et mets en avant les liens entre les sujets."
        )

        try:
            response = self.client.chat.completions.create(
                model=Config.ANALYST_MODEL_NAME,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"Dashboard actuel :\n{markdown_content}"}
                ],
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"[Analyste] ❌ Erreur Briefing Vocal : {e}")
            return ""