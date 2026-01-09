from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from pathlib import Path
import json
import collections

from core.settings import settings

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Modèle pour l'input texte
class TextInput(BaseModel):
    text: str

# --- Helpers Logs ---
def get_latest_journal():
    try:
        files = list(settings.LOGS_DIR.glob("journal_*.jsonl"))
        if not files: return None
        return max(files, key=lambda f: f.stat().st_mtime)
    except Exception: return None

def read_jsonl_tail(filepath: Path, n=50):
    if not filepath or not filepath.exists(): return []
    try:
        data = []
        with open(filepath, "r", encoding="utf-8") as f:
            lines = collections.deque(f, maxlen=n)
            for line in lines:
                try: data.append(json.loads(line))
                except: continue
        return data
    except Exception: return []

# --- Endpoints API ---

@app.post("/api/input/text")
async def send_text(payload: TextInput):
    """Reçoit du texte depuis le Web et l'envoie à l'Orchestrateur."""
    if hasattr(app.state, "input_queue"):
        # On met un tuple ("text", contenu)
        app.state.input_queue.put(("text", payload.text))
        return {"status": "ok"}
    raise HTTPException(status_code=503, detail="Queue non connectée")

@app.post("/api/control/ptt/{action}")
async def control_ptt(action: str):
    """Contrôle le micro : action = 'start' ou 'stop'."""
    if hasattr(app.state, "control_queue"):
        if action in ["start", "stop"]:
            app.state.control_queue.put(("ptt", action))
            return {"status": f"Micro {action}"}
    raise HTTPException(status_code=503, detail="Control Queue non connectée")

# --- Endpoints Affichage ---

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/api/brain")
async def get_brain():
    path = settings.LOGS_DIR / "brain_activity.json"
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f: return json.load(f)
        except: pass
    return {"nodes": []}

@app.get("/api/logs")
async def get_logs():
    journal_path = get_latest_journal()
    journal = read_jsonl_tail(journal_path, n=30)
    llm = read_jsonl_tail(settings.LOGS_DIR / "llm_trace.jsonl", n=10)
    return {"journal": list(reversed(journal)), "llm": list(reversed(llm))}

# Note: Le bloc if __name__ == "__main__" n'est plus utile car lancé par main.py