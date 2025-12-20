# brain/diarization.py
from openai import OpenAI
import io
import wave
import numpy as np
from config import Config


class Diarizer:
    def __init__(self):
        # Connexion au serveur Speaches (Docker)
        self.client = OpenAI(base_url=Config.WHISPER_BASE_URL, api_key="not-needed")

    def diarize(self, audio_data: np.ndarray, sample_rate: int):
        """Identifie les locuteurs en utilisant les attributs d'objet."""
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes((audio_data * 32767).astype('int16').tobytes())
        buffer.seek(0)

        try:
            response = self.client.audio.transcriptions.create(
                model=Config.WHISPER_MODEL,
                file=("audio.wav", buffer),
                response_format="verbose_json"
            )

            speakers = []
            if hasattr(response, 'segments') and response.segments:
                for seg in response.segments:
                    # On accède à l'attribut .speaker directement
                    s_id = getattr(seg, 'speaker', None)
                    if s_id:
                        speakers.append(s_id)

                return sorted(list(set(speakers))) if speakers else [Config.DEFAULT_SPEAKER]
            return [Config.DEFAULT_SPEAKER]
        except Exception as e:
            print(f"[Cerveau] ⚠️ Erreur Diarisation : {e}")
            return [Config.DEFAULT_SPEAKER]