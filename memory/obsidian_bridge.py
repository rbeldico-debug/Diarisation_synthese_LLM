import httpx
import urllib3
from core.settings import settings

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class ObsidianBridge:
    def __init__(self):
        self.base_url = settings.OBSIDIAN_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {settings.OBSIDIAN_API_KEY}",
            "Content-Type": "text/markdown"
        }
        self.client = httpx.Client(verify=False, timeout=2.0)

    def _get_endpoint(self, path: str):
        clean_path = path.strip("/")
        return f"{self.base_url}/vault/{clean_path}"

    def check_connection(self) -> bool:
        try:
            response = self.client.get(f"{self.base_url}/")
            return response.status_code == 200
        except Exception:
            return False

    def update_dashboard(self, content: str):
        endpoint = self._get_endpoint(settings.OBSIDIAN_DASHBOARD_PATH)
        try:
            self.client.put(endpoint, content=content, headers=self.headers)
        except Exception as e:
            print(f"[Obsidian] ⚠️ Échec mise à jour Dashboard : {e}")

    def create_concept_note(self, filename: str, content: str, frontmatter: str):
        full_path = f"{settings.OBSIDIAN_ZETTEL_FOLDER}{filename}"
        endpoint = self._get_endpoint(full_path)
        full_content = frontmatter + "\n" + content
        try:
            self.client.put(endpoint, content=full_content, headers=self.headers)
            print(f"[Obsidian] ✅ Note créée : {full_path}")
        except Exception as e:
            print(f"[Obsidian] ❌ Erreur création note {filename} : {e}")

    def append_to_note(self, filename: str, text_to_add: str):
        full_path = f"{settings.OBSIDIAN_ZETTEL_FOLDER}{filename}"
        endpoint = self._get_endpoint(full_path)
        try:
            current = self.client.get(endpoint, headers=self.headers)
            if current.status_code == 200:
                new_content = current.text + "\n\n" + text_to_add
                self.client.put(endpoint, content=new_content, headers=self.headers)
                print(f"[Obsidian] 🔄 Note enrichie : {filename}")
        except Exception as e:
            print(f"[Obsidian] ❌ Erreur append : {e}")

    def file_exists(self, filename: str) -> bool:
        full_path = f"{settings.OBSIDIAN_ZETTEL_FOLDER}{filename}"
        endpoint = self._get_endpoint(full_path)
        try:
            response = self.client.head(endpoint, headers=self.headers)
            return response.status_code == 200
        except Exception:
            return False

    def create_note_at_path(self, relative_path: str, content: str, frontmatter: str):
        """Crée une note à un emplacement spécifique (ex: 00_Inbox/MaNote.md)"""
        endpoint = self._get_endpoint(relative_path)
        full_content = frontmatter + "\n" + content
        try:
            self.client.put(endpoint, content=full_content, headers=self.headers)
            print(f"[Obsidian] ✅ Note créée dans {relative_path}")
        except Exception as e:
            print(f"[Obsidian] ❌ Erreur création {relative_path} : {e}")