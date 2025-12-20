# main.py (Imports nettoyés)
import multiprocessing
import queue
import time
import numpy as np

# Patch NumPy pour compatibilité ascendante
if not hasattr(np, "NaN"):
    np.NaN = np.nan

from ears.microphone import MicrophoneStream
from ears.vad_engine import VADSegmenter
from config import Config

def ear_process(audio_queue: multiprocessing.Queue, stop_event: multiprocessing.Event):
    """
    Processus P1 (Producteur) : Écoute le micro et envoie les segments validés.
    """
    print(f"[Oreille] Initialisation VAD (Silence min: {Config.VAD_MIN_SILENCE_DURATION_MS}ms)...")

    # Instanciation avec les paramètres de la Config
    vad = VADSegmenter(
        sample_rate=Config.SAMPLE_RATE,
        threshold=Config.VAD_THRESHOLD,
        min_silence_duration_ms=Config.VAD_MIN_SILENCE_DURATION_MS
    )

    print("[Oreille] Prête. Parlez !")

    try:
        # Utilisation de Config.SAMPLE_RATE, etc.
        with MicrophoneStream(rate=Config.SAMPLE_RATE, block_size=Config.BLOCK_SIZE) as mic:
            for chunk in mic.generator():
                if stop_event.is_set():
                    break

                # Traitement VAD
                payload = vad.process_chunk(chunk)

                if payload:
                    print(f"[Oreille] 🎤 Phrase détectée ({payload.duration_seconds:.2f}s) -> Envoi au Cerveau.")
                    audio_queue.put(payload)

    except Exception as e:
        print(f"[Oreille] ❌ Erreur : {e}")
    finally:
        print("[Oreille] Arrêt.")


def brain_process(audio_queue: multiprocessing.Queue, stop_event: multiprocessing.Event):
    """Processus P2 : Consomme les segments audio et coordonne l'IA."""
    from brain.transcription import Transcriber
    from brain.diarization import Diarizer
    from brain.llm_client import LLMClient
    from output.formatter import DialogueFormatter

    # Initialisation des ouvriers
    transcriber = Transcriber()
    diarizer = Diarizer()
    llm = LLMClient()
    formatter = DialogueFormatter()

    print("[Cerveau] 🧠 Prêt à traiter les segments.")

    while not stop_event.is_set():
        try:
            payload = audio_queue.get(timeout=1.0)
        except queue.Empty:
            continue

        # 1. Transcription & Diarisation (via Docker)
        text = transcriber.transcribe(payload.audio_data, payload.sample_rate)

        speakers = ["Utilisateur"]
        if payload.duration_seconds > Config.MIN_DURATION_FOR_DIARIZATION:
            speakers = diarizer.diarize(payload.audio_data, payload.sample_rate)

        # 2. Formatage du tour de parole
        display_line = formatter.process_turn(text, speakers)
        print(f"\n{display_line}")

        # 3. Réflexion & Réponse LLM
        # On ne répond que si le texte n'est pas vide et si c'est l'utilisateur qui parle
        if len(text.strip()) > 2:
            context = formatter.get_context_string()
            print("🤖 Assistant réfléchit...", end="\r")

            response = llm.query(context, text)

            # On ajoute la réponse de l'IA à l'historique
            formatter.process_turn(response, ["Assistant"])
            print(f"🤖 Assistant: {response}")


if __name__ == "__main__":
    # Protection obligatoire pour Windows
    multiprocessing.freeze_support()

    print("--- DÉMARRAGE DU SYSTÈME MULTI-AGENTS ---")
    print("Ctrl+C pour arrêter.")

    # Création des outils de communication inter-processus
    # La Queue sert de tuyau entre l'Oreille et le Cerveau
    main_queue = multiprocessing.Queue()
    stop_signal = multiprocessing.Event()

    # Création des processus
    p_ear = multiprocessing.Process(target=ear_process, args=(main_queue, stop_signal))
    p_brain = multiprocessing.Process(target=brain_process, args=(main_queue, stop_signal))

    # Lancement
    p_brain.start()  # On lance le cerveau d'abord pour qu'il charge
    p_ear.start()

    try:
        while True:
            time.sleep(1)
            # Vérifie si les processus sont toujours vivants
            if not p_ear.is_alive() or not p_brain.is_alive():
                print("⚠️ Un processus s'est arrêté inopinément.")
                break
    except KeyboardInterrupt:
        print("\n🛑 Arrêt demandé par l'utilisateur...")
    finally:
        # Arrêt propre
        stop_signal.set()
        p_ear.join()
        p_brain.join()
        print("--- SYSTÈME ÉTEINT ---")