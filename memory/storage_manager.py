import json
from datetime import datetime
from config import Config
from memory.obsidian_bridge import ObsidianBridge


class MemoryManager:
    """
    Orchestre la mémoire :
    1. Log Brut -> Fichier JSONL (Backup & Machine)
    2. Log Visuel -> Obsidian (Utilisateur)
    """

    def __init__(self):
        Config.LOGS_DIR.mkdir(exist_ok=True)
        self.journal_path = Config.JOURNAL_PATH

        # Initialisation du pont vers Obsidian
        self.obsidian = ObsidianBridge()

        # Vérification connexion au démarrage
        if self.obsidian.check_connection():
            print("[Mémoire] 🟢 Connecté à Obsidian Vault.")
        else:
            print("[Mémoire] 🟠 Obsidian non détecté (Mode Backup Local uniquement).")

    def log_event(self, source, text, intent="FLUX LIBRE", extra=None):
        """Source de vérité brute (ADR-010)."""
        payload = {
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "text": text,
            "intent_tag": intent,
            "meta": extra or {},
            "ignored": False
        }
        # Écriture locale toujours active (Sécurité)
        with open(self.journal_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def update_dashboard(self, markdown_content):
        """Pousse la synthèse vers Obsidian."""
        # On délègue l'affichage à Obsidian
        self.obsidian.update_dashboard(markdown_content)

        # (Optionnel) On peut garder une copie locale si tu veux debug sans Obsidian
        backup_path = Config.LOGS_DIR / "dashboard_backup.md"
        with open(backup_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

    def create_atomic_note(self, title: str, content: str, tags: list) -> str:
        """ADR-016 : Crée une note via le Bridge et retourne son nom de fichier."""
        # Nettoyage du titre (On garde lettres, chiffres, espaces, tirets, underscores)
        safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '_', '-')]).strip()
        filename = f"{safe_title}.md"

        # Construction du Frontmatter
        frontmatter = (
            "---\n"
            f"id: {datetime.now().strftime('%Y%m%d%H%M%S')}\n"
            "type: concept\n"
            f"tags: {tags}\n"
            f"source: [[00-Dashboard]]\n"
            "---\n"
        )

        # Appel au pont Obsidian
        self.obsidian.create_concept_note(filename, content, frontmatter)

        # IMPORTANT : On retourne le nom exact pour que le Bibliothécaire puisse l'indexer
        return filename