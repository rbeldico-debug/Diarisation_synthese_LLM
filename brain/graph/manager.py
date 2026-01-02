import json
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

        # Phase de "Cristallisation" : On sauvegarde le poids statique calculé
        print(f"[Graph] 🧮 Cristallisation des poids initiaux dans les fichiers MD...")
        updated_count = 0
        for node in self.nodes.values():
            # Si le poids calculé diffère significativement de celui stocké, on met à jour
            current_calc = node._static_score  # On prend le score statique pur
            if abs(node.base_weight - current_calc) > 0.5:
                try:
                    # On met à jour la valeur en RAM pour qu'elle soit synchro
                    node.base_weight = current_calc
                    self._update_node_file(node, update_weight=True)
                    updated_count += 1
                except Exception:
                    pass

        if updated_count > 0:
            print(f"[Graph] 💾 {updated_count} notes mises à jour (Poids calibrés).")

    def propagate_activation(self):
        """
        ADR-022 (Top-Down): Les nœuds actifs transmettent de l'énergie à leurs voisins.
        """
        transfers = {}

        for source_node in self.nodes.values():
            if source_node.activation > 0.1:
                energy_packet = source_node.activation * Config.PROPAGATION_RATE
                for target_filename in source_node.links:
                    if target_filename in self.nodes:
                        if target_filename not in transfers:
                            transfers[target_filename] = 0.0
                        transfers[target_filename] += energy_packet

        count = 0
        for target_filename, amount in transfers.items():
            self.nodes[target_filename].stimulate(amount)
            count += 1

    def save_state(self):
        print(f"[Graph] 💾 Sauvegarde de l'état mental...")
        count = 0
        for node in self.nodes.values():
            if node.activation > 0.1 or node.consecutive_activations > 0:
                if node.full_path and node.full_path.exists():
                    try:
                        self._update_node_file(node, update_weight=False)
                        count += 1
                    except Exception as e:
                        print(f"[Graph] ❌ Erreur sauvegarde {node.filename}: {e}")

        if count > 0:
            print(f"[Graph] ✅ {count} notes mises à jour (Activité).")

    def _update_node_file(self, node: GraphNode, update_weight: bool = False):
        if not node.full_path or not node.full_path.exists():
            return

        with open(node.full_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        new_lines = []
        in_yaml = False
        yaml_start = False
        new_date_str = datetime.now().strftime(Config.DATE_FORMAT)
        weight_written = False

        for line in lines:
            stripped = line.strip()
            if stripped == "---":
                if not yaml_start:
                    yaml_start = True
                    in_yaml = True
                else:
                    if update_weight and not weight_written and in_yaml:
                        new_lines.append(f"poids: {int(node.base_weight)}\n")
                    in_yaml = False
                new_lines.append(line)
                continue

            if in_yaml:
                if stripped.startswith("date_updated:"):
                    new_lines.append(f"date_updated: {new_date_str}\n")
                    continue
                if stripped.startswith("poids:") and update_weight:
                    new_lines.append(f"poids: {int(node.base_weight)}\n")
                    weight_written = True
                    continue

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
            return GraphNode(
                full_path=path,
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
            full_path=path,
            filename=path.name,
            uid=meta.get("uid", ""),
            title=path.stem,
            tags=set(meta.get("tags", [])),
            links=normalized_links,
            base_weight=weight,
            date_updated=self._parse_date(meta.get("date_updated"))
        )

    def inject_stimulus(self, text: str, intent_tags: str):
        text_lower = text.lower()
        detected_tags = set(re.findall(r'\[(.*?)\]', intent_tags))
        stimulated_count = 0

        for node in self.nodes.values():
            boost = 0.0
            if node.title.lower() in text_lower:
                boost += 15.0
            common_tags = node.tags.intersection(detected_tags)
            if common_tags:
                boost += 3.0 * len(common_tags)
            if boost > 0:
                node.stimulate(boost)
                stimulated_count += 1

    def export_activity_snapshot(self, filepath: Path, top_k: int = 20):
        """Exporte l'état des nœuds pour le monitoring web."""
        all_nodes = list(self.nodes.values())

        # Tri : D'abord par Activation, puis par Poids
        sorted_nodes = sorted(
            all_nodes,
            key=lambda x: (x.activation, x.get_current_weight()),
            reverse=True
        )[:top_k]

        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "nodes": [
                {
                    "title": n.title,
                    "activation": round(n.activation, 2),
                    "total_weight": round(n.get_current_weight(), 2),
                    "links": len(n.links),
                    "fatigue": n.consecutive_activations
                }
                for n in sorted_nodes
            ]
        }

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, ensure_ascii=False)
        except Exception as e:
            print(f"[Graph] ⚠️ Erreur export snapshot : {e}")

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