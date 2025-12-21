# config.py
import os
import torch
from dotenv import load_dotenv

load_dotenv()


class Config:
    # --- AUDIO & VAD (Local) ---
    SAMPLE_RATE = 16000
    BLOCK_SIZE = 512
    VAD_THRESHOLD = 0.5
    # ADR-005 : Réduction à 500ms pour plus de réactivité
    VAD_MIN_SILENCE_DURATION_MS = 500
    TTS_SAMPLE_RATE = 16000  # Piper standard

    # --- SERVEUR IA (Docker Speaches) ---
    WHISPER_BASE_URL = "http://localhost:8000/v1"
    WHISPER_MODEL = "Systran/faster-whisper-large-v3"

    # --- LLM (Ollama) ---
    LLM_BASE_URL = "http://localhost:11434/v1"
    LLM_MODEL_NAME = "gpt-oss:20b"

    # --- LOGIQUE MÉTIER ---
    # ADR-004 : On garde ce seuil pour décider si on affiche le locuteur
    MIN_DURATION_FOR_DIARIZATION = 1.0
    MAX_HISTORY_TURNS = 10
    SPEAKER_MAPPING = {
        "SPEAKER_00": "Utilisateur",
        "SPEAKER_01": "Assistant",
    }
    DEFAULT_SPEAKER = "Utilisateur"

    SYSTEM_PROMPT = (
        "Tu es Gérald, un assistant vocal intelligent et réactif. "
        "Tu t'adresses à l'utilisateur directement par la voix. "
        "Fais des réponses très courtes (2 phrases maximum), pas de listes, "
        "sois naturel comme dans une vraie conversation."
    )