import chromadb
from core.settings import settings

class VectorManager:
    """
    Gère la mémoire à long terme via ChromaDB.
    Deux collections distinctes :
    1. 'gerald_memory' : Logs de conversation (Pour le RAG contextuel).
    2. 'oceane_concepts' : Base de connaissances (Pour le dédoublonnage Zettelkasten).
    """

    def __init__(self):
        try:
            self.client = chromadb.HttpClient(
                host=settings.CHROMA_HOST,
                port=settings.CHROMA_PORT
            )

            # Collection 1 : Souvenirs de conversation
            self.memory_collection = self.client.get_or_create_collection(name="gerald_memory")

            # Collection 2 : Concepts atomiques (Zettelkasten)
            self.concept_collection = self.client.get_or_create_collection(
                name="oceane_concepts",
                metadata={"hnsw:space": "cosine"}
            )
            print("[Vecteur] 🟢 Connexion ChromaDB établie (2 collections).")
        except Exception as e:
            print(f"[Vecteur] ⚠️ Erreur d'initialisation Chroma : {e}")
            # IMPORTANT : On définit les attributs à None pour éviter le crash AttributeError
            self.memory_collection = None
            self.concept_collection = None

    # --- MÉTHODES POUR LES LOGS (RAG) ---
    def add_to_memory(self, text: str, embedding: list, metadata: dict):
        if not self.memory_collection: return
        try:
            doc_id = f"msg_{metadata.get('timestamp').replace(':', '-')}"

            # CORRECTIF : Gestion sécurisée du type embedding
            safe_embedding = embedding.tolist() if hasattr(embedding, 'tolist') else embedding

            self.memory_collection.add(
                ids=[doc_id],
                embeddings=[safe_embedding],
                documents=[text],
                metadatas=[metadata]
            )
        except Exception as e:
            print(f"[Vecteur] ❌ Erreur stockage log : {e}")

    def search_similar(self, query_embedding: list, n_results: int = 5):
        if not self.memory_collection: return None
        try:
            safe_embedding = query_embedding.tolist() if hasattr(query_embedding, 'tolist') else query_embedding
            return self.memory_collection.query(
                query_embeddings=[safe_embedding],
                n_results=n_results
            )
        except Exception as e:
            print(f"[Vecteur] ⚠️ Erreur recherche memory : {e}")
            return None

    # --- MÉTHODES POUR LES CONCEPTS (DÉDOUBLONNAGE) ---
    def find_existing_concept(self, embedding: list, threshold: float = 0.15):
        """
        Cherche un concept sémantiquement proche.
        """
        if not self.concept_collection: return None
        try:
            safe_embedding = embedding.tolist() if hasattr(embedding, 'tolist') else embedding

            results = self.concept_collection.query(
                query_embeddings=[safe_embedding],
                n_results=1
            )

            if results['distances'] and len(results['distances'][0]) > 0:
                distance = results['distances'][0][0]
                existing_id = results['ids'][0][0]  # L'ID est le nom du fichier

                if distance < threshold:
                    return existing_id  # On retourne le nom du fichier existant

            return None
        except Exception as e:
            print(f"[Vecteur] ⚠️ Erreur recherche concept : {e}")
            return None

    def index_concept(self, filename: str, content: str, embedding: list, tags: list):
        """Enregistre un nouveau concept dans l'index."""
        if not self.concept_collection: return
        try:
            safe_embedding = embedding.tolist() if hasattr(embedding, 'tolist') else embedding

            self.concept_collection.add(
                ids=[filename],
                embeddings=[safe_embedding],
                documents=[content],
                metadatas={"tags": str(tags)}
            )
            print(f"[Vecteur] 🧠 Concept indexé : {filename}")
        except Exception as e:
            print(f"[Vecteur] ❌ Erreur indexation concept : {e}")