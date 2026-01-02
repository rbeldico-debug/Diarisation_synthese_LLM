import re


class TextSanitizer:
    """
    Filtre les hallucinations connues de Whisper et le bruit de fond.
    Ne modifie PAS le contenu sémantique (pas de remplacement).
    """

    # Liste des phrases parasites fréquentes de Whisper
    HALLUCINATIONS = [
        r"(?i)sous-titrage st'?\s*501",
        r"(?i)sous-titres? réalisé",
        r"(?i)amara\.org",
        r"(?i)téléchargé par",
        r"(?i)sous-titres? par",
        r"(?i)abonnez-vous",
        r"(?i)suivez-nous",
        r"(?i)transcrit par",
        r"(?i)traduit par"
    ]

    @staticmethod
    def is_valid(text: str) -> bool:
        """Retourne False si le texte est du bruit ou une hallucination."""
        if not text or len(text.strip()) < 2:
            return False

        # 1. Vérification des hallucinations connues
        for pattern in TextSanitizer.HALLUCINATIONS:
            if re.search(pattern, text):
                return False

        # 2. Répétitions suspectes (ex: "Oui oui oui oui")
        # Si le texte est long (>10 chars) mais contient moins de 2 mots uniques
        if len(text) > 10 and len(set(text.split())) < 2:
            return False

        return True