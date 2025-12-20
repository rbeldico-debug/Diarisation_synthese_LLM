import os
import sys


# --- CORRECTIF WINDOWS GPU ---
# Ajout des chemins des bibliothèques NVIDIA installées via pip au PATH
# pour que CTranslate2 (Faster-Whisper) puisse les trouver.
def add_nvidia_libs_to_path():
    try:
        import nvidia.cublas.lib
        import nvidia.cudnn.lib

        paths_to_add = [
            os.path.dirname(nvidia.cublas.lib.__file__),
            os.path.dirname(nvidia.cudnn.lib.__file__)
        ]

        for p in paths_to_add:
            if os.path.exists(p):
                os.add_dll_directory(p)  # Pour Python 3.8+
                os.environ["PATH"] = p + os.pathsep + os.environ["PATH"]
                print(f"✅ Libs NVIDIA ajoutées : {p}")
    except ImportError:
        print("⚠️ Attention : Modules nvidia-cudnn-cu12 ou nvidia-cublas-cu12 non trouvés via pip.")
        print("Si tu as une erreur DLL, installe-les : pip install nvidia-cudnn-cu12 nvidia-cublas-cu12")


# Appliquer le correctif avant tout import de torch ou whisper
if os.name == 'nt':
    add_nvidia_libs_to_path()
# -----------------------------

import numpy as np
from scipy.io import wavfile
import torch  # Import torch après le patch

from brain.transcription import Transcriber
from brain.diarization import Diarizer


def load_wav_as_float32(filename):
    """Charge un wav et le normalise en float32 entre -1 et 1"""
    rate, data = wavfile.read(filename)
    if data.dtype == np.int16:
        data = data.astype(np.float32) / 32768.0
    return rate, data


def main():
    # Vérification CUDA
    print(f"Version Torch : {torch.__version__}")
    print(f"CUDA disponible : {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU : {torch.cuda.get_device_name(0)}")
    else:
        print("⚠️ ALERTE : Tu tournes toujours sur CPU !")

    target_file = "test_segments/phrase_001.wav"

    if not os.path.exists(target_file):
        print(f"Erreur: Le fichier {target_file} n'existe pas.")
        return

    print(f"--- TEST STEP 2 : ANALYSE DU FICHIER {target_file} ---")

    # 1. Chargement Audio
    rate, audio_data = load_wav_as_float32(target_file)
    print(f"Audio chargé : {len(audio_data) / rate:.2f} secondes.")

    # 2. Transcription (Whisper)
    # Le try/except capture l'erreur spécifique de DLL
    try:
        transcriber = Transcriber()
        text = transcriber.transcribe(audio_data, sample_rate=rate)
        print(f"\n📝 TRANSCRIPTION :\n{text}")
    except Exception as e:
        print(f"\n❌ ERREUR WHISPER : {e}")
        print("Verifie l'installation de cuDNN.")
        return

    # 3. Diarisation (Pyannote)
    try:
        diarizer = Diarizer()
        segments = diarizer.diarize(audio_data, sample_rate=rate)

        print("\n🗣️ DIARISATION :")
        if not segments:
            print("Aucun locuteur détecté (segment trop court ?)")
        for seg in segments:
            print(f"  - {seg['speaker']} : {seg['start']:.2f}s -> {seg['end']:.2f}s")

    except Exception as e:
        print(f"\n❌ ERREUR PYANNOTE : {e}")


if __name__ == "__main__":
    main()