import asyncio
import edge_tts
import pygame
import io
import multiprocessing
from core.settings import settings


class EdgeVoice:
    def __init__(self):
        self.voice = settings.TTS_VOICE
        if not pygame.mixer.get_init():
            pygame.mixer.init()

    async def _generate_and_play(self, text):
        communicate = edge_tts.Communicate(text, self.voice)
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]

        # Lecture en mémoire (sans fichier temporaire)
        sound_file = io.BytesIO(audio_data)
        pygame.mixer.music.load(sound_file)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.1)

    def speak(self, text):
        if not text: return
        try:
            asyncio.run(self._generate_and_play(text))
        except Exception as e:
            print(f"[Bouche] ❌ Erreur Edge-TTS : {e}")


def mouth_worker(tts_queue, stop_event):
    print(f"[Bouche] ✅ Prête ({settings.TTS_VOICE}).")
    speaker = EdgeVoice()

    while not stop_event.is_set():
        try:
            text = tts_queue.get(timeout=1.0)
            if text:
                print(f"[Bouche] 🎙️ Lecture en cours...")
                speaker.speak(text)
        except:
            continue