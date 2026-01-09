from collections import deque

# On définit un mapping local ou on l'ajoute dans Settings plus tard
# Pour l'instant, on hardcode ici pour éviter de toucher à settings.py
SPEAKER_MAPPING = {"SPEAKER_00": "Utilisateur", "SPEAKER_01": "Océane"}
DEFAULT_SPEAKER = "Utilisateur"


class DialogueFormatter:
    """
    Gère l'historique de la conversation.
    """

    def __init__(self, max_history=10):
        self.history = deque(maxlen=max_history)

    def process_turn(self, text: str, speakers: list) -> str:
        speaker_name = self._resolve_speaker(speakers)
        clean_text = text.strip()
        formatted_line = f"{speaker_name}: {clean_text}"
        self.history.append(formatted_line)
        return formatted_line

    @staticmethod
    def _resolve_speaker(speakers: list) -> str:
        if not speakers or speakers == ['?']:
            return DEFAULT_SPEAKER

        # On prend le premier locuteur identifié
        raw_speaker = speakers[0]
        return SPEAKER_MAPPING.get(raw_speaker, raw_speaker)

    def get_context_string(self) -> str:
        return "\n".join(self.history)