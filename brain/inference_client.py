# Nouveau fichier : brain/inference_client.py
from openai import OpenAI
import io
import wave
import numpy as np
from config import Config


class InferenceClient:
    """
    Client unique pour la transcription et la diarisation (ADR-004).
    Centralise les appels vers le serveur Speaches (Docker).
    """

    def __init__(self):
        self.client = OpenAI(base_url=Config.WHISPER_BASE_URL, api_key="not-needed")

    def process_audio(self, audio_data: np.ndarray, sample_rate: int):
        """
        Effectue une seule requête pour obtenir texte + locuteurs.
        """
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            # Conversion float32 -> int16 pour le format WAV
            wf.writeframes((audio_data * 32767).astype('int16').tobytes())
        buffer.seek(0)

        try:
            # Appel unique avec response_format="verbose_json"
            response = self.client.audio.transcriptions.create(
                model=Config.WHISPER_MODEL,
                file=("audio.wav", buffer),
                response_format="verbose_json"
            )

            text = response.text
            speakers = self._extract_speakers(response)

            return text, speakers

        except Exception as e:
            print(f"[Inference] ❌ Erreur API : {e}")
            return "", [Config.DEFAULT_SPEAKER]

    def _extract_speakers(self, response) -> list:
        """Extrait la liste unique des locuteurs depuis le JSON verbose."""
        speakers = []
        if hasattr(response, 'segments'):
            for seg in response.segments:
                s_id = getattr(seg, 'speaker', None)
                if s_id:
                    speakers.append(s_id)

        # Retourne une liste unique triée, ou le speaker par défaut
        return sorted(list(set(speakers))) if speakers else [Config.DEFAULT_SPEAKER]