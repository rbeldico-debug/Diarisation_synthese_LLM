# 🌊 Océane - Assistant de Réflexion Sémantique (v2.5)

Océane est un écosystème multi-agents local conçu pour transformer vos réflexions orales en un **Zettelkasten** structuré dans Obsidian.

## 🏗️ Architecture des Agents
1. **P1: L'Oreille** (Silero VAD) : Découpe le flux audio en segments logiques.
2. **P2: Le Cerveau** (Whisper + Semantic Router) : Transcrit, identifie les locuteurs et classe les intentions via **Similarité Cosinus** (pas de LLM pour le tri, 100% fiable).
3. **P3: La Bouche** (Edge-TTS) : Restitue des briefings vocaux haute fidélité (Voix: Vivienne).
4. **P4: L'Analyste** (Mistral-Nemo + RAG) : Analyse le journal JSONL, interroge **ChromaDB** pour retrouver des souvenirs passés, et sculpte le Dashboard Obsidian.

## 🧠 Fonctions Avancées
- **Similarité Sémantique** : Plus d'hallucination de tags. Le système compare mathématiquement vos propos à la Taxonomie Universelle.
- **RAG (Retrieval Augmented Generation)** : L'analyste crée des liens `[[WikiLinks]]` entre vos propos actuels et vos réflexions des sessions précédentes.
- **Zettelkasten Automatique** : À chaque arrêt, une note atomique formatée est archivée dans votre Vault Obsidian.

## 🛠️ Maintenance & Commandes
- **Démarrage** : `execute.bat` (Lance Docker Whisper, ChromaDB, Ollama et le script Main).
- **Arrêt propre** : `python stop.py` (Déclenche l'archivage final et coupe les processus).

## 📊 Architecture du Flux

```mermaid
graph TD
    subgraph "HÔTE WINDOWS (Python 3.11)"
        A[Microphone] --> B(P1: Oreille - Silero VAD)
        B -->|Segment Audio| C(P2: Cerveau - Orchestrateur)
        C -->|Texte + Intent| D[(Journal.jsonl - Journaling)]
        D --> E(P4: Analyste - Synthèse)
        E -->|Markdown| F[Dashboard.md - Zettelkasten]
        C -->|Texte Réponse| G(P3: Bouche - Piper TTS)
    end

    subgraph "DOCKER (Isolé - GPU)"
        C -->|API| H[Speaches: Whisper + Diarization]
        C -->|API| I[Router: Llama 1B]
    end

    subgraph "OLLAMA (Service Externe)"
        C -->|API| J[LLM Principal: gpt-oss-20b]
        E -->|API| J
    end
```

## 🛠️ Pré-requis

*   **OS** : Windows 10/11 avec **Docker Desktop** (WSL2 backend).
*   **GPU** : NVIDIA RTX (drivers à jour).
*   **Outils** : Ollama (installé sur Windows).

## 🚀 Installation Rapide

1.  **Préparer l'environnement Python** :
    ```bash
    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    ```

2.  **Lancer le moteur IA (Docker)** :
    *   Remplissez votre `HF_TOKEN` dans le fichier `docker-compose.yml`.
    *   Dans un terminal, lancez :
    ```bash
    docker compose up -d
    ```

3.  **Vérifier le serveur** :
    Accédez à [http://localhost:8000/docs](http://localhost:8000/docs). Si la page s'affiche, le moteur est prêt.

## ⚙️ Configuration

*   **Diarisation** : Automatiquement gérée par le serveur Speaches via l'argument `extra_body={"diarization": True}` dans `diarization.py`.
*   **VRAM** : Le modèle `large-v3` consomme environ 5-6 Go de VRAM sur votre GPU via Docker.

## ▶️ Utilisation

1.  Lancer Ollama.
2.  Lancer le conteneur Docker (si pas déjà fait).
3.  Exécuter le programme :
    ```bash
    python main.py
    ```

## 💎 Avantages de la v2.0
*   **Zéro Conflit** : Plus de problème de version NumPy ou de DLL CUDA manquantes.
*   **Performance** : Le modèle Whisper est pré-chargé dans la VRAM par Docker, éliminant la latence de chargement au premier mot.
*   **Portabilité** : Le code Python est devenu un simple client API ultra-léger.


---

### 4. Rappel du fichier `docker-compose.yml` (À placer à la racine)
C'est le fichier qui "sauve" ton projet.

```yaml
name: Diarisation_Synthese_LLM

services:
  # --- MOTEUR AUDIO (Whisper) ---
  whisper:
    image: ghcr.io/speaches-ai/speaches:latest-cuda
    container_name: whisper-server
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - whisper_data:/home/ubuntu/.cache/huggingface
    environment:
      - HF_TOKEN=[CLE API ICI]
      - HF_HOME=/home/ubuntu/.cache/huggingface
      - SPEACHES_MODELS_PRELOAD=Systran/faster-whisper-large-v3
      - WHISPER__MODEL=Systran/faster-whisper-large-v3
      - WHISPER__DEVICE=cuda
      - WHISPER__COMPUTE_TYPE=int8_float16
      - WHISPER__NUM_WORKERS=4
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]

  # --- LE CERVEAU UNIQUE (Ollama: Nemo + Embeddings) ---
  router-llm:
    image: ollama/ollama:latest
    container_name: LLM-router
    restart: unless-stopped
    ports:
      - "11435:11434"
    volumes:
      - ollama_storage:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]

  # --- LA MÉMOIRE VECTORIELLE (ChromaDB) ---
  chromadb:
    image: ghcr.io/chroma-core/chroma:latest
    container_name: chromadb-server
    restart: unless-stopped
    ports:
      - "8001:8000"
    volumes:
      - chroma_data:/chroma/chroma # Volume persistant pour le RAG
    environment:
      - IS_PERSISTENT=TRUE
      - ANONYMIZED_TELEMETRY=FALSE

volumes:
  whisper_data:
  ollama_storage:
  chroma_data:
```
