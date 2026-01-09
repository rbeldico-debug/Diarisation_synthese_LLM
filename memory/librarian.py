import os
from datetime import datetime
from pathlib import Path

from core.settings import settings
from brain.router import IntentRouter
from memory.vector_manager import VectorManager
from memory.storage_manager import MemoryManager


class Librarian:
    """
    Responsable de l'intégrité de la base de connaissances.
    Implémente la "Zone Safety" (ADR-025) :
    Ne modifie jamais le texte utilisateur situé avant <!-- AI_GARDEN_START -->.
    """

    SAFETY_MARKER = "<!-- AI_GARDEN_START -->"

    def __init__(self):
        self.router = IntentRouter()
        self.vectors = VectorManager()
        self.storage = MemoryManager()

    def process_concept(self, title: str, content: str, tags: list) -> str:
        """
        Point d'entrée principal pour l'Analyste.
        Décide s'il faut créer ou mettre à jour une note.
        """
        safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '_', '-')]).strip()
        filename = f"{safe_title}.md"

        # 1. Le fichier existe-t-il physiquement ?
        if self.storage.obsidian.file_exists(filename):
            print(f"[Librarian] 📂 Enrichissement note existante : '{filename}'")
            self._update_garden_zone(filename, content)
            return filename

        # 2. Sinon, est-ce un doublon sémantique ? (Vecteurs)
        embedding = self.router.get_embedding(content)
        existing_filename = None
        if embedding is not None:
            existing_filename = self.vectors.find_existing_concept(embedding, threshold=0.15)

        if existing_filename:
            print(f"[Librarian] 🔄 Fusion sémantique vers : '{existing_filename}'")
            self._update_garden_zone(existing_filename, content)
            return existing_filename

        # 3. Création pure
        print(f"[Librarian] ✨ Nouvelle note : '{title}'")
        real_filename = self.storage.create_atomic_note(title, content, tags)

        # Indexation immédiate
        if embedding is not None:
            self.vectors.index_concept(real_filename, content, embedding, tags)

        return real_filename

    def _update_garden_zone(self, filename: str, new_ai_content: str):
        """
        Met à jour uniquement la partie réservée à l'IA.
        """
        full_path = f"{settings.OBSIDIAN_ZETTEL_FOLDER}{filename}"
        endpoint = self.storage.obsidian._get_endpoint(full_path)

        try:
            # 1. Lecture du contenu actuel via le Bridge (Obsidian REST API)
            response = self.storage.obsidian.client.get(endpoint, headers=self.storage.obsidian.headers)

            if response.status_code != 200:
                print(f"[Librarian] ❌ Impossible de lire {filename} pour mise à jour.")
                return

            current_text = response.text
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')

            # 2. Séparation User / AI
            if self.SAFETY_MARKER in current_text:
                # On garde tout ce qui est avant le marqueur (Partie Humaine Intouchable)
                user_part = current_text.split(self.SAFETY_MARKER)[0].strip()
            else:
                # Si pas de marqueur, tout est considéré comme humain
                user_part = current_text.strip()

            # 3. Reconstruction
            # On ajoute le nouveau contenu IA après le marqueur
            # On peut décider ici si on APPEND (ajoute) ou si on REPLACE (remplace) la zone IA.
            # Pour un "Jardin", l'IA cultive et remplace souvent sa synthèse précédente.
            # Ici, je choisis l'APPEND intelligent pour garder l'historique IA,
            # mais on pourrait changer pour écraser si ça devient trop long.

            updated_ai_part = (
                f"\n\n{self.SAFETY_MARKER}\n"
                f"### 🌱 Jardinage IA ({timestamp})\n"
                f"{new_ai_content}"
            )

            final_content = user_part + updated_ai_part

            # 4. Écriture
            self.storage.obsidian.client.put(
                endpoint,
                content=final_content,
                headers=self.storage.obsidian.headers
            )
            print(f"[Librarian] ✅ Zone Jardin mise à jour sur {filename}")

        except Exception as e:
            print(f"[Librarian] ❌ Erreur Update Garden : {e}")