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
    VAD_MIN_SILENCE_DURATION_MS = 1000

    # --- SERVEUR IA (Docker Speaches) ---
    # L'URL pointe vers le conteneur Docker sur le port 8000
    WHISPER_BASE_URL = "http://localhost:8000/v1"
    WHISPER_MODEL = "Systran/faster-whisper-large-v3"

    # --- LLM (Ollama) ---
    LLM_BASE_URL = "http://localhost:11434/v1"
    LLM_MODEL_NAME = "gpt-oss:20b"  # Ou deepseek-r1 / llama3

    # --- LOGIQUE MÉTIER ---
    MIN_DURATION_FOR_DIARIZATION = 1.5
    MAX_HISTORY_TURNS = 10
    SPEAKER_MAPPING = {
        "SPEAKER_00": "Utilisateur",
        "SPEAKER_01": "Assistant",
    }
    DEFAULT_SPEAKER = "Utilisateur"

    SYSTEM_PROMPT = (
        "Tu es une IA assistante vocale nommée Gérald. "
        "Réponds de manière directe et concise. Pas de listes à puces. "
        "Fais des phrases courtes et naturelles pour une synthèse vocale."
    )