import torch
import numpy as np
from datetime import datetime
from typing import Optional, List

from core.data_models import AudioPayload


class VADSegmenter:
    """
    Gère la détection d'activité vocale (VAD) et l'assemblage des segments audio.
    Utilise Silero VAD pour analyser les chunks entrants.
    """

    def __init__(self, sample_rate: int = 16000, threshold: float = 0.5, min_silence_duration_ms: int = 500):
        self.sample_rate = sample_rate
        self.threshold = threshold
        self.min_silence_duration_ms = min_silence_duration_ms

        # Chargement du modèle Silero
        print("Chargement de Silero VAD...")
        # Ajout de trust_repo=True pour éviter le warning de sécurité (ADR-001 validé)
        try:
            self.model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                               model='silero_vad',
                                               force_reload=False,
                                               trust_repo=True,
                                               onnx=False)
        except Exception as e:
            print(f"Erreur critique lors du chargement de Silero: {e}")
            raise e

        self.get_speech_timestamps, _, self.read_audio, _, _ = utils
        self.model.eval()  # Mode évaluation
        print("Silero VAD chargé.")

        # État interne
        self.buffer: List[np.ndarray] = []
        self.is_speaking = False
        self.silence_counter = 0
        self.segment_start_time = None

    def process_chunk(self, chunk: np.ndarray) -> Optional[AudioPayload]:
        """
        Traite un petit morceau d'audio (chunk).
        Retourne un AudioPayload si une phrase est terminée, sinon None.
        """
        # 1. Conversion pour Silero (attend du float32)
        if chunk.dtype != np.float32:
            chunk = chunk.astype(np.float32)

        # Silero attend un tensor
        chunk_tensor = torch.from_numpy(chunk)

        # 2. Prédiction (Probabilité que ce soit de la parole)
        # Note : On met .item() pour récupérer la valeur float du tensor
        speech_prob = self.model(chunk_tensor, self.sample_rate).item()

        current_is_speech = speech_prob > self.threshold

        # 3. Logique de segmentation (Machine à états simplifiée)

        if current_is_speech:
            # --- Ça parle ---
            if not self.is_speaking:
                self.is_speaking = True
                self.segment_start_time = datetime.now()

            self.silence_counter = 0
            self.buffer.append(chunk)

        else:
            # --- Silence ---
            if self.is_speaking:
                self.buffer.append(chunk)
                self.silence_counter += 1

                # Calcul de la durée du silence accumulé
                chunk_duration_ms = (len(chunk) / self.sample_rate) * 1000
                current_silence_duration = self.silence_counter * chunk_duration_ms

                if current_silence_duration > self.min_silence_duration_ms:
                    return self._finalize_segment()

            else:
                pass

        return None

    def _finalize_segment(self) -> AudioPayload:
        """Crée l'objet final et nettoie le buffer."""
        if not self.buffer:
            return None

        full_audio = np.concatenate(self.buffer)
        duration = len(full_audio) / self.sample_rate

        payload = AudioPayload(
            audio_data=full_audio,
            sample_rate=self.sample_rate,
            timestamp=self.segment_start_time,
            duration_seconds=duration
        )

        # Reset de l'état
        self.buffer = []
        self.is_speaking = False
        self.silence_counter = 0
        self.segment_start_time = None

        return payload