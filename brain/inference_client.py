import io
import wave
import numpy as np
from pathlib import Path
from openai import OpenAI
from core.settings import settings


class InferenceClient:
    def __init__(self):
        self.client = OpenAI(base_url=settings.WHISPER_BASE_URL, api_key="not-needed")

    def warm_up(self, test_file_path: str = "test_segments/warmup.wav"):
        print("[STT] 🔥 Préchauffage du moteur Whisper...")

        test_path = Path(test_file_path)

        if test_path.exists():
            # Cas 1 : Utilisation de ton fichier audio réel
            try:
                silence = np.zeros(settings.SAMPLE_RATE, dtype=np.float32)
                self.process_audio(silence, settings.SAMPLE_RATE)
                print("[STT] ✅ Préchauffage réussi (Silence généré).")
            except Exception as e:
                print(f"[STT] ❌ Échec critique du préchauffage : {e}")
                return

        # Cas 2 : Repli (Fallback) sur un buffer de silence si le fichier n'est pas là
        try:
            silence = np.zeros(settings.SAMPLE_RATE, dtype=np.float32)
            self.process_audio(silence, settings.SAMPLE_RATE)
            print("[STT] ✅ Préchauffage réussi (Silence généré).")
        except Exception as e:
            print(f"[STT] ❌ Échec critique du préchauffage : {e}")

    def process_audio(self, audio_data: np.ndarray, sample_rate: int):
        """Effectue une requête pour obtenir texte + locuteurs en forçant le Français."""
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes((audio_data * 32767).astype('int16').tobytes())
        buffer.seek(0)

        try:
            response = self.client.audio.transcriptions.create(
                model=settings.WHISPER_MODEL,
                file=("audio.wav", buffer),
                response_format="verbose_json",
                language="fr"
            )

            text = response.text
            speakers = []
            if hasattr(response, 'segments'):
                for seg in response.segments:
                    s_id = getattr(seg, 'speaker', None)
                    if s_id: speakers.append(s_id)

            unique_speakers = sorted(list(set(speakers))) if speakers else ["Utilisateur"]
            return text, unique_speakers

        except Exception as e:
            print(f"[Inference] ❌ Erreur API : {e}")
            return "", ["Utilisateur"]