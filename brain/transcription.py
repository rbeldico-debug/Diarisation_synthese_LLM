import numpy as np
from faster_whisper import WhisperModel


class Transcriber:
    """
    Wrapper pour Faster-Whisper.
    """

    def __init__(self, model_size="large-v3", device="cuda", compute_type="float16"):
        print(f"Chargement de Whisper ({model_size}) sur {device}...")
        try:
            self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
            print("Whisper chargé.")
        except Exception as e:
            print(f"Erreur chargement Whisper: {e}")
            print("Tentative de fallback sur CPU (lent)...")
            self.model = WhisperModel(model_size, device="cpu", compute_type="int8")

    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        """
        Retourne le texte transcrit à partir d'un segment audio brut.
        """
        # Faster-Whisper accepte directement le numpy array
        segments, info = self.model.transcribe(audio_data, beam_size=5, language="fr")

        # On rassemble tous les segments en une seule chaîne
        full_text = " ".join([segment.text for segment in segments])
        return full_text.strip()