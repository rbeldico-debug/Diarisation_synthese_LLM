from datetime import datetime
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.console import Console
from rich.text import Text
from rich.progress import BarColumn, Progress, TextColumn


class TUIManager:
    def __init__(self):
        self.console = Console()
        self.layout = Layout()

        # Division de l'écran : Haut (Header), Milieu (Split), Bas (Footer)
        self.layout.split(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=3)
        )

        # Division du milieu : Gauche (Logs) / Droite (Cerveau)
        self.layout["main"].split_row(
            Layout(name="logs", ratio=1),
            Layout(name="brain", ratio=1)
        )

        self.log_history = []
        self.max_logs = 30

    def get_layout(self, brain_data: list, last_logs: list, status_info: str):
        self._update_header(status_info)
        self._update_logs(last_logs)
        self._update_brain(brain_data)
        self._update_footer()
        return self.layout

    def _update_header(self, status):
        grid = Table.grid(expand=True)
        grid.add_column(justify="left", ratio=1)
        grid.add_column(justify="right")
        grid.add_row(
            "[b cyan]🌊 OCÉANE v2.5[/b cyan] | [yellow]Système Cognitif Distribué[/yellow]",
            f"[white]{datetime.now().strftime('%H:%M:%S')}[/white]"
        )
        self.layout["header"].update(Panel(grid, style="blue"))

    def _update_logs(self, new_logs):
        # new_logs est une liste de tuples (source, message, style)
        for log in new_logs:
            timestamp = datetime.now().strftime("%H:%M:%S")
            src, msg, style = log
            self.log_history.append(f"[{style}][{timestamp}] {src}: {msg}[/{style}]")

        # Garder seulement les derniers
        if len(self.log_history) > self.max_logs:
            self.log_history = self.log_history[-self.max_logs:]

        content = "\n".join(self.log_history)
        self.layout["logs"].update(Panel(content, title="📜 Flux d'Événements", border_style="green"))

    def _update_brain(self, nodes_data):
        """
        nodes_data: Liste de dicts {'name': str, 'weight': float, 'activation': float, 'ignited': bool}
        """
        table = Table(expand=True, border_style="dim")
        table.add_column("État", justify="center", width=4)
        table.add_column("Nœud (Concept)", ratio=1)
        table.add_column("Poids", justify="right")
        table.add_column("Activation", ratio=1)

        if not nodes_data:
            table.add_row("💤", "Cerveau au repos...", "", "")

        for node in nodes_data:
            # Icône et Style
            icon = "🔥" if node['ignited'] else "🟢"
            style = "bold red" if node['ignited'] else "green"

            # Barre de chargement simulée
            bar_length = 10
            filled = int((node['activation'] / 50.0) * bar_length)
            filled = min(filled, bar_length)  # Cap
            bar = "█" * filled + "░" * (bar_length - filled)

            table.add_row(
                icon,
                f"[{style}]{node['name']}[/{style}]",
                f"{node['weight']:.1f}",
                f"[{style}]{bar}[/{style}] ({node['activation']:.1f})"
            )

        self.layout["brain"].update(Panel(table, title="🧠 Activité Neuronale (Temps Réel)", border_style="magenta"))

    def _update_footer(self):
        text = Text("Appuyez sur Ctrl+C pour arrêter | Logs sauvegardés dans /logs", justify="center", style="dim")
        self.layout["footer"].update(Panel(text))