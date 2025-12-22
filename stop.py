from pathlib import Path
import os

# On définit le chemin (doit être le même que dans config.py)
stop_file = Path("logs/oceane.stop")

def signal_stop():
    stop_file.parent.mkdir(exist_ok=True)
    stop_file.touch()
    print("\n[Signal] 🛑 Commande d'arrêt envoyée à Océane.")
    print("[Signal] Elle s'éteindra après sa prochaine vérification (max 1s).")

if __name__ == "__main__":
    signal_stop()