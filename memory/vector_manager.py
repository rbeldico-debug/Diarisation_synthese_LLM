import chromadb
from config import Config


class VectorManager:
    def __init__(self):
        # On utilise HttpClient pour se connecter au Docker chromadb-server
        try:
            self.client = chromadb.HttpClient(host="localhost", port=8001)
            # On récupère la collection.
            self.collection = self.client.get_or_create_collection(name="gerald_memory")
        except Exception as e:
            print(f"[Vecteur] ⚠️ Erreur d'initialisation Chroma : {e}")

    def add_to_memory(self, text: str, embedding: list, metadata: dict):
        try:
            # On génère un ID basé sur le timestamp pour éviter les collisions
            doc_id = f"msg_{metadata.get('timestamp').replace(':', '-')}"

            self.collection.add(
                ids=[doc_id],
                embeddings=[embedding.tolist()],
                documents=[text],
                metadatas=[metadata]
            )
        except Exception as e:
            print(f"[Vecteur] ❌ Erreur stockage : {e}")

    def search_similar(self, query_embedding: list, n_results: int = 5):
        """Recherche les souvenirs les plus proches."""
        return self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=n_results
        )