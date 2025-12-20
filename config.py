import os
import torch
from dotenv import load_dotenv

# Charge les variables d'environnement (.env)
load_dotenv()


class Config:
    # --- AUDIO & VAD ---
    SAMPLE_RATE = 16000
    BLOCK_SIZE = 512

    # Seuil de probabilité pour considérer que c'est de la parole (0.0 à 1.0)
    # Augmenter si le micro capte trop de bruit de fond.
    VAD_THRESHOLD = 0.5

    # Durée de silence (en ms) avant de considérer la phrase finie.
    # C'est ici que tu gères la "latence".
    # 500ms = rapide / 1000ms = plus naturel pour des pauses de réflexion.
    VAD_MIN_SILENCE_DURATION_MS = 1000

    # --- MODEL PATHS & DEVICE ---
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

    # Modèle Whisper (tiny, base, small, medium, large-v3)
    WHISPER_MODEL_SIZE = "large-v3"
    WHISPER_COMPUTE_TYPE = "float16"  # ou "int8" si manque de VRAM

    # Modèle Pyannote
    PYANNOTE_MODEL = "pyannote/speaker-diarization-3.1"
    HF_TOKEN = os.getenv("HF_TOKEN")

    # --- LOGIC ---
    # Durée minimale d'un segment pour tenter une diarisation (en secondes)
    MIN_DURATION_FOR_DIARIZATION = 1.5

    # --- FORMATTING ---
    # Mappe les IDs de Pyannote vers des noms réels
    # Si inconnu, on peut utiliser une heuristique ou laisser tel quel
    SPEAKER_MAPPING = {
        "SPEAKER_00": "Utilisateur",
        "SPEAKER_01": "Assistant",
        # Tu pourras ajuster ça après avoir vu qui est qui dans les logs
    }

    # Nom par défaut si la diarisation échoue ([?])
    DEFAULT_SPEAKER = "Utilisateur"

    # Nombre de tours de parole à garder en mémoire pour le contexte LLM
    MAX_HISTORY_TURNS = 10

    # --- LLM (Ollama) ---
    LLM_BASE_URL = "http://localhost:11434/v1"
    LLM_API_KEY = "ollama"
    LLM_MODEL_NAME = "gpt-oss:20b"

    # Prompt Système Optimisé pour le Temps Réel (Mode "Low Effort")
    # On lui demande explicitement d'être direct pour simuler le "low reasoning".
    SYSTEM_PROMPT = (
        "Tu es une IA assistante vocale. "
        "Réponds de manière directe, concise et naturelle. "
        "Ne génère pas de longues réflexions internes inutiles. "
        "Évite les listes à puces. Fais des phrases courtes."
    )