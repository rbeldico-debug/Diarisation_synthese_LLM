import multiprocessing
import queue
import sys
import time
from datetime import datetime

# Import des modules locaux
from core.data_models import AudioPayload
from ears.microphone import MicrophoneStream
from ears.vad_engine import VADSegmenter
from brain.llm_client import LLMClient
from config import Config


# Note : On n'importe PAS Transcriber/Diarizer ici au niveau global
# pour éviter qu'ils soient chargés dans le processus principal inutilement.


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
    """
    Processus P2 (Consommateur) : Récupère les segments et applique l'IA.
    """
    print("[Cerveau] Chargement des modèles (Whisper + Pyannote)... Patience.")

    from brain.transcription import Transcriber
    from brain.diarization import Diarizer
    # Import du nouveau module
    from output.formatter import DialogueFormatter
    from config import Config  # Pour accéder aux constantes si besoin

    try:
        transcriber = Transcriber()
        diarizer = Diarizer()
        formatter = DialogueFormatter()  # <-- Initialisation
        llm = LLMClient() # <--- NOUVEAU
        print("[Cerveau] 🧠 Modèles chargés. En attente de données...")
    except Exception as e:
        print(f"[Cerveau] ❌ Erreur critique chargement modèles : {e}")
        return

    while not stop_event.is_set():
        try:
            payload = audio_queue.get(timeout=1.0)
        except queue.Empty:
            continue

        # --- TRAITEMENT IA ---
        start_time = time.time()
        print(f"\n[Cerveau] ⚙️ Traitement...")

        # 1. Transcription
        try:
            text = transcriber.transcribe(payload.audio_data, payload.sample_rate)
        except Exception as e:
            print(f"[Cerveau] Erreur Whisper : {e}")
            text = "..."

        # 2. Diarisation
        speakers_list = []
        if payload.duration_seconds >= Config.MIN_DURATION_FOR_DIARIZATION:
            try:
                segments = diarizer.diarize(payload.audio_data, payload.sample_rate)
                speakers_list = sorted(list(set([s['speaker'] for s in segments])))
            except Exception as e:
                print(f"[Cerveau] Erreur Diarization : {e}")

        # 3. Formatage & Historique
        formatted_line = formatter.process_turn(text, speakers_list)
        process_time = time.time() - start_time
        print(f"✅ {formatted_line} (Calcul: {process_time:.2f}s)")

        # 4. GÉNÉRATION DE RÉPONSE (Si c'est l'utilisateur qui parle)
        if "Utilisateur" in formatted_line or "Gérald" in formatted_line:
            print("[Cerveau] 🤔 Réflexion...")

            # --- CHRONO DÉBUT ---
            llm_start_time = time.time()

            # On envoie tout l'historique
            context = formatter.get_context_string()
            response = llm.query(context, text)

            # --- CHRONO FIN ---
            llm_duration = time.time() - llm_start_time

            # On l'ajoute aussi à l'historique pour que l'IA s'en souvienne
            formatter.process_turn(response, ["Assistant"])

            # Affichage avec le temps de latence
            print(f"🤖 Assistant: {response} (Génération: {llm_duration:.2f}s)")
            print("-" * 50)


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