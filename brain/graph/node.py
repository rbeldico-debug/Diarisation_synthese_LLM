# brain/graph/node.py

import math
from dataclasses import dataclass, field
from typing import Set, Optional
from datetime import datetime
from pathlib import Path
from config import Config


@dataclass
class GraphNode:
    """
    Représentation en mémoire d'une note atomique (Le Neurone).
    """
    # --- Données Persistantes ---
    full_path: Path
    filename: str
    uid: str
    title: str
    tags: Set[str]
    links: Set[str]
    base_weight: float
    date_updated: datetime

    # --- Données Volatiles (Runtime) ---
    activation: float = 0.0
    consecutive_activations: int = 0
    _static_score: float = 0.0

    def __post_init__(self):
        self._calculate_static_potential()

    def _calculate_static_potential(self):
        # 1. Structure (Logarithmique)
        n_links = len(self.links)
        s_score = Config.COEF_STRUCTURE * math.log(1 + n_links)

        # 2. Fraîcheur (Hyperbolique)
        age_days = (datetime.now() - self.date_updated).days
        age_days = max(0, age_days)
        c_score = Config.COEF_RECENCY / (1 + age_days * 0.1)

        # 3. Maturité
        maturity_mult = 1.0
        for tag in self.tags:
            if tag in Config.COEF_MATURITY:
                maturity_mult = Config.COEF_MATURITY[tag]
                break

        self._static_score = (self.base_weight + s_score + c_score) * maturity_mult

    def stimulate(self, amount: float):
        self.activation += amount

    def decay(self):
        self.activation *= Config.DECAY_RATE
        if self.activation < 0.1:
            self.activation = 0.0

    def get_current_weight(self) -> float:
        """
        Calcule le poids total en appliquant la pénalité de fatigue
        conformément à la formule de l'ADR-022.
        """
        # Formule de l'ADR : Penalty = (n / N_max) ** 3
        # Pour éviter une division par zéro si N_max est 0, on s'assure qu'il est > 0
        if Config.FATIGUE_TOLERANCE > 0:
            fatigue_ratio = self.consecutive_activations / Config.FATIGUE_TOLERANCE
            # La pénalité est mise à l'échelle par le score statique pour être proportionnelle
            fatigue_cost = (fatigue_ratio ** 3) * self._static_score
        else:
            fatigue_cost = 0.0

        total = (self._static_score + self.activation) - fatigue_cost
        return max(0.0, total)

    def register_activation(self):
        self.consecutive_activations += 1

    def rest(self):
        # L'oubli de la fatigue est plus lent que l'oubli de l'activation
        if self.consecutive_activations > 0:
            self.consecutive_activations -= 1

    def __hash__(self):
        return hash(self.filename)