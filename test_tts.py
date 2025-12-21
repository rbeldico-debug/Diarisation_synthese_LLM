import os
import time
import pygame.mixer
import pathlib
import piper_phonemize
from piper.voice import PiperVoice

# 1. Configuration du chemin des phonèmes (Indispensable pour Piper)
package_dir = pathlib.Path(piper_phonemize.__file__).parent
os.environ["ESPEAK_DATA_PATH"] = str(package_dir / "espeak-ng-data")


def test():
    # Chemins relatifs à la racine du projet
    model_path = "models/fr_FR-gilles-low.onnx"
    config_path = model_path + ".json"

    if not os.path.exists(model_path):
        print(f"❌ Erreur : Le fichier {model_path} est introuvable.")
        return

    print("Chargement de la voix...")
    voice = PiperVoice.load(model_path, config_path)

    print("Initialisation Audio...")
    if pygame.mixer.get_init(): pygame.mixer.quit()
    # Gilles-low est en 22050Hz, 16-bit, Mono (channels=1)
    pygame.mixer.init(frequency=22050, size=-16, channels=1)

    text = "Bonjour, je suis enfin capable de parler sur Windows !"
    print(f"Synthèse de : '{text}'")

    # --- CORRECTION ICI : synthesize_stream_raw ---
    full_audio = b""
    for audio_bytes in voice.synthesize_stream_raw(text):
        full_audio += audio_bytes

    if full_audio:
        print(f"Audio généré ({len(full_audio)} octets). Lecture...")
        sound = pygame.mixer.Sound(buffer=full_audio)
        sound.play()
        while pygame.mixer.get_busy():
            time.sleep(0.1)
        print("✅ Succès ! Vous devriez avoir entendu la voix.")
    else:
        print("❌ Erreur : Aucun audio généré.")


if __name__ == "__main__":
    test()