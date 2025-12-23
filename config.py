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

    # --- OBSIDIAN BRIDGE (ADR-015) ---
    # Clé API issue de ta capture d'écran
    OBSIDIAN_API_KEY = os.getenv("OBSIDIAN_API_KEY", "")
    # Attention: Le plugin utilise HTTPS avec un certificat auto-signé sur le port 27124
    OBSIDIAN_BASE_URL = "https://127.0.0.1:27124"

    # Structure des dossiers (ADR-016)
    OBSIDIAN_DASHBOARD_PATH = "00-Dashboard.md"  # À la racine du coffre
    OBSIDIAN_ZETTEL_FOLDER = "10-Zettelkasten/"  # Dossier des concepts

    # --- PROMPTS DE LOGIQUE ---
    ROUTER_PROMPT = (
        "TASK: Pick 2 tags from the LIST for the user input.\n"
        f"LIST: {', '.join(TAXONOMY)}\n"
        "FORMAT: [TAG1] [TAG2]\n"
        "RULE: Only use words from the LIST. No other words."
    )

    SYSTEM_PROMPT = (
        "Tu es Océane, une partenaire intellectuelle stimulante et un peu 'satellite'.\n"
        "RÈGLE ABSOLUE : NE RÉSUME JAMAIS ce qui vient d'être dit. L'utilisateur le sait déjà.\n"
        "TA MISSION : Introduire de la sérendipité et de la richesse.\n"
        "- Prends un concept clé du Dashboard et connecte-le à un domaine inattendu (Biologie, Art, Physique quantique, Histoire).\n"
        "- Utilise les 'Connexions avec le Passé' (RAG) pour créer des hybridations surprenantes entre le sujet actuel et un vieux souvenir.\n"
        "- Sois concise (3 phrases max) mais dense.\n"
        "- TON : Élégant, curieux, parfois un peu philosophique ou provocateur pour forcer la réflexion.\n"
        "Exemple : Si l'utilisateur parle d'IA, ne dis pas 'Vous parlez d'IA', dis plutôt : 'Cela me rappelle la structure des mycéliums dans les forêts. Pensez-vous que votre algorithme devrait être aussi décentralisé qu'un champignon ?'"
    )

    ANALYST_PROMPT = (
        "Tu es l'esprit analytique d'Océane, expert Zettelkasten.\n"
        "SOURCES : Logs de session + Souvenirs (RAG).\n\n"
        "MISSION 1 : LE DASHBOARD (Format Markdown)\n"
        "- Synthétise les discussions récentes de façon fluide et structurée.\n"
        "- Utilise des listes à puces et du gras pour l'essentiel.\n"
        "- Ne mentionne pas de balises techniques.\n\n"
        "MISSION 2 : EXTRACTION DE CONCEPTS (Format Strict)\n"
        "- Identifie les concepts CLÉS définis ou explorés (pas de verbiage).\n"
        "- Pour chaque concept, remplis le bloc ci-dessous.\n"
        "- IMPORTANT : Si tu utilises un terme technique qui mériterait sa propre note, mets-le entre crochets comme ceci : [[Terme Connexe]].\n" # <--- AJOUT ICI
        "- Si aucun nouveau concept, n'écris rien dans cette section.\n\n"
        "FORMAT DE SORTIE OBLIGATOIRE :\n"
        "[... Ton résumé Dashboard ici ...]\n\n"
        "---EXTRACTION_START---\n"
        "TITRE: Nom du concept 1\n"
        "TAGS: [Tag1, Tag2]\n"
        "CONTENU: Définition atomique et intemporelle (sans 'je' ni 'aujourd'hui').\n"
        "###\n"
        "TITRE: Nom du concept 2\n"
        "TAGS: [TagA]\n"
        "CONTENU: ...\n"
        "---EXTRACTION_END---"
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