import numpy as np
import os
from datetime import datetime
from openai import OpenAI
from config import Config


class IntentRouter:
    def __init__(self):
        self.client = OpenAI(base_url=Config.ROUTER_BASE_URL, api_key="ollama")
        self.taxonomy = Config.TAXONOMY
        self._cached_taxonomy_embeddings = None
        # Fichier pour capturer les manques de la taxonomie
        self.reflexion_log = Config.LOGS_DIR / "tag_reflexion.log"

    def _get_embedding(self, text: str):
        try:
            response = self.client.embeddings.create(
                model=Config.EMBEDDING_MODEL_NAME,
                input=text
            )
            return np.array(response.data[0].embedding)
        except Exception as e:
            print(f"[Router] ❌ Erreur Embedding : {e}")
            return None

    def _precompute_taxonomy(self):
        print("[Router] 🧮 Initialisation de la taxonomie sémantique...")
        embeddings = []
        for tag in self.taxonomy:
            emb = self._get_embedding(tag)
            if emb is not None: embeddings.append(emb)
        self._cached_taxonomy_embeddings = np.array(embeddings)

    def route(self, text: str) -> str:
        if self._cached_taxonomy_embeddings is None:
            self._precompute_taxonomy()

        user_emb = self._get_embedding(text)
        if user_emb is None: return "[REFLEXION]"

        # Similarité Cosinus
        similarities = np.dot(self._cached_taxonomy_embeddings, user_emb) / (
                np.linalg.norm(self._cached_taxonomy_embeddings, axis=1) * np.linalg.norm(user_emb)
        )

        best_indices = np.argsort(similarities)[-3:][::-1]
        results = [f"[{self.taxonomy[i]}]" for i in best_indices if similarities[i] > 0.35]

        if not results:
            # --- LOG DE RÉFLEXION ---
            with open(self.reflexion_log, "a", encoding="utf-8") as f:
                timestamp = datetime.now().isoformat()
                f.write(f"{timestamp} | {text}\n")
            return "[REFLEXION]"

        return " ".join(results)