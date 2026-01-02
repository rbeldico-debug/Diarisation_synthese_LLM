from brain.graph.manager import GraphStateManager


def test():
    print("--- Test du GraphState & Moteur Cognitif (ADR-022) ---")
    gm = GraphStateManager()
    gm.load_state()  # Scan récursif du test_vault

    if not gm.nodes:
        print("❌ Vide.")
        return

    print(f"\n🧠 Analyse de {len(gm.nodes)} nœuds :\n")

    # On trie par "Poids Statique" décroissant pour voir les champions
    sorted_nodes = sorted(gm.nodes.values(), key=lambda x: x.get_current_weight(), reverse=True)

    print(f"{'FICHIER':<40} | {'POIDS TOTAL':<10} | {'ACTIVATION':<10} | {'LIENS'}")
    print("-" * 80)

    # Affiche le Top 10
    for node in sorted_nodes[:10]:
        w = node.get_current_weight()
        print(f"{node.filename:<40} | {w:<10.2f} | {node.activation:<10.2f} | {len(node.links)}")

    print("\n🧪 Test de Stimulation :")
    top_node = sorted_nodes[0]
    print(f"-> Stimulation de '{top_node.filename}' (+50 points)")
    top_node.stimulate(50.0)
    print(f"-> Nouveau Poids : {top_node.get_current_weight():.2f}")

    print("-> Cycle de Fatigue (Ignition)")
    top_node.register_activation()
    top_node.register_activation()  # 2 fois de suite
    print(f"-> Poids après 2 activations (Fatigue): {top_node.get_current_weight():.2f}")


if __name__ == "__main__":
    test()