import time

class WarmupManager:
    """
    Module spécialisé pour stabiliser le système au démarrage.
    Vérifie les conteneurs Docker et précharge les modèles.
    """

    def __init__(self, inference, router, vector_db, stop_event):
        self.inference = inference
        self.router = router
        self.vector_db = vector_db
        self.stop_event = stop_event # <--- Ajout de l'event

    def perform_all(self):
        # On vérifie avant chaque étape si l'arrêt n'a pas été demandé
        if self.stop_event.is_set(): return

        print("\n--- 🏁 PHASE DE PRÉCHAUFFAGE GÉNÉRAL ---")

        # 1. Test ChromaDB (Docker)
        try:
            self.vector_db.client.heartbeat()
            print("[Warmup] ✅ ChromaDB est en ligne.")
        except Exception:
            print("[Warmup] ❌ ChromaDB injoignable.")

        if self.stop_event.is_set(): return

        # 2. Test STT
        self.inference.warm_up()

        if self.stop_event.is_set(): return

        # 3. Taxonomie
        print("[Warmup] 🧮 Pré-calcul de la taxonomie sémantique...")
        self.router.get_embedding("test") # Version courte pour tester la connexion
        self.router._precompute_taxonomy()

        print("--- ✅ SYSTÈME PRÊT --- \n")