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
    """P4 : Analyste + Oracle Vocal + Bibliothécaire"""  # <--- Updated docstring
    from analyst.synthesizer import Synthesizer
    from memory.storage_manager import MemoryManager
    from memory.librarian import Librarian  # <--- Nouvel import
    import time

    synther = Synthesizer()
    memory = MemoryManager()
    librarian = Librarian()  # <--- Instanciation

    last_vocal_brief = time.time()
    VOCAL_INTERVAL = 120

    print(f"[Analyste] ✅ Prêt. Session : {Config.SESSION_ID}")

    while not stop_event.is_set():
        # ... (Boucle d'attente inchangée) ...
        for _ in range(Config.ANALYST_UPDATE_INTERVAL_SECONDS):
            if stop_event.is_set(): return
            time.sleep(1)

        # 1. GÉNÉRATION
        dashboard_md, concepts = synther.generate_summary()

        # 2. UPDATE DASHBOARD
        memory.update_dashboard(dashboard_md)
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[Analyste] 📝 {timestamp} : Dashboard mis à jour.")

        # 3. TRAITEMENT INTELLIGENT DES CONCEPTS (Librarian)
        if concepts:
            print(f"[Analyste] 💎 {len(concepts)} concepts candidats. Le Bibliothécaire analyse...")
            for concept in concepts:
                if stop_event.is_set(): break
                try:
                    # On délègue tout au Bibliothécaire
                    librarian.process_concept(
                        title=concept['title'],
                        content=concept['content'],
                        tags=concept['tags']
                    )
                    time.sleep(0.5)
                except Exception as e:
                    print(f"[Analyste] ⚠️ Erreur Librarian sur '{concept.get('title')}': {e}")

        sys.stdout.flush()

        # 4. BRIEFING VOCAL (Reste inchangé)
        now = time.time()
        if now - last_vocal_brief >= VOCAL_INTERVAL:
            # ... (Code existant du briefing vocal)
            brief = synther.generate_vocal_brief(dashboard_md)
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
        # --- ARCHIVAGE FINAL ---
        print("\n" + "-" * 30)
        print("[Main] 📂 Archivage de la session...")
        try:
            # On essaie de lire le backup local créé par MemoryManager
            backup_path = Config.LOGS_DIR / "dashboard_backup.md"

            if backup_path.exists():
                with open(backup_path, "r", encoding="utf-8") as f:
                    content = f.read()

                m = MemoryManager()
                # On archive dans le Zettelkasten via le Bridge
                # Note: On utilise create_atomic_note pour garder la cohérence
                archive_name = f"Session_Archive_{Config.SESSION_ID}"
                m.create_atomic_note(archive_name, content, ["ARCHIVE_SESSION"])
                print(f"[Main] ✅ Session archivée sous : {archive_name}")
            else:
                print("[Main] ⚠️ Backup local introuvable, archivage ignoré.")
        except Exception as e:
            print(f"[Main] ⚠️ Erreur archivage : {e}")