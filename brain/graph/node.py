import math
from dataclasses import dataclass
from typing import Set
from datetime import datetime
from pathlib import Path

# MIGRATION CONFIG
from core.settings import settings

@dataclass
class GraphNode:
    full_path: Path
    filename: str
    uid: str
    title: str
    tags: Set[str]
    links: Set[str]
    base_weight: float
    date_updated: datetime

    # Runtime
    activation: float = 0.0
    consecutive_activations: int = 0
    _static_score: float = 0.0

    def __post_init__(self):
        self._calculate_static_potential()

    def _calculate_static_potential(self):
        n_links = len(self.links)
        s_score = settings.COEF_STRUCTURE * math.log(1 + n_links)

        age_days = (datetime.now() - self.date_updated).days
        age_days = max(0, age_days)
        c_score = settings.COEF_RECENCY / (1 + age_days * 0.1)

        maturity_mult = 1.0
        for tag in self.tags:
            if tag in settings.COEF_MATURITY:
                maturity_mult = settings.COEF_MATURITY[tag]
                break

        self._static_score = (self.base_weight + s_score + c_score) * maturity_mult

    def stimulate(self, amount: float):
        self.activation += amount

    def decay(self):
        self.activation *= settings.DECAY_RATE
        if self.activation < 0.1:
            self.activation = 0.0

    def get_current_weight(self) -> float:
        if settings.FATIGUE_TOLERANCE > 0:
            fatigue_ratio = self.consecutive_activations / settings.FATIGUE_TOLERANCE
            fatigue_cost = (fatigue_ratio ** 3) * self._static_score
        else:
            fatigue_cost = 0.0

        total = (self._static_score + self.activation) - fatigue_cost
        return max(0.0, total)

    def register_activation(self):
        self.consecutive_activations += 1

    def rest(self):
        if self.consecutive_activations > 0:
            self.consecutive_activations -= 1

    def __hash__(self):
        return hash(self.filename)