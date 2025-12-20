from collections import deque
from config import Config


class DialogueFormatter:
    """
    Gère l'historique de la conversation et le formatage pour le LLM.
    """

    def __init__(self):
        # Deque est une liste optimisée qui supprime automatiquement les vieux éléments
        # si on dépasse la taille max (maxlen).
        self.history = deque(maxlen=Config.MAX_HISTORY_TURNS)

    def process_turn(self, text: str, speakers: list) -> str:
        """
        Prend le brut (texte + liste speakers) et retourne une ligne formatée.
        Met à jour l'historique.
        """
        # 1. Identification du locuteur
        speaker_name = self._resolve_speaker(speakers)

        # 2. Nettoyage basique du texte
        clean_text = text.strip()

        # 3. Création de l'entrée formatée
        formatted_line = f"{speaker_name}: {clean_text}"

        # 4. Ajout à l'historique
        self.history.append(formatted_line)

        return formatted_line

    def _resolve_speaker(self, speakers: list) -> str:
        """
        Logique pour déterminer le nom à afficher.
        """
        # Cas 1: Aucun speaker détecté ou liste vide -> Default (ou on reprend le dernier ?)
        if not speakers or speakers == ['?']:
            return Config.DEFAULT_SPEAKER

        # Cas 2: On prend le premier speaker détecté (souvent le principal dans une phrase)
        # Pyannote peut en trouver plusieurs si chevauchement.
        raw_speaker = speakers[0]

        # Mapping vers un nom réel (défini dans Config)
        return Config.SPEAKER_MAPPING.get(raw_speaker, raw_speaker)

    def get_context_string(self) -> str:
        """
        Retourne tout l'historique sous forme d'une seule string.
        Prêt à être envoyé au prompt du LLM.
        """
        return "\n".join(self.history)