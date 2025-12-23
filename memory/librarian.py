from brain.router import IntentRouter
from memory.vector_manager import VectorManager
from memory.storage_manager import MemoryManager


class Librarian:
    """
    Responsable de l'intégrité de la base de connaissances.
    Applique la logique ADR-017 : Consolidation (Enrichissement) vs Création.
    """

    def __init__(self):
        self.router = IntentRouter()  # Pour calculer les embeddings
        self.vectors = VectorManager()  # Pour chercher/indexer
        self.storage = MemoryManager()  # Pour écrire dans Obsidian

    def process_concept(self, title: str, content: str, tags: list):
        # 0. Nettoyage préventif du titre pour simuler le nom de fichier
        # (On utilise la même logique que storage_manager pour deviner le nom)
        safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '_', '-')]).strip()
        potential_filename = f"{safe_title}.md"

        # --- GARDE-FOU 1 : EXISTENCE PHYSIQUE (Nom Exact) ---
        if self.storage.obsidian.file_exists(potential_filename):
            print(f"[Librarian] 📂 Fichier existant identifié : '{potential_filename}'. Fusion directe.")
            self.storage.obsidian.append_to_note(potential_filename, content)
            return  # On s'arrête là, pas besoin de calcul vectoriel coûteux

        # 1. Calcul du vecteur (si pas trouvé par nom)
        embedding = self.router.get_embedding(content)
        if embedding is None: return

        # 2. Recherche Sémantique (Vecteurs)
        existing_filename = self.vectors.find_existing_concept(embedding, threshold=0.20) # On monte un peu le seuil (0.15 -> 0.20)

        if existing_filename:
            # --- CAS A : FUSION (Enrichissement) ---
            print(f"[Librarian] 🔄 Concept sémantiquement proche : '{existing_filename}'. Fusion...")
            self.storage.obsidian.append_to_note(existing_filename, content)
        else:
            # --- CAS B : CRÉATION ---
            print(f"[Librarian] ✨ Nouveau concept pur : '{title}'. Création...")
            real_filename = self.storage.create_atomic_note(title, content, tags)
            self.vectors.index_concept(real_filename, content, embedding, tags)
