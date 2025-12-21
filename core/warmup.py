import time


class WarmupManager:
    """
    Module spécialisé pour stabiliser le système au démarrage.
    Vérifie les conteneurs Docker et précharge les modèles.
    """

    def __init__(self, inference, router, vector_db):
        self.inference = inference
        self.router = router
        self.vector_db = vector_db

    def perform_all(self):
        print("\n--- 🏁 PHASE DE PRÉCHAUFFAGE GÉNÉRAL ---")

        # 1. Test ChromaDB (Docker)
        try:
            self.vector_db.client.heartbeat()
            print("[Warmup] ✅ ChromaDB est en ligne.")
        except Exception:
            print("[Warmup] ❌ ChromaDB injoignable. Vérifie le conteneur 'chromadb-server'.")

        # 2. Test STT (Whisper Docker)
        self.inference.warm_up()

        # 3. Taxonomie & Embeddings (Ollama Docker)
        print("[Warmup] 🧮 Pré-calcul de la taxonomie sémantique...")
        self.router._precompute_taxonomy()

        print("--- ✅ SYSTÈME PRÊT --- \n")