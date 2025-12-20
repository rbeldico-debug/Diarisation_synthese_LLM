from dataclasses import dataclass
import numpy as np
from datetime import datetime

@dataclass
class AudioPayload:
    """
    Représente un segment audio complet (une phrase ou un bout de phrase)
    prêt à être traité par le moteur de transcription.
    """
    audio_data: np.ndarray  # Les données brutes (float32)
    sample_rate: int        # Ex: 16000 Hz
    timestamp: datetime     # Heure de début de la capture
    duration_seconds: float # Durée du segment

    def validate(self):
        """Vérifie sommairement la validité des données."""
        if self.audio_data is None or len(self.audio_data) == 0:
            raise ValueError("AudioPayload vide.")