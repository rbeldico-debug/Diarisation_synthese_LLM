import multiprocessing
import threading
import queue
import time
from datetime import datetime
import numpy as np
import os
import sys
from config import Config
from brain.graph.manager import GraphStateManager
from brain.sanitizer import TextSanitizer

from ears.microphone import MicrophoneStream
from ears.vad_engine import VADSegmenter
from output.speaker import mouth_worker
from memory.storage_manager import MemoryManager


def analyst_process(stop_event: multiprocessing.Event,
                    tts_queue: multiprocessing.Queue,
                    stimuli_queue: multiprocessing.Queue):
    """P4 : Analyste + Oracle Vocal + Bibliothécaire + Cerveau + Moniteur"""
    from analyst.synthesizer import Synthesizer
    from memory.storage_manager import MemoryManager
    from memory.librarian import Librarian
    import time

    # --- INITIALISATION ---
    print("[Analyste] 🧠 Chargement de la structure mentale (Graph)...")
    graph_manager = GraphStateManager()
    graph_manager.load_state()

    synther = Synthesizer(graph_manager=graph_manager)
    memory = MemoryManager()
    librarian = Librarian()

    last_vocal_brief = time.time()
    VOCAL_INTERVAL = 120.0

    last_decay_time = time.time()
    last_monitor_time = time.time()  # Timer dédié pour l'affichage

    print(f"[Analyste] ✅ Prêt. Session : {Config.SESSION_ID}")

    try:
        while not stop_event.is_set():

            # --- 1. GESTION DU TEMPS (Oubli / Decay) ---
            # Toutes les 60s, on refroidit le cerveau
            now = time.time()
            if now - last_decay_time > 60.0:
                for node in graph_manager.nodes.values():
                    node.decay()
                    node.rest()
                last_decay_time = now

            # --- 2. BOUCLE RAPIDE (Attente active & Réflexes) ---
            # C'est ici qu'on attend le moment de générer le dashboard (60s)
            # Mais pendant qu'on attend, on surveille les stimuli et on affiche le moniteur

            # On découpe l'attente en tranches de 0.1s
            loops = int(Config.ANALYST_UPDATE_INTERVAL_SECONDS * 10)

            for _ in range(loops):
                if stop_event.is_set(): break

                # A. Réception des Stimuli (Bottom-Up)
                try:
                    stimulus = stimuli_queue.get_nowait()
                    graph_manager.inject_stimulus(stimulus['text'], stimulus['tags'])
                except queue.Empty:
                    pass

                # B. Moniteur Temps Réel (toutes les 5 secondes pour être réactif)
                now = time.time()
                if now - last_monitor_time > 5.0:
                    # On cherche les nœuds excités (Activation > 0.1)
                    top_nodes = sorted(
                        [n for n in graph_manager.nodes.values() if n.activation > 0.1],
                        key=lambda x: x.activation,
                        reverse=True
                    )[:3]

                    if top_nodes:
                        print(f"\n[🔥 ACTIVITÉ] Top Focus :")
                        for n in top_nodes:
                            # On affiche Activation (Réflexe) et Poids Total (Fond)
                            print(f"  - {n.filename} : Act={n.activation:.1f} | Total={n.get_current_weight():.1f}")
                    last_monitor_time = now

                time.sleep(0.1)  # Pause CPU

            if stop_event.is_set(): break

            # --- 3. COGITATION PROFONDE (Dashboard) ---
            # Une fois le temps d'attente écoulé, on réfléchit
            dashboard_md, concepts = synther.generate_summary()
            memory.update_dashboard(dashboard_md)
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[Analyste] 📝 {timestamp} : Dashboard mis à jour.")

            # --- 4. Traitement des Concepts ---
            if concepts:
                print(f"[Analyste] 💎 {len(concepts)} concepts candidats...")
                for concept in concepts:
                    if stop_event.is_set(): break
                    try:
                        filename = librarian.process_concept(
                            title=concept['title'],
                            content=concept['content'],
                            tags=concept['tags']
                        )
                        print(f"[Analyste] ✨ Concept traité : {filename}")
                        time.sleep(0.5)
                    except Exception as e:
                        print(f"[Analyste] ⚠️ Erreur Librarian sur '{concept.get('title')}': {e}")

            sys.stdout.flush()

            # --- 5. Briefing Vocal ---
            now = time.time()
            if Config.ENABLE_TTS and (now - last_vocal_brief >= VOCAL_INTERVAL):
                brief = synther.generate_vocal_brief(dashboard_md)
                if brief:
                    tts_queue.put(brief)
                    last_vocal_brief = now

    except Exception as e:
        print(f"[Analyste] ❌ Erreur critique : {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("\n[Analyste] 🛑 Arrêt demandé. Sauvegarde du cerveau...")
        graph_manager.save_state()
        print("[Analyste] 👋 Au revoir.")

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


def brain_process(audio_queue: multiprocessing.Queue,
                  stimuli_queue: multiprocessing.Queue,
                  stop_event: multiprocessing.Event):
    """P2 : Cerveau (Transcription + Routing + Envoi Stimuli)"""
    from brain.inference_client import InferenceClient
    from brain.router import IntentRouter
    from memory.storage_manager import MemoryManager
    from memory.vector_manager import VectorManager
    from core.warmup import WarmupManager
    import time

    inference = InferenceClient()
    router = IntentRouter()
    memory = MemoryManager()
    vector_db = VectorManager()

    # Warmup
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

        # --- FILTRAGE ANTI-BRUIT SEULEMENT ---
        # On rejette les "Sous-titrage ST 501" mais on garde "K.O."
        if not TextSanitizer.is_valid(text):
            continue

        # (L'étape de nettoyage REPLACEMENTS a été supprimée)

        tags = router.route(text)
        embedding = router.get_embedding(text)

        timestamp = datetime.now().isoformat()
        memory.log_event(source="user", text=text, intent=tags, extra={"speakers": speakers})

        # Envoi Stimulus
        try:
            stimuli_queue.put({"text": text, "tags": tags})
        except Exception:
            pass

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
    s_q = multiprocessing.Queue()  # Stimuli Queue

    processes = [
        multiprocessing.Process(target=ear_process, args=(m_q, s_ev), name="Oreille"),
        multiprocessing.Process(target=brain_process, args=(m_q, s_q, s_ev), name="Cerveau"),
        multiprocessing.Process(target=mouth_worker, args=(t_q, s_ev), name="Bouche"),
        multiprocessing.Process(target=analyst_process, args=(s_ev, t_q, s_q), name="Analyste")
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