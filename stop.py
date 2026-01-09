from pathlib import Path
from core.settings import settings


def signal_stop():
    # On utilise le chemin défini dans les settings
    stop_file = settings.LOGS_DIR / "oceane.stop"

    stop_file.parent.mkdir(exist_ok=True, parents=True)
    stop_file.touch()
    print(f"\n[Signal] 🛑 Commande d'arrêt envoyée : {stop_file}")
    print("[Signal] Elle s'éteindra après sa prochaine boucle (max 1s).")


if __name__ == "__main__":
    signal_stop()