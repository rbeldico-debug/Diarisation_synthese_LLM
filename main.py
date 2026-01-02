import multiprocessing
import queue
import time
import sys
from datetime import datetime
from config import Config
from brain.graph.manager import GraphStateManager
from brain.sanitizer import TextSanitizer
from ears.microphone import MicrophoneStream
from ears.vad_engine import VADSegmenter
from output.speaker import mouth_worker
from output.tui_manager import TUIManager
from memory.storage_manager import MemoryManager

# Import du TUI
from rich.live import Live



# --- FONCTIONS HELPER POUR LES LOGS ---
def log_to_queue(q, source, message, style="white"):
    """Envoie un log formaté à la queue d'affichage."""
    try:
        q.put(("log", (source, message, style)))
    except:
        pass


def update_brain_view(q, nodes_data):
    """Envoie l'état du cerveau à la queue d'affichage."""
    try:
        q.put(("brain", nodes_data))
    except:
        pass


# --- PROCESSUS ---

def analyst_process(stop_event, tts_queue, stimuli_queue, display_queue):
    """P4 : Analyste (Gère le Cerveau et envoie les données d'affichage)"""
    from analyst.synthesizer import Synthesizer
    from memory.librarian import Librarian

    log_to_queue(display_queue, "Analyste", "Chargement du Graphe...", "cyan")
    graph_manager = GraphStateManager()
    graph_manager.load_state()

    synther = Synthesizer(graph_manager=graph_manager)
    memory = MemoryManager()
    librarian = Librarian()

    last_vocal_brief = time.time()
    last_decay_time = time.time()
    last_propagate_time = time.time()
    last_monitor_time = time.time()

    log_to_queue(display_queue, "Analyste", "Système Prêt.", "green")

    try:
        while not stop_event.is_set():
            now = time.time()

            # 1. Propagation (2s)
            if now - last_propagate_time > 2.0:
                graph_manager.propagate_activation()
                last_propagate_time = now

            # 2. Oubli (60s)
            if now - last_decay_time > 60.0:
                for node in graph_manager.nodes.values():
                    node.decay()
                    node.rest()
                last_decay_time = now
                log_to_queue(display_queue, "Cycle", "Oubli naturel appliqué.", "yellow")

            # 3. Boucle Rapide & Monitoring
            loops = int(Config.ANALYST_UPDATE_INTERVAL_SECONDS * 10)
            for _ in range(loops):
                if stop_event.is_set(): break

                # A. Stimuli
                try:
                    stimulus = stimuli_queue.get_nowait()
                    graph_manager.inject_stimulus(stimulus['text'], stimulus['tags'])
                except queue.Empty:
                    pass

                # B. Moniteur Temps Réel
                now = time.time()
                if now - last_monitor_time > 0.5:  # On rafraichit 2x par seconde
                    # Export JSON pour le script de monitoring externe
                    monitor_path = Config.LOGS_DIR / "brain_activity.json"
                    graph_manager.export_activity_snapshot(monitor_path)
                    last_monitor_time = now

                time.sleep(0.1)

            if stop_event.is_set(): break

            # 4. Dashboard & Concepts
            log_to_queue(display_queue, "Analyste", "Mise à jour Dashboard...", "dim cyan")
            dashboard_md, concepts = synther.generate_summary()
            memory.update_dashboard(dashboard_md)

            if concepts:
                log_to_queue(display_queue, "Analyste", f"{len(concepts)} concepts extraits.", "magenta")
                for concept in concepts:
                    try:
                        filename = librarian.process_concept(concept['title'], concept['content'], concept['tags'])
                        log_to_queue(display_queue, "Librarian", f"Concept traité: {filename}", "green")
                    except Exception as e:
                        log_to_queue(display_queue, "Analyste", f"Erreur: {e}", "red")

            # 5. Briefing
            if Config.ENABLE_TTS and (now - last_vocal_brief >= 120.0):
                brief = synther.generate_vocal_brief(dashboard_md)
                if brief:
                    tts_queue.put(brief)
                    log_to_queue(display_queue, "Bouche", "Génération briefing vocal.", "cyan")
                    last_vocal_brief = now

    except Exception as e:
        log_to_queue(display_queue, "Analyste", f"CRASH: {e}", "bold red")
    finally:
        log_to_queue(display_queue, "Analyste", "Sauvegarde...", "red")
        graph_manager.save_state()


def ear_process(audio_queue, stop_event, display_queue):
    """P1 : Oreille"""
    from brain.inference_client import InferenceClient

    log_to_queue(display_queue, "Oreille", "Initialisation VAD...", "dim white")
    # Pour éviter de recharger Silero à chaque fois, on suppose qu'il est léger
    # Mais ici on garde la structure.
    try:
        vad = VADSegmenter(sample_rate=Config.SAMPLE_RATE, threshold=Config.VAD_THRESHOLD,
                           min_silence_duration_ms=Config.VAD_MIN_SILENCE_DURATION_MS)

        with MicrophoneStream(rate=Config.SAMPLE_RATE, block_size=Config.BLOCK_SIZE) as mic:
            log_to_queue(display_queue, "Oreille", "Écoute active 🎤", "bold green")

            for chunk in mic.generator():
                if stop_event.is_set(): break
                payload = vad.process_chunk(chunk)
                if payload:
                    audio_queue.put(payload)
                    # Petit point pour dire qu'on a capté un truc
                    # log_to_queue(display_queue, "Oreille", "Segment capturé", "dim")
    except Exception as e:
        log_to_queue(display_queue, "Oreille", f"Erreur Micro: {e}", "red")


def brain_process(audio_queue, stimuli_queue, stop_event, display_queue):
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

    # Warmup (Simplifié ici pour l'exemple, idéalement on log via display_queue)
    inference.warm_up()
    router._precompute_taxonomy()
    log_to_queue(display_queue, "Cerveau", "Moteurs IA chargés.", "green")

    while not stop_event.is_set():
        try:
            payload = audio_queue.get(timeout=1.0)
        except queue.Empty:
            continue

        text, speakers = inference.process_audio(payload.audio_data, payload.sample_rate)

        if not TextSanitizer.is_valid(text):
            continue

        tags = router.route(text)
        embedding = router.get_embedding(text)

        # Log visible dans l'interface
        log_to_queue(display_queue, "Moi", f"({tags}) {text}", "white")

        memory.log_event(source="user", text=text, intent=tags, extra={"speakers": speakers})

        try:
            stimuli_queue.put({"text": text, "tags": tags})
        except:
            pass

        if embedding is not None:
            vector_db.add_to_memory(text, embedding, {"timestamp": datetime.now().isoformat(), "intent": tags,
                                                      "session": Config.SESSION_ID})


def wrapped_mouth_worker(tts_queue, stop_event, display_queue):
    """Wrapper pour le worker de la bouche pour ajouter des logs"""
    from output.speaker import EdgeVoice
    import asyncio

    log_to_queue(display_queue, "Bouche", "Service TTS prêt.", "green")
    speaker = EdgeVoice()

    while not stop_event.is_set():
        try:
            text = tts_queue.get(timeout=1.0)
            if text:
                log_to_queue(display_queue, "Bouche", "🗣️ En train de parler...", "cyan")
                speaker.speak(text)
        except:
            continue


# --- MAIN ---

if __name__ == "__main__":
    multiprocessing.freeze_support()
    Config.LOGS_DIR.mkdir(exist_ok=True)
    if Config.STOP_SIGNAL_PATH.exists(): Config.STOP_SIGNAL_PATH.unlink()

    # Queues
    m_q = multiprocessing.Queue()
    t_q = multiprocessing.Queue()
    s_q = multiprocessing.Queue()
    display_q = multiprocessing.Queue()  # La queue magique pour le TUI
    s_ev = multiprocessing.Event()

    # Processus
    processes = [
        multiprocessing.Process(target=ear_process, args=(m_q, s_ev, display_q), name="Oreille"),
        multiprocessing.Process(target=brain_process, args=(m_q, s_q, s_ev, display_q), name="Cerveau"),
        multiprocessing.Process(target=wrapped_mouth_worker, args=(t_q, s_ev, display_q), name="Bouche"),
        multiprocessing.Process(target=analyst_process, args=(s_ev, t_q, s_q, display_q), name="Analyste")
    ]

    for p in processes: p.start()

    # --- BOUCLE PRINCIPALE D'AFFICHAGE (MAIN THREAD) ---
    tui = TUIManager()

    # Données locales pour le refresh
    current_brain_data = []
    pending_logs = []

    try:
        with Live(tui.get_layout([], [], "Démarrage..."), refresh_per_second=4, screen=True) as live:
            while not s_ev.is_set():
                if Config.STOP_SIGNAL_PATH.exists():
                    s_ev.set()
                    break

                # On vide la queue d'affichage
                while not display_q.empty():
                    try:
                        msg_type, data = display_q.get_nowait()
                        if msg_type == "log":
                            pending_logs.append(data)
                        elif msg_type == "brain":
                            current_brain_data = data
                    except queue.Empty:
                        break

                # Mise à jour de l'écran
                status_msg = "En écoute..."
                if s_ev.is_set(): status_msg = "Arrêt en cours..."

                live.update(tui.get_layout(current_brain_data, pending_logs, status_msg))
                pending_logs = []  # On vide les logs traités (ils sont stockés dans l'historique du TUI)

                time.sleep(0.1)

    except KeyboardInterrupt:
        s_ev.set()
    finally:
        print("Arrêt des processus...")
        for p in processes:
            p.join(timeout=5)
            if p.is_alive(): p.terminate()
        print("Système éteint.")