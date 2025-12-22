import multiprocessing
import threading
import queue
import time
from datetime import datetime
import numpy as np
import os
import sys
from config import Config

# Patch NumPy
if not hasattr(np, "NaN"): np.NaN = np.nan

from ears.microphone import MicrophoneStream
from ears.vad_engine import VADSegmenter
from output.speaker import mouth_worker
from memory.storage_manager import MemoryManager


def analyst_process(stop_event: multiprocessing.Event, tts_queue: multiprocessing.Queue):
    """P4 : Analyste + Oracle Vocal (Avec monitoring console forcé)"""
    from analyst.synthesizer import Synthesizer
    from memory.storage_manager import MemoryManager

    synther = Synthesizer()
    memory = MemoryManager()

    last_vocal_brief = time.time()
    VOCAL_INTERVAL = 300

    print(f"[Analyste] ✅ Prêt. Session : {Config.SESSION_ID}")

    # --- GÉNÉRATION INITIALE ---
    content = synther.generate_summary()
    memory.update_dashboard(content)
    print(f"[Analyste] 🚀 Dashboard initial généré.")
    sys.stdout.flush()

    while not stop_event.is_set():
        for _ in range(Config.ANALYST_UPDATE_INTERVAL_SECONDS):
            if stop_event.is_set(): return
            time.sleep(1)

        # Mise à jour régulière
        content = synther.generate_summary()
        memory.update_dashboard(content)

        # --- LOG CONSOLE (FORCÉ) ---
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[Analyste] 📝 {timestamp} : Mise à jour Dashboard effectuée.")
        sys.stdout.flush()

        # Briefing vocal
        now = time.time()
        if now - last_vocal_brief >= VOCAL_INTERVAL:
            print("[Analyste] 🧠 Génération du briefing vocal...")
            sys.stdout.flush()
            brief = synther.generate_vocal_brief(content)
            if brief:
                tts_queue.put(brief)
                last_vocal_brief = now


def ear_process(audio_queue: multiprocessing.Queue, stop_event: multiprocessing.Event):
    """P1 : Oreille"""
    from brain.inference_client import InferenceClient
    inf = InferenceClient()
    inf.warm_up()
    vad = VADSegmenter(sample_rate=Config.SAMPLE_RATE, threshold=Config.VAD_THRESHOLD,
                       min_silence_duration_ms=Config.VAD_MIN_SILENCE_DURATION_MS)

    try:
        with MicrophoneStream(rate=Config.SAMPLE_RATE, block_size=Config.BLOCK_SIZE) as mic:
            print(f"[Oreille] ✅ Écoute active.")
            sys.stdout.flush()
            for chunk in mic.generator():
                if stop_event.is_set(): break
                payload = vad.process_chunk(chunk)
                if payload:
                    audio_queue.put(payload)
    except Exception as e:
        print(f"[Oreille] ❌ Erreur micro : {e}")


def brain_process(audio_queue: multiprocessing.Queue, stop_event: multiprocessing.Event):
    """P2 : Cerveau"""
    from brain.inference_client import InferenceClient
    from brain.router import IntentRouter
    from memory.storage_manager import MemoryManager
    from memory.vector_manager import VectorManager
    from core.warmup import WarmupManager

    inference = InferenceClient()
    router = IntentRouter()
    memory = MemoryManager()
    vector_db = VectorManager()
    warmup = WarmupManager(inference, router, vector_db, stop_event)

    warmup.perform_all()
    print(f"[Cerveau] 🧠 Système stabilisé.")
    sys.stdout.flush()

    while not stop_event.is_set():
        try:
            payload = audio_queue.get(timeout=1.0)
        except queue.Empty:
            continue

        text, speakers = inference.process_audio(payload.audio_data, payload.sample_rate)
        if not text.strip(): continue

        tags = router.route(text)
        embedding = router.get_embedding(text)
        timestamp = datetime.now().isoformat()

        memory.log_event(source="user", text=text, intent=tags, extra={"speakers": speakers})
        if embedding is not None:
            vector_db.add_to_memory(text=text, embedding=embedding,
                                    metadata={"timestamp": timestamp, "intent": tags, "session": Config.SESSION_ID})

        print(f"📝 {tags} : {text}")
        sys.stdout.flush()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    Config.LOGS_DIR.mkdir(exist_ok=True)

    if Config.STOP_SIGNAL_PATH.exists():
        Config.STOP_SIGNAL_PATH.unlink()

    print(f"\n--- 🌊 SYSTÈME OCÉANE V2.5 | SESSION {Config.SESSION_ID} ---")
    sys.stdout.flush()

    m_q = multiprocessing.Queue()
    t_q = multiprocessing.Queue()
    s_ev = multiprocessing.Event()

    processes = [
        multiprocessing.Process(target=ear_process, args=(m_q, s_ev), name="Oreille"),
        multiprocessing.Process(target=brain_process, args=(m_q, s_ev), name="Cerveau"),
        multiprocessing.Process(target=mouth_worker, args=(t_q, s_ev), name="Bouche"),
        multiprocessing.Process(target=analyst_process, args=(s_ev, t_q), name="Analyste")
    ]

    for p in processes: p.start()

    print("\n" + "=" * 60)
    print("📢 OCÉANE EST ACTIVE.")
    print(f"👉 ARRÊT : Lancez 'stop.py' ou créez le fichier {Config.STOP_SIGNAL_PATH.name}")
    print("=" * 60 + "\n")
    sys.stdout.flush()

    try:
        while not s_ev.is_set():
            if Config.STOP_SIGNAL_PATH.exists():
                s_ev.set()
                break
            time.sleep(1.0)
    except KeyboardInterrupt:
        s_ev.set()
    finally:
        # --- ARCHIVAGE FINAL ULTRA-RAPIDE (Sans appel LLM) ---
        print("\n" + "-" * 30)
        print("[Main] 📂 Archivage de la session...")
        try:
            if Config.DASHBOARD_PATH.exists():
                with open(Config.DASHBOARD_PATH, "r", encoding="utf-8") as f:
                    content = f.read()

                m = MemoryManager()
                # On crée la note directement avec le dernier contenu connu du dashboard
                note_id = m.create_atomic_note(content, ["ARCHIVE_SESSION", Config.SESSION_ID])
                print(f"[Main] ✅ Note archivée : zettelkasten/{note_id}.md")
            else:
                print("[Main] ⚠️ Dashboard introuvable, archive non créée.")
        except Exception as e:
            print(f"[Main] ⚠️ Erreur archivage : {e}")

        # Suppression du signal et fermeture
        if Config.STOP_SIGNAL_PATH.exists(): Config.STOP_SIGNAL_PATH.unlink()
        for p in processes:
            p.join(timeout=0.5)
            if p.is_alive(): p.terminate()

        print("--- SYSTÈME ÉTEINT PROPREMENT ---")
        sys.stdout.flush()