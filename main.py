import multiprocessing
import queue
import time
from datetime import datetime
import numpy as np
import os
from config import Config

# Patch NumPy
if not hasattr(np, "NaN"): np.NaN = np.nan

from ears.microphone import MicrophoneStream
from ears.vad_engine import VADSegmenter
from output.speaker import mouth_worker
from memory.storage_manager import MemoryManager


def analyst_process(stop_event: multiprocessing.Event, tts_queue: multiprocessing.Queue):
    """P4 : Analyste + Oracle Vocal"""
    from analyst.synthesizer import Synthesizer
    synther = Synthesizer()
    memory = MemoryManager()

    last_vocal_brief = time.time()
    VOCAL_INTERVAL = 300

    print(f"[Analyste] ✅ Prêt. Session : {Config.SESSION_ID}")

    while not stop_event.is_set():
        # Attente
        for _ in range(Config.ANALYST_UPDATE_INTERVAL_SECONDS):
            if stop_event.is_set(): return
            time.sleep(1)

        content = synther.generate_summary()
        memory.update_dashboard(content)

        now = time.time()
        if now - last_vocal_brief >= VOCAL_INTERVAL:
            print("[Analyste] 🧠 Génération du briefing vocal...")
            brief = synther.generate_vocal_brief(content)
            if brief:
                tts_queue.put(brief)
                last_vocal_brief = now


def ear_process(audio_queue: multiprocessing.Queue, stop_event: multiprocessing.Event):
    """P1 : Oreille (Capture & VAD)"""
    from brain.inference_client import InferenceClient
    inf = InferenceClient()
    inf.warm_up()

    vad = VADSegmenter(
        sample_rate=Config.SAMPLE_RATE,
        threshold=Config.VAD_THRESHOLD,
        min_silence_duration_ms=Config.VAD_MIN_SILENCE_DURATION_MS
    )

    try:
        with MicrophoneStream(rate=Config.SAMPLE_RATE, block_size=Config.BLOCK_SIZE) as mic:
            print(f"[Oreille] ✅ Écoute active (Session {Config.SESSION_ID}).")
            for chunk in mic.generator():
                if stop_event.is_set(): break
                payload = vad.process_chunk(chunk)
                if payload:
                    print(f"[Oreille] 🔊 Segment capturé ({payload.duration_seconds:.1f}s) -> Envoi au Cerveau")
                    audio_queue.put(payload)
    except Exception as e:
        print(f"[Oreille] ❌ Erreur micro : {e}")


def brain_process(audio_queue: multiprocessing.Queue, stop_event: multiprocessing.Event):
    """P2 : Scribe Silencieux + Mémoire Long Terme"""
    from brain.inference_client import InferenceClient
    from brain.router import IntentRouter
    from memory.storage_manager import MemoryManager
    from memory.vector_manager import VectorManager
    from core.warmup import WarmupManager # <--- Nouveau

    # Initialisation
    inference = InferenceClient()
    router = IntentRouter()
    memory = MemoryManager()
    vector_db = VectorManager()
    warmup = WarmupManager(inference, router, vector_db) # <--- Nouveau

    # Phase de préchauffage global
    warmup.perform_all()

    print(f"[Cerveau] 🧠 Système stabilisé.")

    while not stop_event.is_set():
        try:
            payload = audio_queue.get(timeout=1.0)
        except queue.Empty:
            continue

        # 1. Transcription
        text, speakers = inference.process_audio(payload.audio_data, payload.sample_rate)
        if not text.strip(): continue

        # 2. Tagging & Embedding (On réutilise l'embedding pour ChromaDB)
        # On modifie légèrement l'usage du router pour récupérer le vecteur
        # Pour simplifier ici, on laisse le router faire son travail
        tags = router.route(text)

        # On récupère l'embedding via le router pour éviter un double appel API
        embedding = router._get_embedding(text)

        # 3. Persistance Double (ADR-010 & ADR-011)
        timestamp = datetime.now().isoformat()

        # A. Log JSONL (Source de vérité)
        memory.log_event(source="user", text=text, intent=tags, extra={"speakers": speakers})

        # B. Mémoire Vectorielle (ChromaDB)
        if embedding is not None:
            vector_db.add_to_memory(
                text=text,
                embedding=embedding,
                metadata={"timestamp": timestamp, "intent": tags, "session": Config.SESSION_ID}
            )

        print(f"📝 {tags} : {text}")


if __name__ == "__main__":
    multiprocessing.freeze_support()

    # On force la création du dossier avant de lancer les processus
    Config.LOGS_DIR.mkdir(exist_ok=True)

    print(f"--- SYSTÈME GÉRALD V2.5 | SESSION {Config.SESSION_ID} ---")
    print(f"--- JOURNAL : {Config.JOURNAL_PATH.name} ---")

    m_q = multiprocessing.Queue()  # Queue Audio
    t_q = multiprocessing.Queue()  # Queue TTS
    s_ev = multiprocessing.Event()

    # Note : On passe Config.SESSION_ID pour garantir la synchro
    processes = [
        multiprocessing.Process(target=ear_process, args=(m_q, s_ev), name="Oreille"),
        multiprocessing.Process(target=brain_process, args=(m_q, s_ev), name="Cerveau"),
        multiprocessing.Process(target=mouth_worker, args=(t_q, s_ev), name="Bouche"),
        multiprocessing.Process(target=analyst_process, args=(s_ev, t_q), name="Analyste")
    ]

    for p in processes:
        p.start()

    try:
        while True:
            time.sleep(1)
            if not any(p.is_alive() for p in processes):
                print("[Main] Un processus est tombé. Arrêt...")
                break
    except KeyboardInterrupt:
        print("\n🛑 Arrêt manuel demandé...")
    finally:
        s_ev.set()
        for p in processes:
            p.join(timeout=2)
            if p.is_alive(): p.terminate()
        print("--- SYSTÈME ÉTEINT ---")