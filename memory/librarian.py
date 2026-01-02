from datetime import datetime
from brain.router import IntentRouter
from memory.vector_manager import VectorManager
from memory.storage_manager import MemoryManager


class Librarian:
    """
    Responsable de l'intégrité de la base de connaissances.
    Applique la logique ADR-017 : Consolidation (Enrichissement) vs Création.
    """

    def __init__(self):
        self.router = IntentRouter()
        self.vectors = VectorManager()
        self.storage = MemoryManager()  # Contient self.storage.obsidian (Bridge)

    def process_concept(self, title: str, content: str, tags: list) -> str:
        """
        Traite un concept extrait par l'Analyste.
        Retourne le nom du fichier (pour les logs).
        """
        # Nettoyage du titre
        safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '_', '-')]).strip()
        potential_filename = f"{safe_title}.md"

        # --- CAS 1 : EXISTENCE PHYSIQUE (Nom Exact) ---
        # Si une note porte DÉJÀ ce nom précis (ex: "Chaos.md"), on enrichit.
        if self.storage.obsidian.file_exists(potential_filename):
            print(f"[Librarian] 📂 Fichier existant identifié : '{potential_filename}'. Fusion...")
            self._append_to_note(potential_filename, content)
            return potential_filename

        # --- CAS 2 : RECHERCHE SÉMANTIQUE (Vecteurs) ---
        # Si le nom n'existe pas, est-ce qu'on parle de la même chose qu'une autre note ?
        embedding = self.router.get_embedding(content)

        existing_filename = None
        if embedding is not None:
            # Seuil à 0.20 (environ 80% de similarité)
            existing_filename = self.vectors.find_existing_concept(embedding, threshold=0.20)

        if existing_filename:
            # C'est une fusion sémantique
            print(f"[Librarian] 🔄 Concept sémantiquement proche : '{existing_filename}'. Fusion...")
            self._append_to_note(existing_filename, content)
            return existing_filename
        else:
            # --- CAS 3 : CRÉATION PURE ---
            print(f"[Librarian] ✨ Nouveau concept pur : '{title}'. Création...")
            real_filename = self.storage.create_atomic_note(title, content, tags)

            # On indexe immédiatement le nouveau concept dans ChromaDB
            if embedding is not None:
                self.vectors.index_concept(real_filename, content, embedding, tags)

            return real_filename

    def _append_to_note(self, filename: str, content: str):
        """Ajoute le contenu avec un timestamp."""
        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M')
        # On prépare un bloc Markdown propre
        append_text = f"\n\n### Enrichissement IA ({timestamp})\n{content}"

        self.storage.obsidian.append_to_note(filename, append_text)