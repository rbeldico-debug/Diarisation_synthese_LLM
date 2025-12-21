import io
import wave
import numpy as np
from pathlib import Path
from openai import OpenAI
from config import Config


class InferenceClient:
    """Client pour la transcription et diarisation via Speaches (Docker)."""

    def __init__(self):
        self.client = OpenAI(base_url=Config.WHISPER_BASE_URL, api_key="not-needed")

    def warm_up(self, test_file_path: str = "test_segments/warmup.wav"):
        """Préchauffe le moteur STT pour éliminer la latence de première requête."""
        print("[STT] 🔥 Préchauffage du moteur Whisper...")

        test_path = Path(test_file_path)

        if test_path.exists():
            # Cas 1 : Utilisation de ton fichier audio réel
            try:
                with open(test_path, "rb") as f:
                    audio_bytes = f.read()
                # On envoie directement le binaire à l'API
                self.client.audio.transcriptions.create(
                    model=Config.WHISPER_MODEL,
                    file=(test_path.name, audio_bytes),
                    response_format="verbose_json"
                )
                print(f"[STT] ✅ Préchauffage réussi avec {test_file_path}")
                return
            except Exception as e:
                print(f"[STT] ⚠️ Échec warm-up avec fichier : {e}")

        # Cas 2 : Repli (Fallback) sur un buffer de silence si le fichier n'est pas là
        try:
            silence = np.zeros(Config.SAMPLE_RATE, dtype=np.float32)
            self.process_audio(silence, Config.SAMPLE_RATE)
            print("[STT] ✅ Préchauffage réussi (Silence généré).")
        except Exception as e:
            print(f"[STT] ❌ Échec critique du préchauffage : {e}")

    def process_audio(self, audio_data: np.ndarray, sample_rate: int):
        """Effectue une requête pour obtenir texte + locuteurs."""
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            # Conversion float32 -> int16
            wf.writeframes((audio_data * 32767).astype('int16').tobytes())
        buffer.seek(0)

        try:
            response = self.client.audio.transcriptions.create(
                model=Config.WHISPER_MODEL,
                file=("audio.wav", buffer),
                response_format="verbose_json"
            )

            text = response.text
            # Extraction sécurisée des speakers (ADR-004)
            speakers = []
            if hasattr(response, 'segments'):
                for seg in response.segments:
                    s_id = getattr(seg, 'speaker', None)
                    if s_id: speakers.append(s_id)

            unique_speakers = sorted(list(set(speakers))) if speakers else [Config.DEFAULT_SPEAKER]
            return text, unique_speakers

        except Exception as e:
            print(f"[Inference] ❌ Erreur API : {e}")
            return "", [Config.DEFAULT_SPEAKER]