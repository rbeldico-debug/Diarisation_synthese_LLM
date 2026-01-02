from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import json
import collections

from config import Config

app = FastAPI()

# Configuration des templates
# Assurez-vous d'avoir créé le dossier "templates" et mis "dashboard.html" dedans
templates = Jinja2Templates(directory="templates")


def read_jsonl_tail(filepath: Path, n=50):
    """Lit les N dernières lignes d'un JSONL de manière robuste."""
    if not filepath.exists(): return []
    try:
        data = []
        with open(filepath, "r", encoding="utf-8") as f:
            # On utilise deque pour ne lire que les dernières lignes efficacement
            lines = collections.deque(f, maxlen=n)
            for line in lines:
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return data
    except Exception as e:
        print(f"Erreur lecture logs: {e}")
        return []


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Sert la page HTML principale."""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/api/brain")
async def get_brain():
    """Renvoie l'état du graphe (snapshot généré par main.py)."""
    path = Config.LOGS_DIR / "brain_activity.json"
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"nodes": []}


@app.get("/api/logs")
async def get_logs():
    """Renvoie les logs système (Journal) et les traces LLM."""
    # On lit les logs
    journal = read_jsonl_tail(Config.JOURNAL_PATH, n=30)
    llm_traces = read_jsonl_tail(Config.LOGS_DIR / "llm_trace.jsonl", n=10)

    # On renverse les listes pour avoir le plus récent en haut dans l'UI
    return {
        "journal": list(reversed(journal)),
        "llm": list(reversed(llm_traces))
    }


if __name__ == "__main__":
    import uvicorn

    # PORT 8002 pour éviter le conflit avec Whisper (8000) et Chroma (8001)
    PORT = 8002
    print(f"🚀 Dashboard accessible sur : http://localhost:{PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)