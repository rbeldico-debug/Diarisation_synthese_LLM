from datetime import datetime
import numpy as np
from pydantic import BaseModel, ConfigDict, Field

class AudioPayload(BaseModel):
    """
    Représente un segment audio complet.
    Utilise Pydantic pour la validation, avec autorisation des types Numpy.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    audio_data: np.ndarray = Field(..., description="Données audio brutes float32")
    sample_rate: int = Field(..., gt=0)
    timestamp: datetime
    duration_seconds: float = Field(..., gt=0)

    def validate_payload(self):
        """Vérification manuelle supplémentaire si nécessaire."""
        if self.audio_data is None or self.audio_data.size == 0:
            raise ValueError("AudioPayload vide.")

class LogEntry(BaseModel):
    """
    Structure standardisée pour les logs (Journal).
    """
    timestamp: str
    source: str
    text: str
    intent_tag: str
    meta: dict = {}
    ignored: bool = False