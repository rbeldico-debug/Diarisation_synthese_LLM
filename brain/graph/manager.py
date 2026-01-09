import json
from pathlib import Path
from typing import Dict, List

from core.settings import settings
from brain.graph.node import GraphNode
from brain.graph.scanner import VaultScanner


class GraphStateManager:
    """
    Implémente ADR-019 (Runtime RAM) et ADR-022 (Dynamique).
    """

    def __init__(self):
        self.state_file = settings.LOGS_DIR / "brain_state.json"
        self.nodes: Dict[str, GraphNode] = {}

    def load_state(self):
        # 1. SCAN PHYSIQUE (ADR-019 Start)
        # On charge la structure réelle pour calculer S, C, T
        scanner = VaultScanner()
        self.nodes = scanner.scan_vault()

        # 2. Chargement État Volatile (Activations précédentes)
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for fname, n_data in data.items():
                        if fname in self.nodes:
                            # On restaure uniquement l'énergie (Volatile)
                            self.nodes[fname].activation = n_data.get("activation", 0.0)
                            self.nodes[fname].consecutive_activations = n_data.get("consecutive_activations", 0)
            except Exception:
                pass

        print(f"[Graph] Cortex chargé : {len(self.nodes)} nœuds actifs.")

    def save_state(self):
        # ADR-019 End : On ne sauvegarde que le volatile ici.
        # Le persistant (YAML) est géré par Librarian/Gardener.
        data = {}
        for fname, node in self.nodes.items():
            if node.activation > 0.1:  # Optimisation
                data[fname] = {
                    "activation": node.activation,
                    "consecutive_activations": node.consecutive_activations
                }
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except:
            pass

    def inject_stimulus(self, text: str, tags: str):
        """
        ADR-022 : Recrutement Bottom-Up (Stimulus).
        Active les nœuds pertinents par rapport au flux entrant.
        """
        text_lower = text.lower()

        # 1. Activation par correspondance directe (Keyword Match)
        # Si le titre d'une note est mentionné, elle reçoit un fort boost.
        for node in self.nodes.values():
            # On nettoie le titre pour la comparaison (.md)
            clean_title = node.title.lower()
            if clean_title in text_lower:
                # BOOST STIMULUS
                # Le boost est arbitraire ici, à calibrer (ex: +20)
                node.stimulate(20.0)
                # print(f"[Graph] ⚡ Stimulus Direct : {node.title}")

        # 2. Activation par Intention (Tags)
        # TODO: Si le routeur détecte [PHILOSOPHIE], activer faiblement tout ce qui est tagué #sujet/philosophie

    def propagate_activation(self):
        """
        ADR-022 : Amplification Top-Down.
        L'énergie se diffuse via les liens (Links).
        """
        # On calcule les deltas d'abord pour ne pas modifier pendant l'itération
        activations_delta = {}

        for filename, node in self.nodes.items():
            if node.activation > 1.0:
                # Quantité d'énergie transmise aux voisins
                energy_to_spread = node.activation * settings.PROPAGATION_RATE

                # Répartition équitable ou totale ? ADR suggère Top-Down.
                # On divise par le nombre de liens pour ne pas exploser le système
                if node.links:
                    energy_per_link = energy_to_spread / len(node.links)

                    for target_link in node.links:
                        # target_link est ex: "Concept.md"
                        if target_link in self.nodes:
                            activations_delta[target_link] = activations_delta.get(target_link, 0.0) + energy_per_link

        # Application des deltas
        for fname, amount in activations_delta.items():
            self.nodes[fname].stimulate(amount)

    def export_activity_snapshot(self, filepath: Path):
        """Génère la vue pour le Dashboard (Tri par Poids ADR-022)."""
        snapshot = {"nodes": []}

        # On utilise get_current_weight() qui est la formule ADR-022 complète
        # W_t = Static(S,C,T) + Dynamic(Act) - Fatigue
        sorted_nodes = sorted(self.nodes.values(), key=lambda x: x.get_current_weight(), reverse=True)

        for node in sorted_nodes[:20]:
            snapshot["nodes"].append({
                "title": node.title,
                "weight": round(node.get_current_weight(), 1),
                "activation": round(node.activation, 1),
                "fatigue": node.consecutive_activations,
                "ignited": node.activation > settings.IGNITION_THRESHOLD,
                "links": len(node.links)
            })

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(snapshot, f)
        except:
            pass