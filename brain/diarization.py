import os
import torch
import numpy as np
from pyannote.audio import Pipeline
from pyannote.core import Annotation
from dotenv import load_dotenv

load_dotenv()


class Diarizer:
    def __init__(self):
        self.auth_token = os.getenv("HF_TOKEN")
        if not self.auth_token:
            raise ValueError("❌ HF_TOKEN manquant dans le fichier .env")

        print("Chargement de Pyannote Pipeline...")
        try:
            # On utilise le modèle 3.1 qui est le standard actuel
            self.pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                token=self.auth_token
            )

            if self.pipeline is None:
                raise ValueError("Erreur téléchargement pipeline. Vérifiez votre token HF.")

            if torch.cuda.is_available():
                self.pipeline.to(torch.device("cuda"))
                print(f"✅ Pyannote chargé sur GPU ({torch.cuda.get_device_name(0)}).")
            else:
                print("⚠️ Pyannote chargé sur CPU.")

        except Exception as e:
            print(f"❌ Erreur chargement Pyannote : {e}")
            raise e

    def diarize(self, audio_data: np.ndarray, sample_rate: int = 16000):
        # 1. Garde-fou : Si l'audio est trop court (< 1.5s), la diarisation va échouer
        duration = len(audio_data) / sample_rate
        if duration < 1.5:
            print(f"⚠️ Segment trop court pour diarisation ({duration:.2f}s < 1.5s). Ignoré.")
            return []

        # 2. Préparation des données
        torch_data = torch.from_numpy(audio_data).float()
        if len(torch_data.shape) == 1:
            torch_data = torch_data.unsqueeze(0)

        inputs = {"waveform": torch_data, "sample_rate": sample_rate}

        try:
            # 3. Exécution
            output = self.pipeline(inputs)

            # 4. Gestion robuste du format de sortie
            # Parfois Pyannote peut renvoyer un objet wrapper au lieu de l'Annotation directe
            if not isinstance(output, Annotation):
                if hasattr(output, "annotation"):
                    output = output.annotation
                else:
                    # Cas de débogage si le format est inconnu
                    # print(f"DEBUG: Type de sortie inattendu: {type(output)}")
                    return []

            results = []
            for turn, _, speaker in output.itertracks(yield_label=True):
                results.append({
                    "start": turn.start,
                    "end": turn.end,
                    "speaker": speaker
                })
            return results

        except Exception as e:
            # On ne veut pas crasher tout le programme si la diarisation échoue
            print(f"❌ Erreur lors du process diarization : {e}")
            return []