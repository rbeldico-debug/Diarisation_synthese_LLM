import json
from datetime import datetime
from typing import Tuple, List, Dict, Optional, Any
from openai import OpenAI
from config import Config
from memory.vector_manager import VectorManager
from brain.router import IntentRouter
# On utilise un "Forward Reference" ou Any pour éviter les imports circulaires si nécessaire
from typing import Any


class Synthesizer:
    def __init__(self, graph_manager: Any = None):
        self.client = OpenAI(base_url=Config.LLM_BASE_URL, api_key="ollama")
        self.vector_db = VectorManager()
        self.router = IntentRouter()
        self.history_path = Config.LOGS_DIR / f"briefings_{Config.SESSION_ID}.md"
        # Le Cerveau est branché ici (Optionnel, peut être None)
        self.graph = graph_manager

    def generate_summary(self) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Génère le dashboard et extrait les concepts.
        Retourne un tuple : (Contenu Markdown du Dashboard, Liste des concepts extraits)
        """
        if not Config.JOURNAL_PATH.exists():
            return "En attente de données...", []

        # 1. Collecte des logs récents
        current_events = []
        recent_text_blob = ""
        display_logs = []

        try:
            with open(Config.JOURNAL_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()
                # On prend les 50 dernières lignes pour le contexte
                for line in lines[-50:]:
                    try:
                        data = json.loads(line)
                        if not data.get("ignored", False):
                            current_events.append(f"- **{data['intent_tag']}**: {data['text']}")
                            recent_text_blob += data['text'] + " "
                    except json.JSONDecodeError:
                        continue

                # Pour le tableau d'affichage (les 10 derniers)
                for line in lines[-10:]:
                    try:
                        data = json.loads(line)
                        ts = data['timestamp'][11:16]  # HH:MM
                        display_logs.append(f"| {ts} | {data['intent_tag']} | {data['text']} |")
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"[Synthesizer] Erreur lecture journal: {e}")
            return "Erreur lecture journal", []

        # 2. RAG Hybride (Vecteur + Graphe)
        past_memories = "Aucun souvenir connexe."
        rag_docs = []

        # A. Recherche Vectorielle (Classique)
        if recent_text_blob:
            # On prend un échantillon plus petit pour l'embedding
            query_emb = self.router.get_embedding(recent_text_blob[-500:])
            if query_emb is not None:
                results = self.vector_db.search_similar(query_emb, n_results=3)
                if results and results['documents'] and results['documents'][0]:
                    rag_docs.extend(results['documents'][0])

        # B. Recherche Graphique (Nœuds Conscients / Ignited)
        if self.graph:
            # On récupère les nœuds les plus actifs du moment (Tri par poids dynamique)
            # On ignore les nœuds avec 0 activation pour ne pas polluer si calme
            active_nodes = [
                n for n in self.graph.nodes.values()
                if n.activation > 0
            ]
            # Tri décroissant
            active_nodes.sort(key=lambda x: x.get_current_weight(), reverse=True)

            # On prend le Top 3
            for node in active_nodes[:3]:
                # On ajoute une mention explicite que c'est le "Système" qui pense
                rag_docs.append(
                    f"[CONSCIENCE SYSTÈME] Note activée : [[{node.title}]] (Poids: {node.get_current_weight():.1f})")

        if rag_docs:
            past_memories = "\n".join([f"- {doc}" for doc in rag_docs])

        # 3. Récupération de l'historique des briefings
        vocal_history = "*(Aucun briefing vocal)*"
        if self.history_path.exists():
            with open(self.history_path, "r", encoding="utf-8") as f:
                vocal_history = f.read()

        # 4. Synthèse LLM & Extraction
        try:
            recent_logs = "\n".join(current_events[-5:])  # Les 5 derniers échanges
            older_logs = "\n".join(current_events[:-5])  # Le contexte d'avant

            prompt_content = (
                f"CONTEXTE GLOBAL (Ne pas répéter les concepts déjà acquis) :\n{older_logs}\n\n"
                f"DISCUSSION ACTUELLE (FOCUS ICI - Extraire nouveaux concepts) :\n{recent_logs}\n\n"
                f"SOUVENIRS & CONSCIENCE DU SYSTÈME :\n{past_memories}"
            )

            # [LOGGING WEB] Sauvegarde du Prompt (Input)
            self._log_llm_trace("INPUT", prompt_content)

            response = self.client.chat.completions.create(
                model=Config.ANALYST_MODEL_NAME,
                messages=[
                    {"role": "system", "content": Config.ANALYST_PROMPT},
                    {"role": "user", "content": prompt_content}
                ],
                temperature=Config.TEMP_ANALYST
            )

            # [LOGGING WEB] Sauvegarde de la Réponse (Output)
            raw_content = response.choices[0].message.content
            self._log_llm_trace("OUTPUT", raw_content)

            raw_content = response.choices[0].message.content
        except Exception as e:
            return f"⚠️ Erreur LLM : {e}", []

        # 5. Parsing (Découpage Dashboard / Concepts)
        dashboard_content = raw_content
        concepts = []

        if "---EXTRACTION_START---" in raw_content:
            try:
                parts = raw_content.split("---EXTRACTION_START---")
                dashboard_content = parts[0].strip()
                extraction_block = parts[1].split("---EXTRACTION_END---")[0]

                concept_blocks = extraction_block.split("###")
                for block in concept_blocks:
                    if "TITRE:" in block and "CONTENU:" in block:
                        part_title = block.split("TITRE:")[1].split("TAGS:")[0].strip()
                        part_tags = block.split("TAGS:")[1].split("CONTENU:")[0].strip()
                        part_content = block.split("CONTENU:")[1].strip()

                        clean_tags = [t.strip() for t in part_tags.replace('[', '').replace(']', '').split(',')]

                        if part_title and part_content:
                            concepts.append({
                                "title": part_title,
                                "tags": clean_tags,
                                "content": part_content
                            })
            except Exception as parse_error:
                print(f"[Synthesizer] ⚠️ Erreur parsing : {parse_error}")

        # 6. Assemblage final du Markdown
        final_md = dashboard_content + "\n\n"
        final_md += "### 🏛️ Connexions avec le Passé (RAG & Graphe)\n" + past_memories + "\n\n"
        final_md += "### 📜 Journal de Session\n"
        final_md += "| Heure | Tags | Transcription |\n| :--- | :--- | :--- |\n" + "\n".join(display_logs) + "\n\n"
        final_md += "---\n\n### 🎙️ Historique des Briefings\n" + vocal_history

        return final_md, concepts

    def _log_llm_trace(self, type_msg: str, content: str):
        trace_path = Config.LOGS_DIR / "llm_trace.jsonl"
        entry = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "type": type_msg,  # INPUT ou OUTPUT
            "content": content
        }
        try:
            with open(trace_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except:
            pass

    def generate_vocal_brief(self, markdown_content: str) -> str:
        """Génère le texte vocal."""
        try:
            text_for_voice = markdown_content.split("### 🏛️")[0]

            response = self.client.chat.completions.create(
                model=Config.ANALYST_MODEL_NAME,
                messages=[
                    {"role": "system", "content": Config.SYSTEM_PROMPT},
                    {"role": "user", "content": f"Dashboard actuel :\n{text_for_voice}"}
                ],
                temperature=Config.TEMP_CREATIVE # Un peu plus créatif
            )
            brief_text = response.choices[0].message.content

            timestamp = datetime.now().strftime("%H:%M")
            with open(self.history_path, "a", encoding="utf-8") as f:
                f.write(f"**[{timestamp}]** : {brief_text}\n\n")

            return brief_text
        except Exception as e:
            print(f"[Analyste] ❌ Erreur Briefing : {e}")
            return ""