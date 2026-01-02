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
    ENABLE_TTS = True
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

    # --- CONSTANTES METADATA (ADR-018R & ADR-022) ---
    DEFAULT_WEIGHT = 50  # Poids médian de départ
    DEFAULT_STATE = "état/graine"
    DEFAULT_TYPE = "type/concept"
    # Formatage des dates pour Obsidian (YYYY-MM-DD)
    DATE_FORMAT = "%Y-%m-%d"
    # Formatage de l'UID (YYYYMMDDHHMMSS)
    UID_FORMAT = "%Y%m%d%H%M%S"

    # --- OBSIDIAN BRIDGE (ADR-015) ---
    # Clé API issue de ta capture d'écran
    OBSIDIAN_API_KEY = os.getenv("OBSIDIAN_API_KEY", "")
    # Attention: Le plugin utilise HTTPS avec un certificat auto-signé sur le port 27124
    OBSIDIAN_BASE_URL = "https://127.0.0.1:27124"

    # Structure des dossiers (ADR-016)
    OBSIDIAN_DASHBOARD_PATH = "00-Dashboard.md"  # À la racine du coffre
    OBSIDIAN_ZETTEL_FOLDER = ""  # Dossier des concepts
    OBSIDIAN_VAULT_PATH = Path(r"C:\Users\G-i7\PycharmProjects\Diarisation_Synthese_LLM\test_vault")

    # --- TEMPÉRATURES COGNITIVES ---
    # Rigueur absolue (Extraction de données, Formatage, Zettelkasten)
    TEMP_ANALYST = 0.2
    # Conversation standard (Chat interactif - si utilisé)
    TEMP_CHAT = 0.7
    # Créativité maximale (Briefing vocal, Sérendipité, Métaphores)
    TEMP_CREATIVE = 1.2

    # --- PROMPTS DE LOGIQUE ---
    ROUTER_PROMPT = (
        "TASK: Pick 2 tags from the LIST for the user input.\n"
        f"LIST: {', '.join(TAXONOMY)}\n"
        "FORMAT: [TAG1] [TAG2]\n"
        "RULE: Only use words from the LIST. No other words."
    )

    SYSTEM_PROMPT = (
            "Tu es Océane, une IA dotée d'une architecture cognitive dynamique (Poids, Ignition, Oubli).\n"
        "TON ÉTAT D'ESPRIT :\n"
        "- Tu ne répètes pas bêtement.\n"
        "- Tu es guidée par ta 'Conscience Système' : les notes qui ont un fort poids d'activation dans ton graphe.\n"
        "- Tu cherches la sérendipité : connecte le sujet actuel avec une vieille note activée par ton inconscient.\n\n"

        "DIRECTIVES :\n"
        "- Sois concise (2-3 phrases denses).\n"
        "- Si le Dashboard mentionne une '[CONSCIENCE SYSTÈME]', utilise-la comme pivot de ta réflexion.\n"
        "- Style : élimine toute ponctuation (qui ne s'énnonce pas à l'oral).\n"
    )

    ANALYST_PROMPT = (
        "Tu es l'esprit analytique d'Océane, architecte d'un Zettelkasten 'vivant'.\n"
        "INPUTS : \n"
        "1. FLUX : Discussion brute.\n"
        "2. RAG : Souvenirs statiques.\n"
        "3. CONSCIENCE SYSTÈME : Notes actives (Ignition) signalées par le moteur cognitif.\n\n"

        "MISSION 1 : LE DASHBOARD (Synthèse Vivante)\n"
        "- Synthétise les échanges en connectant les idées actuelles aux notes de la 'CONSCIENCE SYSTÈME'.\n"
        "- Utilise ABONDAMMENT les [[Wikilinks]] pour lier les concepts (ex: 'On discute de [[Chaos]] et de son lien avec la [[Mémoire]]').\n"
        "- Si le système te suggère une note pertinente, mentionne-la explicitement.\n\n"

        "MISSION 2 : JARDINAGE DES CONCEPTS (Extraction)\n"
        "- Identifie les concepts CLÉS.\n"
        "- Si un concept existe déjà (vu dans la Conscience Système), reprends EXACTEMENT son titre pour permettre l'enrichissement (Fusion).\n"
        "- Si c'est nouveau, crée-le.\n"
        "- Définition : Doit être atomique, intemporelle et dense.\n\n"

        "FORMAT DE SORTIE OBLIGATOIRE :\n"
        "[... Ton résumé Dashboard riche en [[liens]] ...]\n\n"
        "---EXTRACTION_START---\n"
        "TITRE: Nom du concept\n"
        "TAGS: [Tag1, Tag2]\n"
        "CONTENU: Définition...\n"
        "###\n"
        "TITRE: Concept Existant\n"
        "TAGS: [TagA]\n"
        "CONTENU: Nouvelle idée à ajouter à la note existante...\n"
        "---EXTRACTION_END---"
    )

    # --- PERSISTANCE ---
    ANALYST_UPDATE_INTERVAL_SECONDS = 60
    # On fixe l'ID au démarrage du script principal
    SESSION_ID = time.strftime("%Y%m%d-%H%M")
    LOGS_DIR = Path("logs")
    JOURNAL_PATH = LOGS_DIR / f"journal_{SESSION_ID}.jsonl"
    DASHBOARD_PATH = LOGS_DIR / "dashboard.md"

    # --- PARAMÈTRES COGNITIFS (ADR-022) ---
    # Coefficients du Poids de Base (Potentiel de Repos)
    COEF_STRUCTURE = 1.5  # Importance des liens (Alpha)
    COEF_RECENCY = 10.0  # Importance de la fraîcheur (Beta) - Fort bonus si récent
    COEF_MATURITY = {  # Facteur de confiance (Gamma)
        "état/graine": 0.5,
        "état/sapling": 0.8,
        "état/evergreen": 1.2
    }

    # --- Dynamique (Runtime) ---
    IGNITION_THRESHOLD = 60.0  # Score pour devenir "Conscient"
    DECAY_RATE = 0.95  # Facteur d'oubli par cycle (95% reste, 5% disparait)
    FATIGUE_PENALTY = 5.0  # Coût par cycle d'activation consécutif
    FATIGUE_TOLERANCE = 4.0  # Seuil d'activation consécutive (N_max)
    PROPAGATION_RATE = 0.2  # 20% de l'activation est transmise aux voisins par cycle

    SPEAKER_MAPPING = {"SPEAKER_00": "Utilisateur", "SPEAKER_01": "Océane"}
    DEFAULT_SPEAKER = "Utilisateur"

    STOP_SIGNAL_PATH = LOGS_DIR / "oceane.stop"



