from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
import random, json, os
from datetime import datetime
from connector_routes import router as connector_router
scores_memory = []

app = FastAPI(title="Zahlen-Pirat Backend")
app.include_router(connector_router)

DB_FILE = "scores.json"

# Hilfsfunktionen für Scores
def load_scores():
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_scores(scores):
    with open(DB_FILE, "w") as f:
        json.dump(scores, f, indent=2)

# -----------------------------
# Modelle
# -----------------------------
class Task(BaseModel):
    id: str
    frage: str
    korrekteLoesung: str
    operator: str

class TaskRequest(BaseModel):
    operatoren: List[str]
    limit: int = 10

class AnswerRequest(BaseModel):
    sessionId: str
    taskId: str
    antwort: str
    dauerSek: int
    korrekteLoesung: str
    spieler: str
    operator: str

from typing import Optional, List
from pydantic import BaseModel

class SaveRequest(BaseModel):
    spieler: str
    punkte: int
    klasse: Optional[int] = 0
    modus: Optional[str] = "Test"
    operatoren: Optional[List[str]] = []
    schwierigkeit: Optional[str] = "Einfach"
    zahlenauswahl: Optional[str] = "1-20"
    kategorie: Optional[int] = 1
    dauer: Optional[str] = "-"
    autosave: Optional[bool] = True




class StartRequest(BaseModel):
    modus: Optional[str] = "Test"
    timerSek: Optional[int] = 300   # Standard: 5 Minuten
    anzahlAufgaben: Optional[int] = 10

# -----------------------------
# Endpoints
# -----------------------------

# Healthcheck
@app.get("/health")
def health():
    return {"status": "ok"}

# Spiel starten
@app.post("/test/start")
def start_test(req: StartRequest):
    return {
        "sessionId": "s1",   # später evtl. UUID verwenden
        "modus": req.modus,
        "timerSek": req.timerSek,
        "anzahlAufgaben": req.anzahlAufgaben
    }

# Aufgaben erzeugen
@app.post("/get/tasks")
def get_tasks(req: TaskRequest):
    operatoren = req.operatoren
    limit = req.limit
    tasks = []
    for i in range(limit):
        a, b = random.randint(1, 10), random.randint(1, 10)
        if "+" in operatoren:
            frage, loesung, op = f"{a} + {b}", str(a + b), "+"
        elif "-" in operatoren:
            frage, loesung, op = f"{a} - {b}", str(a - b), "-"
        elif "×" in operatoren:
            frage, loesung, op = f"{a} × {b}", str(a * b), "×"
        elif "÷" in operatoren and b != 0:
            frage, loesung, op = f"{a} ÷ {b}", str(a // b), "÷"
        else:
            continue
        tasks.append(Task(id=str(i+1), frage=frage, korrekteLoesung=loesung, operator=op))
    return tasks

# Antwort prüfen
@app.post("/test/answer")
def post_answer(req: AnswerRequest):
    korrekt = req.antwort == req.korrekteLoesung
    punkte_delta = 10 if korrekt else -5
    gesamtpunkte = max(0, punkte_delta)  # TODO: Aufsummieren wenn du Session-Punkte willst

    # Score laden und erweitern
    scores = load_scores()
    entry = {
        "spieler": req.spieler,  # ✅ kommt jetzt direkt vom Request
        "punkte": gesamtpunkte,
        "klasse": 3,
        "modus": "Test",
        "operatoren": [req.operator],
        "schwierigkeit": "Einfach",
        "zahlenauswahl": "1-20",
        "kategorie": 1,
        "dauer": f"{req.dauerSek} Sek",
        "autosave": True,
        "datum": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    scores.append(entry)
    save_scores(scores)

    return {
        "korrekt": korrekt,
        "korrekteLoesung": req.korrekteLoesung,
        "erklaerung": f"Die richtige Lösung war {req.korrekteLoesung}.",
        "punkteDelta": punkte_delta,
        "gesamtpunkte": gesamtpunkte
    }


# Punkte speichern (dauerhaft in scores.json)
@app.post("/save")
def save_score(req: SaveRequest):
    try:
        # Vorhandene Scores laden
        scores = load_scores()
        if not isinstance(scores, list):
            scores = []  # Fallback falls Datei kein Array ist
    except Exception as e:
        print("⚠️ Fehler beim Laden von scores.json in /save:", e)
        scores = []

    # Neuen Eintrag vorbereiten
    entry = req.dict()
    entry["datum"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Eintrag anhängen
    scores.append(entry)

    try:
        save_scores(scores)  # Datei überschreiben
    except Exception as e:
        print("⚠️ Fehler beim Speichern von scores.json:", e)
        return {"message": "Fehler beim Speichern", "error": str(e)}

    return {"message": "Saved", "score": entry}



# Punkte laden (dauerhaft aus scores.json)
@app.get("/load")
def load_scores_for_player(spieler: str):
    try:
        scores = load_scores()
    except Exception as e:
        print("⚠️ Fehler beim Laden von scores.json in /load:", e)
        return []

    # Alle Scores vom Spieler (Case-insensitive)
    matching_scores = [
        s for s in scores
        if "spieler" in s and isinstance(s["spieler"], str) and s["spieler"].lower() == spieler.lower()
    ]

    # Nur die letzten 20 zurückgeben
    return matching_scores[-20:]

# Rangliste (dauerhaft aus scores.json)
@app.get("/leaderboard")
def leaderboard():
    scores = load_scores()
    sorted_scores = sorted(scores, key=lambda x: x["punkte"], reverse=True)
    for idx, s in enumerate(sorted_scores, start=1):
        s["rang"] = idx
    return sorted_scores
