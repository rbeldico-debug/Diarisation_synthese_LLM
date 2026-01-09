import multiprocessing
import time
import sys
import uvicorn
from core.settings import settings
from core.orchestrator import BrainOrchestrator
from ears.microphone import MicrophoneStream
from ears.vad_engine import VADSegmenter
from output.speaker import mouth_worker


# --- P1 : OREILLE (Avec PTT) ---
def ear_process(audio_queue, control_queue, stop_event):
    print("[Oreille] Initialisation...")
    try:
        # Par défaut, le micro est coupé (PTT oblige)
        is_recording = False

        vad = VADSegmenter(
            sample_rate=settings.SAMPLE_RATE,
            threshold=settings.VAD_THRESHOLD,
            min_silence_duration_ms=settings.VAD_MIN_SILENCE_DURATION_MS
        )

        with MicrophoneStream(rate=settings.SAMPLE_RATE, block_size=settings.BLOCK_SIZE) as mic:
            print("[Oreille] 🔇 Micro en veille (Attente PTT).")

            for chunk in mic.generator():
                if stop_event.is_set(): break

                # 1. Vérification des ordres (PTT Start/Stop)
                while not control_queue.empty():
                    msg_type, content = control_queue.get()
                    if msg_type == "ptt":
                        if content == "start":
                            is_recording = True
                            print("\n[Oreille] 🎙️ ON AIR", flush=True)
                        elif content == "stop":
                            is_recording = False
                            print("\n[Oreille] 🔇 MUTED", flush=True)

                # 2. Traitement Audio (Seulement si ON AIR)
                if is_recording:
                    payload = vad.process_chunk(chunk)
                    if payload:
                        audio_queue.put(payload)
                        print("⚡", end="", flush=True)

    except Exception as e:
        print(f"[Oreille] ❌ Erreur : {e}")


# --- P2 : CERVEAU ---
def brain_process_wrapper(audio_queue, tts_queue, input_queue, stop_event):
    try:
        # On passe input_queue à l'orchestrateur
        orchestrator = BrainOrchestrator(audio_queue, tts_queue, input_queue, stop_event)
        orchestrator.run()
    except Exception as e:
        print(f"[Cerveau] ❌ CRASH FATAL : {e}")


# --- P5 : SERVEUR WEB ---
def server_process_wrapper(input_queue, control_queue, stop_event):
    from server import app

    # INJECTION DES QUEUES DANS L'APP FASTAPI
    app.state.input_queue = input_queue
    app.state.control_queue = control_queue

    config = uvicorn.Config(app, host="0.0.0.0", port=8002, log_level="warning")
    server = uvicorn.Server(config)
    print(f"[Web] 🌍 Dashboard prêt : http://localhost:8002")
    server.run()


# --- MAIN ---
if __name__ == "__main__":
    multiprocessing.freeze_support()

    settings.LOGS_DIR.mkdir(exist_ok=True)
    stop_signal_file = settings.LOGS_DIR / "oceane.stop"
    if stop_signal_file.exists(): stop_signal_file.unlink()

    print(f"--- 🌊 OCÉANE v3.3 (Web Control) ---")

    # Queues
    audio_q = multiprocessing.Queue()  # Oreille -> Cerveau
    tts_q = multiprocessing.Queue()  # Cerveau -> Bouche
    input_q = multiprocessing.Queue()  # Web (Texte) -> Cerveau
    control_q = multiprocessing.Queue()  # Web (PTT) -> Oreille

    stop_ev = multiprocessing.Event()

    # Processus
    processes = [
        multiprocessing.Process(target=ear_process, args=(audio_q, control_q, stop_ev), name="Oreille"),
        multiprocessing.Process(target=brain_process_wrapper, args=(audio_q, tts_q, input_q, stop_ev), name="Cerveau"),
        multiprocessing.Process(target=mouth_worker, args=(tts_q, stop_ev), name="Bouche"),
        multiprocessing.Process(target=server_process_wrapper, args=(input_q, control_q, stop_ev), name="Web")
    ]

    for p in processes: p.start()

    try:
        while not stop_ev.is_set():
            if stop_signal_file.exists():
                stop_ev.set()
                break
            time.sleep(1)
            if not processes[1].is_alive():  # Cerveau
                print("⚠️ LE CERVEAU EST MORT ! Arrêt.")
                stop_ev.set()
    except KeyboardInterrupt:
        stop_ev.set()
    finally:
        for p in processes:
            if p.is_alive(): p.terminate()
            p.join()
        print("Système éteint.")