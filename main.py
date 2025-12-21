# main.py
import multiprocessing
import queue
import time
import numpy as np

# Patch NumPy pour compatibilité (nécessaire pour certains environnements Windows/Pyannote)
if not hasattr(np, "NaN"):
    np.NaN = np.nan

from ears.microphone import MicrophoneStream
from ears.vad_engine import VADSegmenter
from config import Config
from output.speaker import mouth_worker  # Import du nouveau worker P3


def ear_process(audio_queue: multiprocessing.Queue, stop_event: multiprocessing.Event):
    """
    Processus P1 (Producteur) : Écoute le micro et envoie les segments validés.
    """
    print(f"[Oreille] Initialisation VAD (Silence min: {Config.VAD_MIN_SILENCE_DURATION_MS}ms)...")

    vad = VADSegmenter(
        sample_rate=Config.SAMPLE_RATE,
        threshold=Config.VAD_THRESHOLD,
        min_silence_duration_ms=Config.VAD_MIN_SILENCE_DURATION_MS
    )

    print("[Oreille] Prête. Parlez !")

    try:
        with MicrophoneStream(rate=Config.SAMPLE_RATE, block_size=Config.BLOCK_SIZE) as mic:
            for chunk in mic.generator():
                if stop_event.is_set():
                    break

                payload = vad.process_chunk(chunk)
                if payload:
                    print(f"[Oreille] 🎤 Phrase détectée ({payload.duration_seconds:.2f}s) -> Envoi au Cerveau.")
                    audio_queue.put(payload)

    except Exception as e:
        print(f"[Oreille] ❌ Erreur : {e}")
    finally:
        print("[Oreille] Arrêt.")


def brain_process(audio_queue: multiprocessing.Queue, tts_queue: multiprocessing.Queue,
                  stop_event: multiprocessing.Event):
    from brain.inference_client import InferenceClient
    from brain.llm_client import LLMClient
    from output.formatter import DialogueFormatter

    inference = InferenceClient()
    llm = LLMClient()
    formatter = DialogueFormatter()

    print("[Cerveau] 🧠 Prêt à traiter les segments.")

    while not stop_event.is_set():
        try:
            payload = audio_queue.get(timeout=1.0)
        except queue.Empty:
            continue

        # --- DÉBUT DU CHRONO ICI ---
        t0 = time.perf_counter()

        # 1. Transcription
        text, speakers = inference.process_audio(payload.audio_data, payload.sample_rate)
        t_transcription = time.perf_counter() - t0

        if not text.strip() or len(text.strip()) <= 2:
            continue

        # 2. Réflexion & Réponse LLM (UN SEUL APPEL)
        context = formatter.get_context_string()
        print(f"🤖 Assistant réfléchit (Transcription en {t_transcription:.2f}s)...", end="\r")

        t_llm_start = time.perf_counter()
        response = llm.query(context, text)
        t_llm = time.perf_counter() - t_llm_start

        # Latence totale avant le début de la parole
        total_latency = time.perf_counter() - t0
        print(f"\n[Stats] Transcription: {t_transcription:.2f}s | LLM: {t_llm:.2f}s | Total: {total_latency:.2f}s")

        # 3. Envoi à la bouche
        tts_queue.put(response)

        # Mise à jour historique
        display_line = formatter.process_turn(text, speakers)
        formatter.process_turn(response, ["SPEAKER_01"])
        print(f"🤖 Assistant: {response}")


if __name__ == "__main__":
    # Protection obligatoire pour Windows
    multiprocessing.freeze_support()

    print("--- DÉMARRAGE DU SYSTÈME GÉRALD V2 (Full-Duplex) ---")
    print("Ctrl+C pour arrêter.")

    # 1. Création des canaux de communication
    main_queue = multiprocessing.Queue()  # Flux : Oreille -> Cerveau
    tts_queue = multiprocessing.Queue()  # Flux : Cerveau -> Bouche
    stop_signal = multiprocessing.Event()  # Signal d'arrêt global

    # 2. Définition des processus (P1, P2, P3)
    p_ear = multiprocessing.Process(
        target=ear_process,
        args=(main_queue, stop_signal),
        name="Oreille"
    )
    p_brain = multiprocessing.Process(
        target=brain_process,
        args=(main_queue, tts_queue, stop_signal),
        name="Cerveau"
    )
    p_mouth = multiprocessing.Process(
        target=mouth_worker,
        args=(tts_queue, stop_signal),
        name="Bouche"
    )

    # 3. Lancement des processus
    # On lance la bouche et le cerveau en premier car ils ont des temps de chargement
    p_mouth.start()
    p_brain.start()
    p_ear.start()

    try:
        while True:
            time.sleep(1)
            # Surveillance de l'état des processus
            if not p_ear.is_alive() or not p_brain.is_alive() or not p_mouth.is_alive():
                print("⚠️ Un processus s'est arrêté inopinément.")
                break
    except KeyboardInterrupt:
        print("\n🛑 Arrêt demandé par l'utilisateur...")
    finally:
        # Arrêt propre et synchronisé
        stop_signal.set()

        # On vide les queues pour débloquer les processus en attente si nécessaire
        while not main_queue.empty(): main_queue.get()
        while not tts_queue.empty(): tts_queue.get()

        p_ear.join(timeout=2)
        p_brain.join(timeout=2)
        p_mouth.join(timeout=2)

        print("--- SYSTÈME ÉTEINT ---")