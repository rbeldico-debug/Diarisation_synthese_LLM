import json
from datetime import datetime
from typing import Tuple, List, Dict, Any
from openai import OpenAI

# MIGRATION CONFIG
from core.settings import settings

from memory.vector_manager import VectorManager
from brain.router import IntentRouter


class Synthesizer:
    def __init__(self, graph_manager: Any = None):
        self.client = OpenAI(base_url=settings.LLM_BASE_URL, api_key="ollama")
        self.vector_db = VectorManager()
        self.router = IntentRouter()
        # Note: SESSION_ID n'est pas dans settings, on scanne ou on génère un nom générique
        self.history_path = settings.LOGS_DIR / f"briefings_last.md"
        self.graph = graph_manager

    def generate_summary(self) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Génère le dashboard et extrait les concepts.
        Nettoyé pour éviter la pollution sémantique (FLUX, etc.)
        """
        # Logique pour trouver le journal le plus récent
        journal_files = list(settings.LOGS_DIR.glob("journal_*.jsonl"))
        if not journal_files:
            return "En attente de données...", []
        latest_journal = max(journal_files, key=lambda f: f.stat().st_mtime)

        # 1. Collecte des logs récents (NETTOYAGE ICI)
        current_events = []
        recent_text_blob = ""
        display_logs = []

        try:
            with open(latest_journal, "r", encoding="utf-8") as f:
                lines = f.readlines()

                # A. Pour le LLM (Les 50 dernières lignes)
                for line in lines[-50:]:
                    try:
                        data = json.loads(line)
                        if not data.get("ignored", False):
                            # MODIFICATION : On retire le tag technique [FLUX] du prompt LLM
                            # On garde juste le texte pur.
                            # Si on veut garder le locuteur : f"- {data.get('source', 'Utilisateur')}: {data['text']}"
                            # Ici on fait simple pour le focus conceptuel :
                            current_events.append(f"- {data['text']}")
                            recent_text_blob += data['text'] + " "
                    except json.JSONDecodeError:
                        continue

                # B. Pour l'affichage Web (On garde les tags ici pour l'humain)
                for line in lines[-10:]:
                    try:
                        data = json.loads(line)
                        ts = data['timestamp'][11:16]
                        display_logs.append(f"| {ts} | {data['intent_tag']} | {data['text']} |")
                    except:
                        continue
        except Exception as e:
            print(f"[Synthesizer] Erreur lecture journal: {e}")
            return "Erreur lecture journal", []

        # 2. RAG Hybride
        past_memories = "Aucun souvenir connexe."
        rag_docs = []

        # A. Recherche Vectorielle
        if recent_text_blob:
            query_emb = self.router.get_embedding(recent_text_blob[-500:])
            if query_emb is not None:
                results = self.vector_db.search_similar(query_emb, n_results=5)  # On en demande plus pour filtrer
                if results and results['documents']:
                    for doc in results['documents'][0]:
                        # FILTRE ANTI-ECHO : On n'ajoute pas le souvenir s'il est identique à ce qu'on vient de dire
                        if doc.strip() not in recent_text_blob:
                            rag_docs.append(doc)

        # B. Recherche Graphique
        if self.graph:
            active_nodes = [n for n in self.graph.nodes.values() if n.activation > 0]
            active_nodes.sort(key=lambda x: x.get_current_weight(), reverse=True)
            for node in active_nodes[:3]:
                rag_docs.append(f"[CONSCIENCE SYSTÈME] Note activée : [[{node.title}]]")

        if rag_docs:
            past_memories = "\n".join([f"- {doc}" for doc in rag_docs[:5]])  # Top 5 retenu

        # 3. Récupération de l'historique des briefings
        vocal_history = "*(Aucun briefing vocal)*"
        if self.history_path.exists():
            with open(self.history_path, "r", encoding="utf-8") as f:
                vocal_history = f.read()

        # 4. Synthèse LLM & Extraction
        try:
            recent_logs = "\n".join(current_events[-5:])
            older_logs = "\n".join(current_events[:-5])

            prompt_content = (
                f"CONTEXTE GLOBAL (Ne pas répéter les concepts déjà acquis) :\n{older_logs}\n\n"
                f"DISCUSSION ACTUELLE (FOCUS ICI - Extraire nouveaux concepts) :\n{recent_logs}\n\n"
                f"SOUVENIRS & CONSCIENCE DU SYSTÈME :\n{past_memories}"
            )

            # [LOGGING WEB] Sauvegarde du Prompt (Input)
            self._log_llm_trace("INPUT", prompt_content)

            response = self.client.chat.completions.create(
                model=settings.ANALYST_MODEL_NAME,
                messages=[
                    {"role": "system", "content": settings.ANALYST_PROMPT},
                    {"role": "user", "content": prompt_content}
                ],
                temperature=settings.TEMP_ANALYST
            )

            # [LOGGING WEB] Sauvegarde de la Réponse (Output)
            raw_content = response.choices[0].message.content
            self._log_llm_trace("OUTPUT", raw_content)

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
        trace_path = settings.LOGS_DIR / "llm_trace.jsonl"
        entry = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "type": type_msg,
            "content": content
        }
        try:
            with open(trace_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except:
            pass

    def generate_vocal_brief(self, markdown_content: str) -> str:
        try:
            text_for_voice = markdown_content.split("### 🏛️")[0]
            response = self.client.chat.completions.create(
                model=settings.ANALYST_MODEL_NAME,
                messages=[
                    {"role": "system", "content": settings.SYSTEM_PROMPT},
                    {"role": "user", "content": f"Dashboard actuel :\n{text_for_voice}"}
                ],
                temperature=settings.TEMP_CREATIVE
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"[Analyste] ❌ Erreur Briefing : {e}")
            return ""