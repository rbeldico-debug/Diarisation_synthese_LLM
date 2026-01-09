import time
import queue
import logging
from datetime import datetime
from pathlib import Path

from core.settings import settings
from core.data_models import AudioPayload
from brain.sanitizer import TextSanitizer

# Modules Métier
from brain.inference_client import InferenceClient
from brain.router import IntentRouter
from brain.graph.manager import GraphStateManager
from analyst.synthesizer import Synthesizer
from memory.storage_manager import MemoryManager
from memory.vector_manager import VectorManager
from memory.librarian import Librarian


class BrainOrchestrator:
    # AJOUT de input_queue dans les arguments
    def __init__(self, audio_queue: queue.Queue, tts_queue: queue.Queue, input_queue: queue.Queue, stop_event):
        self.audio_queue = audio_queue
        self.tts_queue = tts_queue
        self.input_queue = input_queue  # <--- Nouveau
        self.stop_event = stop_event

        print("[Orchestrator] 🧠 Initialisation du Cortex...")
        # ... (Reste de l'init inchangé : chargement moteurs, etc.) ...
        self.inference = InferenceClient()
        self.router = IntentRouter()
        self.graph = GraphStateManager()
        self.memory = MemoryManager()
        self.vectors = VectorManager()
        self.librarian = Librarian()
        self.synthesizer = Synthesizer(graph_manager=self.graph)

        self.graph.load_state()
        self.inference.warm_up()
        self.graph.export_activity_snapshot(settings.LOGS_DIR / "brain_activity.json")

        self.last_propagation = time.time()
        self.last_decay = time.time()
        self.last_gardening = time.time()

        print("[Orchestrator] ✅ Système Prêt.")

    def run(self):
        """Boucle Principale"""
        while not self.stop_event.is_set():
            try:
                # 1. Check Texte (Priorité max)
                try:
                    msg_type, content = self.input_queue.get_nowait()
                    if msg_type == "text":
                        self.process_text_input(content)
                except queue.Empty:
                    pass

                # 2. Check Audio (Priorité haute)
                # On utilise get_nowait ou timeout très court pour ne pas bloquer le texte
                try:
                    audio_payload = self.audio_queue.get(timeout=0.1)
                    self.process_interaction(audio_payload)
                except queue.Empty:
                    # 3. Tâches de fond (Si rien d'autre)
                    self.process_background_tasks()

            except Exception as e:
                print(f"[Orchestrator] Erreur Loop: {e}")

    def process_text_input(self, text: str):
        """Entrée Texte (Clavier)"""
        print(f"\n[Flux Texte] ⌨️ {text}")
        # On délègue à la logique centrale
        self._execute_intent(text, source="Clavier")

    def process_interaction(self, payload: AudioPayload):
        """Entrée Audio (Microphone)"""
        # 1. Transcription (Whisper)
        text, speakers = self.inference.process_audio(payload.audio_data, payload.sample_rate)

        if not TextSanitizer.is_valid(text):
            return

        print(f"\n[Flux Audio] 🗣️ {text}")

        # On délègue à la logique centrale
        self._execute_intent(text, source="Vocal")

        # --- LOGIQUE CENTRALE (Cerveau) ---

    def _execute_intent(self, text: str, source: str):
        """
        Cœur décisionnel : Route -> Agit.
        """
        # 1. Identification de l'intention (Mistral Nemo)
        intent = self.router.route(text)
        print(f"[Orchestrator] Intention : {intent}")

        # 2. Aiguillage
        if intent == "[READ]":
            # Mode Assistant : On répond à l'utilisateur
            self._handle_read_intent(text, source)

        elif intent == "[WRITE]":
            # Mode Prise de Note : On enregistre et on se tait
            self._handle_write_intent(text, source, intent_tag=intent)

        elif intent == "[CHAT]":
            # Mode Conversation : On enregistre comme du Write pour l'instant
            # (Plus tard on pourra ajouter une réponse "Chat" pure sans note)
            self._handle_write_intent(text, source, intent_tag=intent)

        elif intent == "[CMD]":
            print("[Orchestrator] Commande reçue (Non implémenté).")

        # --- HANDLERS SPÉCIFIQUES ---

    def _handle_write_intent(self, text: str, source: str, intent_tag: str):
        """
        Pipeline classique : Stimulus -> Vector -> Dashboard -> Librarian (Inbox)
        """
        # 1. Injection Stimulus (Réveil Graphe)
        self.graph.inject_stimulus(text, intent_tag)

        # 2. Log Journal (Mémoire Court Terme)
        self.memory.log_event(source=source, text=text, intent=intent_tag)

        # 3. Mémoire Vectorielle (Long Terme)
        embedding = self.router.get_embedding(text)
        if embedding is not None:
            self.vectors.add_to_memory(text, embedding, {
                "timestamp": datetime.now().isoformat(),
                "session": "current"
            })

        # 4. Synthèse Dashboard (Mise à jour Web)
        dashboard_md, concepts = self.synthesizer.generate_summary()
        self.memory.update_dashboard(dashboard_md)

        # 5. Extraction de Concepts (Vers 00_Inbox)
        if concepts:
            print(f"[Orchestrator] 💡 {len(concepts)} concepts extraits -> Inbox.")
            for concept in concepts:
                self.librarian.process_concept(concept['title'], concept['content'], concept['tags'])

    def _handle_read_intent(self, text: str, source: str):
        """
        Pipeline RAG + TTS : Recherche -> Synthèse -> Parole
        """
        print("[Orchestrator] 🔍 Recherche d'information...")

        # 1. Log de la demande
        self.memory.log_event(source=source, text=text, intent="[READ]")

        # 2. Recherche RAG (Vecteurs + Graphe)
        context = []

        # A. Vecteurs (Ce qu'on a déjà dit)
        emb = self.router.get_embedding(text)
        if emb is not None:
            res = self.vectors.search_similar(emb, n_results=3)
            if res and res['documents']:
                context.extend(res['documents'][0])

        # B. Graphe (Ce qui est activé/Relié)
        # On pourrait chercher les nœuds dont le titre ressemble à la demande
        # Pour l'instant on prend les nœuds actifs
        active_nodes = sorted([n for n in self.graph.nodes.values() if n.activation > 0],
                              key=lambda x: x.activation, reverse=True)[:3]
        for n in active_nodes:
            context.append(f"Concept pertinent : {n.title}")

        # 3. Génération de la réponse vocale (LLM)
        context_str = "\n".join(context)
        system_prompt = (
            "Tu es Océane. L'utilisateur te pose une question sur sa base de connaissance.\n"
            "Réponds brièvement (max 2 phrases) en utilisant le CONTEXTE fourni.\n"
            "Si tu ne sais pas, dis-le simplement."
        )

        try:
            from openai import OpenAI  # Import local pour éviter conflit si non chargé globalement
            client = OpenAI(base_url=settings.LLM_BASE_URL, api_key="ollama")

            response = client.chat.completions.create(
                model=settings.LLM_MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"CONTEXTE:\n{context_str}\n\nQUESTION: {text}"}
                ],
                temperature=0.7
            )
            answer = response.choices[0].message.content

            # 4. Affichage & Parole
            print(f"[Océane] 🗣️ {answer}")
            self.memory.log_event(source="Océane", text=answer, intent="[REPONSE]")

            # Envoi à la Bouche (TTS)
            self.tts_queue.put(answer)

        except Exception as e:
            print(f"[Orchestrator] Erreur Read Intent: {e}")

    def process_background_tasks(self):
        """Maintenance du système quand l'utilisateur ne parle pas."""
        now = time.time()

        # A. Propagation de l'Activation (Toutes les 2s)
        if now - self.last_propagation > 2.0:
            self.graph.propagate_activation()
            # Export JSON pour le Web
            self.graph.export_activity_snapshot(settings.LOGS_DIR / "brain_activity.json")
            self.last_propagation = now

        # B. Oubli & Fatigue (Toutes les 10s pour être plus réactif)
        if now - self.last_decay > 10.0:
            for node in self.graph.nodes.values():
                node.decay()
                node.rest()
            self.last_decay = now

        # C. Jardinage Automatique (Toutes les 60s)
        # C'est ici qu'on applique vos règles (Graine -> Sapling)
        if now - self.last_gardening > 60.0:
            self._gardening_cycle()
            self.last_gardening = now

    def _gardening_cycle(self):
        """
        Applique les règles algorithmiques de '00_tags.md'.
        """
        # On ne scanne pas tout pour ne pas geler le PC, juste un échantillon ou les actifs
        # Pour l'instant, on fait un pass sur les nœuds en mémoire RAM
        changes_count = 0

        for node in self.graph.nodes.values():
            # RÈGLE 1 : Graine -> Sapling
            # SI #état/graine ET (liens > 2) -> #état/sapling
            if "état/graine" in node.tags and len(node.links) > 2:
                print(f"[Jardinier] 🌱 -> 🌳 Croissance détectée : {node.title}")
                node.tags.remove("état/graine")
                node.tags.add("état/sapling")
                # TODO: Répercuter la modif dans le fichier Markdown physique via Librarian
                changes_count += 1

            # RÈGLE 2 : Archivage (Apoptose)
            # SI non modifié depuis 2 ans (730 jours) -> #archives
            days_inactive = (datetime.now() - node.date_updated).days
            if days_inactive > 730 and "archives" not in str(node.tags):
                print(f"[Jardinier] 🍂 Archivage auto : {node.title}")
                # Logic d'archivage à implémenter
                pass

        if changes_count > 0:
            print(f"[Jardinier] {changes_count} mises à jour effectuées.")
            self.graph.save_state()