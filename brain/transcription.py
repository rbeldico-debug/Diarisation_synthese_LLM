# brain/transcription.py
from openai import OpenAI
import io
import wave
import numpy as np
from config import Config

class Transcriber:
    def __init__(self):
        # Utilisation du client compatible OpenAI pour parler à Speaches
        self.client = OpenAI(base_url=Config.WHISPER_BASE_URL, api_key="not-needed")

    def transcribe(self, audio_data: np.ndarray, sample_rate: int) -> str:
        """Envoie l'audio au serveur Docker et récupère le texte."""
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2) # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes((audio_data * 32767).astype('int16').tobytes())
        buffer.seek(0)

        try:
            response = self.client.audio.transcriptions.create(
                model=Config.WHISPER_MODEL,
                file=("audio.wav", buffer)
            )
            return response.text
        except Exception as e:
            return f"[Erreur Transcription: {e}]"