import os
import pathlib
import time
import unicodedata
import re
import numpy as np
import pygame.mixer
import piper
import piper_phonemize
from piper.voice import PiperVoice

# Config phonèmes
package_dir = pathlib.Path(piper_phonemize.__file__).parent
os.environ["ESPEAK_DATA_PATH"] = str(package_dir / "espeak-ng-data")


class VoiceOut:
    def __init__(self, model_name="fr_FR-gilles-low.onnx"):
        base_dir = pathlib.Path(__file__).parent.parent
        model_path = base_dir / "models" / model_name

        self.voice = PiperVoice.load(str(model_path.resolve()), str(model_path) + ".json")

        # --- RÉGLAGE FRÉQUENCE RÉELLE (Gilles-Low = 16000) ---
        self.sample_rate = 16000

        # --- RÉGLAGE DE LA DOUCEUR / VITESSE ---
        self.vitesse = 1.15  # 1.0 = normal, 1.2 = plus lent et posé

        if pygame.mixer.get_init():
            pygame.mixer.quit()

        # Initialisation en Stéréo 16kHz
        pygame.mixer.pre_init(frequency=self.sample_rate, size=-16, channels=2, buffer=512)
        pygame.mixer.init()

    def _clean_text(self, text: str) -> str:
        """Nettoyage radical pour supprimer les phonèmes manquants et tildes."""
        if not text: return ""
        # 1. Normalisation Unicode
        text = unicodedata.normalize('NFD', text)
        # 2. Suppression de tous les caractères de combinaison (Accents flottants, tildes)
        # On ne garde que les caractères de base (lettres, chiffres, ponctuation)
        text = re.sub(r'[\u0300-\u036f]', '', text)
        # 3. Recomposition propre
        text = unicodedata.normalize('NFC', text)
        return text.strip()

    def speak(self, text):
        if not text: return
        t_start = time.perf_counter()
        clean_text = self._clean_text(text)

        try:
            # On passe 'length_scale' pour ralentir la voix directement dans le moteur
            audio_bytes = b"".join(self.voice.synthesize_stream_raw(
                clean_text,
                length_scale=self.vitesse
            ))

            if audio_bytes:
                audio_np = np.frombuffer(audio_bytes, dtype=np.int16)

                # Mono -> Stéréo
                stereo_audio = np.stack((audio_np, audio_np), axis=-1)

                duration_s = len(audio_np) / self.sample_rate
                t_prep = time.perf_counter() - t_start
                print(f"[Bouche] 🔊 Audio: {duration_s:.2f}s | Prep: {t_prep:.3f}s | Vitesse: {self.vitesse}")

                sound = pygame.sndarray.make_sound(stereo_audio)
                channel = sound.play()
                while channel.get_busy():
                    time.sleep(0.01)

        except Exception as e:
            print(f"[Bouche] ❌ Erreur audio : {e}")


def mouth_worker(tts_queue, stop_event):
    os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
    try:
        speaker = VoiceOut()
        print("[Bouche] ✅ Prête.")
    except Exception as e:
        print(f"[Bouche] ❌ Échec: {e}")
        return

    while not stop_event.is_set():
        try:
            text = tts_queue.get(timeout=0.5)
            if text: speaker.speak(text)
        except:
            continue