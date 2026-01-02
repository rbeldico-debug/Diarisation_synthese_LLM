import json
from datetime import datetime
from config import Config
from memory.obsidian_bridge import ObsidianBridge


class MemoryManager:
    """
    Orchestre la mémoire :
    1. Log Brut -> Fichier JSONL (Backup & Machine)
    2. Log Visuel -> Obsidian (Utilisateur)

    Implémente ADR-018R (Standardisation YAML) et ADR-020 (Logique Append-Only).
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
        """Pousse la synthèse vers Obsidian (Fichier Volatile)."""
        self.obsidian.update_dashboard(markdown_content)

        # Backup local
        backup_path = Config.LOGS_DIR / "dashboard_backup.md"
        with open(backup_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

    def create_atomic_note(self, title: str, content: str, tags: list) -> str:
        """
        ADR-018R : Crée une note respectant le schéma strict de métadonnées.
        Garantit la compatibilité avec le futur moteur de poids.
        """
        # 1. Nettoyage du titre (Caractères sûrs uniquement)
        safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '_', '-')]).strip()
        filename = f"{safe_title}.md"

        # 2. Préparation des données dynamiques
        now = datetime.now()
        uid = now.strftime(Config.UID_FORMAT)
        date_str = now.strftime(Config.DATE_FORMAT)

        # 3. Gestion des Tags (Fusion System + User)
        # On s'assure d'avoir les tags obligatoires définis dans Config
        final_tags = set(tags)
        final_tags.add(Config.DEFAULT_TYPE)  # ex: type/concept
        final_tags.add(Config.DEFAULT_STATE)  # ex: état/graine

        # Formatage YAML propre pour les tags (liste à tirets)
        tags_yaml = "\n".join([f"  - {t}" for t in final_tags])

        # 4. Construction du Frontmatter (ADR-018R)
        frontmatter = (
            "---\n"
            f"uid: {uid}\n"
            "aliases: []\n"
            "tags:\n"
            f"{tags_yaml}\n"
            f"poids: {Config.DEFAULT_WEIGHT}\n"
            "source:\n"
            "  - IA\n"
            f"  - [[{Config.SESSION_ID}]]\n"
            f"date_created: {date_str}\n"
            f"date_updated: {date_str}\n"
            "---\n"
        )

        # 5. Appel au pont Obsidian
        self.obsidian.create_concept_note(filename, content, frontmatter)

        return filename