import re
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime

from config import Config
from brain.graph.node import GraphNode


class GraphStateManager:
    def __init__(self):
        self.nodes: Dict[str, GraphNode] = {}
        self.vault_root = Config.OBSIDIAN_VAULT_PATH
        self.link_pattern = re.compile(r'\[\[([^|\]]+)(?:\|.*?)?')

    def load_state(self):
        print(f"[Graph] 📂 Scan récursif du coffre : {self.vault_root}")
        if not self.vault_root.exists():
            print(f"[Graph] ⚠️ Dossier introuvable : {self.vault_root}")
            return

        loaded_count = 0
        for file_path in self.vault_root.rglob("*.md"):
            if ".obsidian" in file_path.parts or ".trash" in file_path.parts:
                continue
            try:
                node = self._parse_file(file_path)
                if node:
                    self.nodes[node.filename] = node
                    loaded_count += 1
            except Exception as e:
                print(f"[Graph] ❌ Erreur lecture {file_path.name}: {e}")
        print(f"[Graph] ✅ Graphe construit : {loaded_count} nœuds actifs.")

        # [NOUVEAU] Phase de "Cristallisation"
        # On met à jour les fichiers physiques avec le poids calculé initial
        print(f"[Graph] 🧮 Cristallisation des poids initiaux...")
        updated_count = 0
        for node in self.nodes.values():
            # Le nœud vient d'être chargé, son _static_score est frais.
            # On veut que le fichier reflète ce score (arrondi).
            current_calc = node.get_current_weight()

            # On vérifie si ça vaut le coup d'écrire (éviter I/O inutile)
            # Si la différence entre le poids stocké et le calculé est > 0.1
            if abs(node.base_weight - current_calc) > 0.1:
                try:
                    self._update_node_file(node)
                    updated_count += 1
                except Exception:
                    pass

        print(f"[Graph] 💾 {updated_count} notes mises à jour avec leur poids structurel.")

    def save_state(self):
        """
        Sauvegarde l'état pertinent (Date mise à jour, Poids Statique) dans les fichiers.
        À appeler à l'arrêt du système.
        """
        print(f"[Graph] 💾 Sauvegarde de l'état mental...")
        count = 0
        for node in self.nodes.values():
            # Critère de sauvegarde :
            # 1. Le nœud a été activé pendant la session (activation > 0 ou fatigue > 0)
            # 2. OU c'est une nouvelle note (pas encore implémenté ici mais géré par Librarian)
            # if node.activation > 1.0 or node.consecutive_activations > 0: #Désactivé pour sauvegarder tous les poids.
            if node.full_path and node.full_path.exists():
                try:
                    self._update_node_file(node)
                    count += 1
                except Exception as e:
                    print(f"[Graph] ❌ Erreur sauvegarde {node.filename}: {e}")



        if count > 0:
            print(f"[Graph] ✅ {count} notes mises à jour (Activité détectée).")
        else:
            print(f"[Graph] 💤 Aucune modification structurelle à sauvegarder.")

    def _update_node_file(self, node: GraphNode):
        """Écrit physiquement dans le fichier .md (Mise à jour métadonnées uniquement)."""
        if not node.full_path or not node.full_path.exists():
            return

        with open(node.full_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        new_lines = []
        in_yaml = False

        # On met à jour la date car le nœud a été "touché" par l'esprit
        new_date_str = datetime.now().strftime(Config.DATE_FORMAT)

        for line in lines:
            if line.strip() == "---":
                in_yaml = not in_yaml
                new_lines.append(line)
                continue

            if in_yaml:
                # Mise à jour date
                if line.strip().startswith("date_updated:"):
                    new_lines.append(f"date_updated: {new_date_str}\n")
                    continue
                # (Optionnel) Mise à jour poids statique si tu veux le persister
                # if line.strip().startswith("poids:"): ...

            new_lines.append(line)

        with open(node.full_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

    def _parse_file(self, path: Path) -> Optional[GraphNode]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            return None

        yaml_match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)

        if not yaml_match:
            # Note sans YAML
            return GraphNode(
                full_path=path,  # <---
                filename=path.name,
                uid="",
                title=path.stem,
                tags=set(),
                links=set(),
                base_weight=float(Config.DEFAULT_WEIGHT),
                date_updated=datetime.now()
            )

        yaml_text = yaml_match.group(1)
        meta = self._simple_yaml_parse(yaml_text)

        body = content[yaml_match.end():]
        links = set(self.link_pattern.findall(body))
        normalized_links = {f"{link}.md" if not link.endswith(".md") else link for link in links}

        raw_weight = meta.get("poids", Config.DEFAULT_WEIGHT)
        if isinstance(raw_weight, list):
            raw_weight = raw_weight[0] if raw_weight else Config.DEFAULT_WEIGHT
        try:
            weight = float(raw_weight)
        except (ValueError, TypeError):
            weight = float(Config.DEFAULT_WEIGHT)

        return GraphNode(
            full_path=path,  # <--- Stockage du chemin
            filename=path.name,
            uid=meta.get("uid", ""),
            title=path.stem,
            tags=set(meta.get("tags", [])),
            links=normalized_links,
            base_weight=weight,
            date_updated=self._parse_date(meta.get("date_updated"))
        )

    def inject_stimulus(self, text: str, intent_tags: str):
        """
        Bottom-Up : Réaction immédiate aux mots entendus.
        Parcourt les nœuds et stimule ceux qui sont mentionnés.
        """
        text_lower = text.lower()

        # On nettoie les tags reçus du Router (ex: "[POLITIQUE] [CHAOS]")
        # Pour en faire une liste : ['POLITIQUE', 'CHAOS']
        detected_tags = set(re.findall(r'\[(.*?)\]', intent_tags))

        stimulated_count = 0

        for node in self.nodes.values():
            boost = 0.0

            # 1. Correspondance Directe (Le mot est dit)
            # Ex: Si on dit "Chaos", le nœud "Chaos.md" ou "Théorie du Chaos.md" s'allume
            if node.title.lower() in text_lower:
                boost += 15.0  # Grosse décharge (Mots-clés)
                print(f"[Réflexe] ⚡ Stimulation directe : {node.filename} (+15)")

            # 2. Correspondance Thématique (Tags)
            # Ex: Si le Router sort [POLITIQUE] et que la note est tagguée politique
            # On fait une intersection entre les tags du nœud et les tags détectés
            common_tags = node.tags.intersection(detected_tags)
            if common_tags:
                boost += 2.0 * len(common_tags)  # Petite décharge d'ambiance

            # Application
            if boost > 0:
                node.stimulate(boost)
                stimulated_count += 1

        if stimulated_count > 0:
            # Petit log pour confirmer que le système nerveux fonctionne
            pass

    # ... (Le reste : _simple_yaml_parse, _parse_date, get_node inchangé) ...
    @staticmethod
    def _simple_yaml_parse(yaml_text: str) -> Dict[str, Any]:
        data = {}
        lines = yaml_text.split('\n')
        current_list = None
        for line in lines:
            line = line.strip()
            if not line: continue
            if line.startswith("- "):
                val = line[2:].strip()
                if current_list and isinstance(data.get(current_list), list):
                    data[current_list].append(val)
                continue
            if ":" in line:
                key, val = line.split(":", 1)
                key = key.strip()
                val = val.strip()
                if not val:
                    current_list = key
                    data[key] = []
                else:
                    current_list = None
                    val = val.replace('"', '').replace("'", "")
                    if val.startswith('[') and val.endswith(']'):
                        content = val[1:-1]
                        data[key] = [x.strip() for x in content.split(',')] if content else []
                    else:
                        data[key] = val
        return data

    @staticmethod
    def _parse_date(date_str: Any) -> datetime:
        if not date_str: return datetime.now()
        try:
            return datetime.strptime(str(date_str).strip(), Config.DATE_FORMAT)
        except ValueError:
            return datetime.now()

    def get_node(self, filename: str) -> Optional[GraphNode]:
        return self.nodes.get(filename)