import os
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    # --- INFRASTRUCTURE ---
    LLM_BASE_URL = "http://localhost:11434/v1"
    LLM_MODEL_NAME = "gpt-oss:20b"
    ANALYST_MODEL_NAME = "gpt-oss:20b"

    WHISPER_BASE_URL = "http://localhost:8000/v1"
    WHISPER_MODEL = "Systran/faster-whisper-large-v3"

    ROUTER_BASE_URL = "http://localhost:11435/v1"
    ROUTER_MODEL_NAME = "mistral-nemo"
    EMBEDDING_MODEL_NAME = "mxbai-embed-large"

    CHROMA_URL = "http://localhost:8001"

    # --- AUDIO & VAD (P1) ---
    SAMPLE_RATE = 16000
    BLOCK_SIZE = 512
    VAD_THRESHOLD = 0.5 # Légèrement plus sensible
    VAD_MIN_SILENCE_DURATION_MS = 1000 # Réduit de 3000 à 700ms pour plus de réactivité

    # --- SYNTHÈSE VOCALE (P3) ---
    # On utilise Vivienne (Multilingue) ou Denise (Français pur)
    TTS_VOICE = "fr-FR-VivienneMultilingualNeural"

    # --- TAXONOMIE UNIVERSELLE (Inspirée CDU/Dewey) ---
    TAXONOMY = [
        # 0. GÉNÉRALITÉS & SYSTÈMES
        "SYSTEME", "CYBERNETIQUE", "INFORMATION", "IA", "ALGORITHME", "DATA", "LOGICIEL", "DOCUMENTATION",

        # 1. PHILOSOPHIE & LOGIQUE
        "LOGIQUE", "ETHIQUE", "EPISTEMOLOGIE", "METAPHYSIQUE", "MORALE", "ESTHETIQUE", "DIALECTIQUE",

        # 2. PSYCHOLOGIE & ESPRIT
        "COGNITION", "EMOTION", "COMPORTEMENT", "CONSCIENCE", "PERCEPTION", "MEMOIRE", "RESSENTI",

        # 3. SCIENCES SOCIALES & ÉCONOMIE
        "ECONOMIE", "SOCIOLOGIE", "DROIT", "POLITIQUE", "EDUCATION", "ANTHROPOLOGIE", "GESTION", "STRATEGIE",

        # 4. LANGAGE & COMMUNICATION
        "LINGUISTIQUE", "SEMANTIQUE", "RHETORIQUE", "COMMUNICATION", "TRADUCTION", "NARRATION",

        # 5. SCIENCES PURES
        "MATHEMATIQUES", "PHYSIQUE", "CHIMIE", "BIOLOGIE", "ASTRONOMIE", "GEOLOGIE", "EVOLUTION", "ENERGIE",

        # 6. SCIENCES APPLIQUÉES & TECH
        "INGENIERIE", "MEDECINE", "SANTE", "INFORMATIQUE", "ELECTRONIQUE", "MECANIQUE", "AGRONOMIE", "DOMOTIQUE",

        # 7. ARTS, JEUX & LOISIRS
        "ARCHITECTURE", "DESIGN", "MUSIQUE", "ARTS_VISUELS", "GAMEPLAY", "SPORT", "LOISIR", "SPECTACLE",

        # 8. LITTÉRATURE & CRÉATION
        "LITTERATURE", "POESIE", "ESSAI", "CRITIQUE", "FICTION",

        # 9. HISTOIRE & GÉOGRAPHIE
        "HISTOIRE", "GEOGRAPHIE", "BIOGRAPHIE", "ARCHEOLOGIE", "CULTURE",

        # 10. MÉTA-CATÉGORIES (Pour le Zettelkasten)
        "DEBUG", "OPTIMISATION", "PROJET", "REFLEXION", "NOTE_RAPIDE", "SYNTHESE", "PROBLEM_SOLVING"
    ]

    # --- PROMPTS DE LOGIQUE ---
    ROUTER_PROMPT = (
        "TASK: Pick 2 tags from the LIST for the user input.\n"
        f"LIST: {', '.join(TAXONOMY)}\n"
        "FORMAT: [TAG1] [TAG2]\n"
        "RULE: Only use words from the LIST. No other words."
    )

    SYSTEM_PROMPT = (
        "Tu es Océane, l'assistante personnelle de l'utilisateur. "
        "En te basant sur le dashboard de session, fais une synthèse orale élégante. "
        "Parle à la première personne. Ne cite jamais de balises markdown. "
        "Commence par : 'Ici Océane. Voici un point sur vos dernières réflexions.' "
        "Sois synthétique (4 phrases max) et mets en avant les liens entre les sujets."
    )

    ANALYST_PROMPT = (
        "Tu es l'esprit analytique d'Océane, un expert en gestion des connaissances (Zettelkasten).\n\n"
        "SOURCES DISPONIBLES :\n"
        "1. **CONTEXTE ACTUEL** : Les derniers échanges de la session.\n"
        "2. **SOUVENIRS CONNEXES** : Des fragments de pensées issus de tes sessions passées (via mémoire vectorielle).\n\n"
        "TA MISSION :\n"
        "- Produis une synthèse ARCHITECTURÉE en Markdown.\n"
        "- **Maillage Sémantique** : Relie impérativement les idées actuelles aux souvenirs passés si une connexion existe.\n"
        "- **Évolution** : Relève si l'utilisateur change d'avis ou approfondit un concept déjà croisé.\n"
        "- **Format** : Utilise des titres, des tableaux pour les décisions, et des listes à puces.\n\n"
        "CONSIGNES : Sois concis mais dense en informations. Ne cite pas d'IDs techniques."
    )

    # --- PERSISTANCE ---
    ANALYST_UPDATE_INTERVAL_SECONDS = 60
    # On fixe l'ID au démarrage du script principal
    SESSION_ID = time.strftime("%Y%m%d-%H%M")
    LOGS_DIR = Path("logs")
    JOURNAL_PATH = LOGS_DIR / f"journal_{SESSION_ID}.jsonl"
    DASHBOARD_PATH = LOGS_DIR / "dashboard.md"

    SPEAKER_MAPPING = {"SPEAKER_00": "Utilisateur", "SPEAKER_01": "Océane"}
    DEFAULT_SPEAKER = "Utilisateur"

    STOP_SIGNAL_PATH = LOGS_DIR / "oceane.stop"