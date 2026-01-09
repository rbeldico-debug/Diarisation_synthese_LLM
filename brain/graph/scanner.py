import os
import re
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict

from core.settings import settings
from brain.graph.node import GraphNode


class VaultScanner:
    """
    Implémente ADR-019 (Phase 1 : Chargement).
    Lit le Frontmatter et les Wikilinks pour permettre à GraphNode
    de calculer le Poids Statique (ADR-022).
    """

    LINK_PATTERN = re.compile(r'\[\[(.*?)\]\]')
    FRONTMATTER_PATTERN = re.compile(r'^---\n(.*?)\n---', re.DOTALL)

    def scan_vault(self) -> Dict[str, GraphNode]:
        nodes = {}
        vault_path = settings.OBSIDIAN_VAULT_PATH

        if not vault_path.exists():
            print(f"[Scanner] ⚠️ Dossier introuvable : {vault_path}")
            return {}

        print(f"[Scanner] 📂 Extraction des métadonnées (S, C, T)...")

        for root, _, files in os.walk(vault_path):
            for file in files:
                if file.endswith(".md"):
                    try:
                        node = self._parse_file(Path(root) / file, file)
                        if node:
                            nodes[node.filename] = node
                    except Exception:
                        pass  # On ignore silencieusement les fichiers corrompus

        return nodes

    def _parse_file(self, full_path: Path, filename: str) -> GraphNode:
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 1. Parsing YAML (Pour Récence C et Maturité T)
        meta = {}
        fm_match = self.FRONTMATTER_PATTERN.match(content)
        if fm_match:
            try:
                meta = yaml.safe_load(fm_match.group(1)) or {}
            except yaml.YAMLError:
                pass

        title = meta.get("title", filename.replace(".md", ""))
        tags = set(meta.get("tags", []))

        # Gestion Date (Récence C)
        date_updated = datetime.now()
        if "date_updated" in meta:
            d = meta["date_updated"]
            if isinstance(d, (datetime, str)):
                try:
                    if isinstance(d, str):
                        date_updated = datetime.strptime(d, settings.DATE_FORMAT)
                    else:
                        date_updated = d
                except:
                    pass

        # Poids persistant (ADR-019)
        base_weight = float(meta.get("poids", settings.DEFAULT_WEIGHT))

        # 2. Parsing Liens (Pour Structure S)
        links = set()
        raw_links = self.LINK_PATTERN.findall(content)
        for l in raw_links:
            target = l.split('|')[0]  # Gère [[Note|Alias]]
            if not target.endswith(".md"): target += ".md"
            links.add(target)

        # GraphNode calculera lui-même son _static_score dans __post_init__
        return GraphNode(
            full_path=full_path,
            filename=filename,
            uid=str(meta.get("uid", "")),
            title=title,
            tags=tags,
            links=links,
            base_weight=base_weight,
            date_updated=date_updated
        )