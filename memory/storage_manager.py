import json
import os
from datetime import datetime
from pathlib import Path
from config import Config


class MemoryManager:
    """
    Gère la persistance double : 
    1. Journal Brut (JSONL) pour la machine.
    2. Notes Atomiques (Markdown) pour l'utilisateur (Zettelkasten).
    """

    def __init__(self):
        Config.LOGS_DIR.mkdir(exist_ok=True)
        # Dossier spécifique pour Obsidian
        self.zettel_dir = Config.LOGS_DIR / "zettelkasten"
        self.zettel_dir.mkdir(exist_ok=True)

    def log_event(self, source, text, intent="FLUX LIBRE", extra=None):
        """Source de vérité brute (ADR-010)."""
        payload = {
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "text": text,
            "intent_tag": intent,
            "meta": extra or {},
            "ignored": False  # Utile pour l'ADR-012
        }
        with open(Config.JOURNAL_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def create_atomic_note(self, content: str, tags: list):
        """
        ADR-011 : Crée une note au format Obsidian-Zettelkasten.
        """
        uid = datetime.now().strftime("%Y%m%d%H%M")
        filename = self.zettel_dir / f"{uid}.md"

        frontmatter = (
            "---\n"
            f"id: {uid}\n"
            f"date: {datetime.now().isoformat()}\n"
            f"tags: {tags}\n"
            f"session: {Config.SESSION_ID}\n"
            "---\n\n"
        )

        with open(filename, "w", encoding="utf-8") as f:
            f.write(frontmatter + content)

        return uid