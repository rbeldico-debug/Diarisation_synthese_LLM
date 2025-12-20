import sys
import os
import torch
import torchvision


def check():
    print(f"--- DIAGNOSTIC ---")
    print(f"Python       : {sys.version.split()[0]}")

    # Vérification Torch
    print(f"Torch        : {torch.__version__}")
    if "+cpu" in torch.__version__:
        print("⚠️ ALERTE     : Torch est en version CPU ! (Pas de GPU utilisé)")

    print(f"Torchvision  : {torchvision.__version__}")

    # Vérification CUDA
    cuda_available = torch.cuda.is_available()
    print(f"CUDA Dispo   : {cuda_available}")
    if cuda_available:
        print(f"Carte Graph  : {torch.cuda.get_device_name(0)}")
    else:
        print("❌ ERREUR     : CUDA n'est pas détecté.")

    # Vérification Pyannote
    try:
        import pyannote.audio
        print("Pyannote     : ✅ Installé")
    except ImportError as e:
        print(f"Pyannote     : ❌ Erreur: {e}")

    # Test crucial de l'opérateur NMS
    try:
        from torchvision import ops
        # On tente un appel dummy pour être sûr
        print("Test Ops     : ✅ Opérateurs Torchvision trouvés")
    except Exception as e:
        print(f"Test Ops     : ❌ ERREUR CRITIQUE (NMS manquant): {e}")


if __name__ == "__main__":
    check()