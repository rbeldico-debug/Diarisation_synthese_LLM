import json
import time
from datetime import datetime
from core.settings import settings
from memory.obsidian_bridge import ObsidianBridge


class MemoryManager:
    def __init__(self):
        settings.LOGS_DIR.mkdir(exist_ok=True)
        # On génère un ID de session localement si ce n'est pas fait ailleurs
        session_id = time.strftime("%Y%m%d-%H%M")
        self.journal_path = settings.LOGS_DIR / f"journal_{session_id}.jsonl"

        self.obsidian = ObsidianBridge()
        if self.obsidian.check_connection():
            print("[Mémoire] 🟢 Connecté à Obsidian Vault.")
        else:
            print("[Mémoire] 🟠 Obsidian non détecté (Mode Backup Local).")

    def log_event(self, source, text, intent="FLUX LIBRE", extra=None):
        payload = {
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "text": text,
            "intent_tag": intent,
            "meta": extra or {},
            "ignored": False
        }
        with open(self.journal_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def update_dashboard(self, markdown_content):
        self.obsidian.update_dashboard(markdown_content)
        backup_path = settings.LOGS_DIR / "dashboard_backup.md"
        with open(backup_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

    def create_atomic_note(self, title: str, content: str, tags: list) -> str:
        """Crée une note dans 00_Inbox."""
        safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '_', '-')]).strip()
        filename = f"{safe_title}.md"

        # CHEMIN FORCÉ VERS INBOX
        full_path_relative = f"{settings.OBSIDIAN_INBOX_FOLDER}{filename}"

        now = datetime.now()
        uid = now.strftime(settings.UID_FORMAT)
        date_str = now.strftime(settings.DATE_FORMAT)

        final_tags = set(tags)
        final_tags.add(settings.DEFAULT_TYPE)
        final_tags.add(settings.DEFAULT_STATE)
        tags_yaml = "\n".join([f"  - {t}" for t in final_tags])

        frontmatter = (
            "---\n"
            f"uid: {uid}\n"
            "aliases: []\n"
            "tags:\n"
            f"{tags_yaml}\n"
            f"poids: {settings.DEFAULT_WEIGHT}\n"
            "source:\n"
            "  - IA\n"
            f"date_created: {date_str}\n"
            f"date_updated: {date_str}\n"
            "---\n"
        )

        # Appel avec chemin complet
        self.obsidian.create_note_at_path(full_path_relative, content, frontmatter)
        return filename