import os
from pathlib import Path

# === CONFIGURATION ===

# Chemin à scanner.
# "." signifie "le dossier où se trouve ce script".
# Tu peux mettre un chemin absolu si tu préfères (ex: r"C:\Projets\MonApp")
TARGET_DIR = r"C:\Users\G-i7\PycharmProjects\Diarisation_Synthese_LLM"

# Nom du fichier de sortie
OUTPUT_FILE = "structure.txt"

# 1. Dossiers ou Fichiers spécifiques à ignorer (Nom exact)
IGNORE_NAMES = {
    '.git', '.idea', '__pycache__', 'venv', '.venv', 'env', 'node_modules',
    '.pytest_cache', '.DS_Store', 'structure.txt', 'test_vault', 'test_segment', 'logs'
}

# 2. Extensions de fichiers à ignorer (ex: images, binaires, logs)
IGNORE_EXTENSIONS = {
    '.pyc', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg',  # Images
    '.exe', '.dll', '.so', '.o',  # Binaires
    '.log', '.tmp', '.zip', '.tar', '.gz', '.md'  # Divers
}

# Style visuel
# True  = Arbre (│ ├──) -> Joli pour l'humain
# False = Indentation   -> Économe pour le LLM
USE_ASCII_ART = True


def generate_structure(root_path, output_path, use_art=True):
    """Orchestre la création de la map."""

    # Nettoyage du chemin cible
    root = Path(root_path.strip('"').strip("'"))
    # Résolution du chemin du script actuel pour l'auto-exclusion
    current_script = Path(__file__).resolve()

    if not root.exists():
        print(f"Erreur : Le dossier '{root}' n'existe pas.")
        return

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"Project Root: {root.name}/\n")

        if use_art:
            _write_tree_art(f, root, current_script)
        else:
            _write_tree_simple(f, root, current_script)

    print(f"Succès : Structure générée dans '{output_path}'")


def _should_ignore(path, current_script_path):
    """
    Logique centrale de filtrage.
    Retourne True si le fichier/dossier doit être ignoré.
    """
    # 1. Auto-exclusion : Si le chemin est celui de ce script
    if path.resolve() == current_script_path:
        return True

    # 2. Exclusion par nom exact (dossiers ou fichiers spécifiques)
    if path.name in IGNORE_NAMES:
        return True

    # 3. Exclusion par extension (si c'est un fichier)
    if path.is_file() and path.suffix.lower() in IGNORE_EXTENSIONS:
        return True

    return False


def _write_tree_art(file_obj, directory, current_script, prefix=""):
    """Génère l'arbre visuel."""
    # Filtrage et Tri
    items = []
    try:
        for p in directory.iterdir():
            if not _should_ignore(p, current_script):
                items.append(p)
    except PermissionError:
        return  # Ignore les dossiers sans permission

    # On trie : Dossiers d'abord, puis ordre alphabétique
    items.sort(key=lambda p: (p.is_file(), p.name.lower()))

    count = len(items)
    for index, item in enumerate(items):
        is_last = (index == count - 1)
        connector = "└── " if is_last else "├── "

        file_obj.write(f"{prefix}{connector}{item.name}")
        if item.is_dir():
            file_obj.write("/")
        file_obj.write("\n")

        if item.is_dir():
            extension = "    " if is_last else "│   "
            _write_tree_art(file_obj, item, current_script, prefix + extension)


def _write_tree_simple(file_obj, directory, current_script, indent=0):
    """Génère l'arbre économe en tokens."""
    items = []
    try:
        for p in directory.iterdir():
            if not _should_ignore(p, current_script):
                items.append(p)
    except PermissionError:
        return

    items.sort(key=lambda p: (p.is_file(), p.name.lower()))

    indent_str = "  " * indent

    for item in items:
        # Prefix 'D' pour Dossier, '-' pour Fichier (aide le LLM à distinguer)
        prefix = "- " if item.is_file() else "D "
        file_obj.write(f"{indent_str}{prefix}{item.name}")
        if item.is_dir():
            file_obj.write("/")
        file_obj.write("\n")

        if item.is_dir():
            _write_tree_simple(file_obj, item, current_script, indent + 1)


if __name__ == "__main__":
    # Définition de la cible et de la sortie
    target = Path(TARGET_DIR)

    # Si TARGET_DIR est ".", on prend le dossier courant
    if str(target) == ".":
        target = Path.cwd()

    # Le fichier de sortie est créé dans le dossier racine du projet scanné
    output = target / OUTPUT_FILE

    generate_structure(str(target), output, use_art=USE_ASCII_ART)