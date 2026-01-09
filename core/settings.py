import os
from pathlib import Path
from typing import List, Dict, Set
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    # --- INFRASTRUCTURE ---
    LLM_BASE_URL: str = "http://localhost:11434/v1"
    LLM_MODEL_NAME: str = "gpt-oss:20b"
    ANALYST_MODEL_NAME: str = "gpt-oss:20b"

    WHISPER_BASE_URL: str = "http://localhost:8000/v1"
    WHISPER_MODEL: str = "Systran/faster-whisper-large-v3"

    ROUTER_BASE_URL: str = "http://localhost:11435/v1"
    ROUTER_MODEL_NAME: str = "mistral-nemo"
    EMBEDDING_MODEL_NAME: str = "mxbai-embed-large"

    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001

    # --- AUDIO & VAD (P1) ---
    SAMPLE_RATE: int = 16000
    BLOCK_SIZE: int = 512
    VAD_THRESHOLD: float = 0.5
    VAD_MIN_SILENCE_DURATION_MS: int = 1000

    # --- SYNTHÈSE VOCALE (P3) ---
    ENABLE_TTS: bool = True
    TTS_VOICE: str = "fr-FR-VivienneMultilingualNeural"

    # --- CONSTANTES METADATA ---
    DEFAULT_WEIGHT: float = 50.0
    DEFAULT_STATE: str = "état/graine"
    DEFAULT_TYPE: str = "type/concept"
    DATE_FORMAT: str = "%Y-%m-%d"
    UID_FORMAT: str = "%Y%m%d%H%M%S"

    # --- OBSIDIAN BRIDGE ---
    OBSIDIAN_API_KEY: str = Field(default="", description="Clé API Obsidian Local REST")
    OBSIDIAN_BASE_URL: str = "https://127.0.0.1:27124"
    OBSIDIAN_DASHBOARD_PATH: str = "00-Dashboard.md"
    OBSIDIAN_INBOX_FOLDER: str = "00_Inbox/"
    OBSIDIAN_ZETTEL_FOLDER: str = "10_Zettelkasten/"
    # Note: On utilise Path pour une gestion cross-platform (Windows/Linux)
    OBSIDIAN_VAULT_PATH: Path = Field(default=Path("test_vault"))

    # --- TEMPÉRATURES ---
    TEMP_ANALYST: float = 0.2
    TEMP_CHAT: float = 0.7
    TEMP_CREATIVE: float = 1.2

    # --- PARAMÈTRES COGNITIFS ---
    COEF_STRUCTURE: float = 1.5
    COEF_RECENCY: float = 10.0
    COEF_MATURITY: Dict[str, float] = {
        "état/graine": 0.5,
        "état/sapling": 0.8,
        "état/evergreen": 1.2
    }

    IGNITION_THRESHOLD: float = 60.0
    DECAY_RATE: float = 0.95
    FATIGUE_PENALTY: float = 5.0
    FATIGUE_TOLERANCE: float = 4.0
    PROPAGATION_RATE: float = 0.2

    # --- LOGGING & PERSISTANCE ---
    ANALYST_UPDATE_INTERVAL_SECONDS: int = 60
    # SESSION_ID sera généré dynamiquement dans le main, pas ici
    LOGS_DIR: Path = Path("logs")

    # --- PROMPTS SYSTEME ---
    # (Je garde les prompts ici pour l'instant pour faciliter la transition,
    # ils bougeront probablement dans un fichier YAML ou JSON plus tard)
    SYSTEM_PROMPT: str = (
        "Tu es Océane, une IA dotée d'une architecture cognitive dynamique.\n"
        "Sois concise, directe, et évite la politesse inutile."
    )

    ANALYST_PROMPT: str = (
        "Tu es l'esprit analytique d'Océane.\n"
        "INPUTS: Une discussion en flux continu.\n"
        "MISSION:\n"
        "1. Synthétise les échanges récents en un paragraphe dense avec des [[WikiLinks]].\n"
        "2. Identifie les concepts émergents qui méritent une note permanente.\n\n"

        "RÈGLES STRICTES (INTERDICTIONS) :\n"
        "- NE JAMAIS définir les termes techniques du système comme : 'FLUX', 'INPUT', 'SYSTEME', 'CLAVIER'.\n"
        "- Ce sont des métadonnées, pas des concepts philosophiques. Ignore-les.\n"
        "- Ne cite pas tes propres messages précédents comme des nouvelles idées.\n\n"

        "FORMAT D'EXTRACTION OBLIGATOIRE :\n"
        "---EXTRACTION_START---\n"
        "TITRE: Nom du Concept\n"
        "TAGS: [Tag1, Tag2]\n"
        "CONTENU: Définition atomique...\n"
        "---EXTRACTION_END---"
    )

    ROUTER_SYSTEM_PROMPT: str = (
        "Tu es le système de routage d'Océane. Classifie l'intention de l'utilisateur.\n"
        "CATÉGORIES POSSIBLES :\n"
        "1. [READ] : Demande de lecture, de recherche ou d'explication d'une note existante.\n"
        "2. [WRITE] : Apport d'information, dictée, nouvelle idée à noter.\n"
        "3. [CMD] : Ordre technique (ex: 'Arrête', 'Efface', 'Synthetise').\n"
        "4. [CHAT] : Conversation sociale ou réflexion sans but précis.\n\n"
        "RÈGLE : Réponds UNIQUEMENT par le tag de catégorie. Rien d'autre."
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # Ignore les variables en trop dans le .env
    )


# Instance unique accessible partout
settings = Settings()