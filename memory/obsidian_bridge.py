import httpx
import urllib3
from config import Config

# On désactive les warnings liés au certificat auto-signé (localhost)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ObsidianBridge:
    """
    Gère la communication avec le plugin Obsidian Local REST API.
    Responsabilité : I/O vers le coffre Obsidian (Lecture/Écriture).
    """

    def __init__(self):
        self.base_url = Config.OBSIDIAN_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {Config.OBSIDIAN_API_KEY}",
            "Content-Type": "text/markdown"
        }
        # Client HTTP optimisé (verify=False car certificat local auto-signé)
        self.client = httpx.Client(verify=False, timeout=2.0)

    def _get_endpoint(self, path: str):
        """Nettoie le chemin pour l'URL."""
        # L'API s'attend à 'vault/MonFichier.md'
        clean_path = path.strip("/")
        return f"{self.base_url}/vault/{clean_path}"

    def check_connection(self) -> bool:
        """Vérifie si Obsidian est ouvert et l'API active."""
        try:
            response = self.client.get(f"{self.base_url}/")
            return response.status_code == 200
        except Exception:
            return False

    def update_dashboard(self, content: str):
        """Met à jour le Dashboard (Mode PUT = Écrasement complet)."""
        endpoint = self._get_endpoint(Config.OBSIDIAN_DASHBOARD_PATH)
        try:
            self.client.put(endpoint, content=content, headers=self.headers)
        except Exception as e:
            print(f"[Obsidian] ⚠️ Échec mise à jour Dashboard : {e}")

    def create_concept_note(self, filename: str, content: str, frontmatter: str):
        """
        Crée une note atomique dans le dossier Zettelkasten.
        filename: ex 'Cybernetique.md' (sans le dossier)
        """
        full_path = f"{Config.OBSIDIAN_ZETTEL_FOLDER}{filename}"
        endpoint = self._get_endpoint(full_path)
        full_content = frontmatter + "\n" + content

        try:
            # PUT crée le fichier s'il n'existe pas
            self.client.put(endpoint, content=full_content, headers=self.headers)
            print(f"[Obsidian] ✅ Note créée : {full_path}")
        except Exception as e:
            print(f"[Obsidian] ❌ Erreur création note {filename} : {e}")

    def append_to_note(self, filename: str, text_to_add: str):
        """
        Ajoute du contenu à la fin d'une note existante (Mode PATCH).
        Utilisé pour l'enrichissement sémantique (ADR-017).
        """
        full_path = f"{Config.OBSIDIAN_ZETTEL_FOLDER}{filename}"
        endpoint = self._get_endpoint(full_path)

        try:
            # L'API REST Obsidian supporte l'ajout via header spécifique ou appel PATCH selon config
            # Ici on utilise une lecture simple + réécriture pour compatibilité maximale
            # (Le vrai PATCH dépend de l'implémentation du plugin, la méthode safe est GET + PUT)
            current = self.client.get(endpoint, headers=self.headers)
            if current.status_code == 200:
                new_content = current.text + "\n\n" + text_to_add
                self.client.put(endpoint, content=new_content, headers=self.headers)
                print(f"[Obsidian] 🔄 Note enrichie : {filename}")
            else:
                print(f"[Obsidian] ⚠️ Note introuvable pour enrichissement : {filename}")
        except Exception as e:
            print(f"[Obsidian] ❌ Erreur append : {e}")

    def file_exists(self, filename: str) -> bool:
        """Vérifie si une note existe déjà (HEAD request)."""
        full_path = f"{Config.OBSIDIAN_ZETTEL_FOLDER}{filename}"
        endpoint = self._get_endpoint(full_path)
        try:
            # On demande juste les headers pour aller vite (pas le contenu)
            response = self.client.head(endpoint, headers=self.headers)
            return response.status_code == 200
        except Exception:
            return False