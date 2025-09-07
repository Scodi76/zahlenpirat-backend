const express = require("express");
const { generateTasks } = require("./generateTasks");
const fs = require("fs");

const app = express();
app.use(express.json());

// Speicher für Sessions (im RAM)
let sessions = {};

// Speicher für Scores (persistiert in Datei)
const SCORE_FILE = "scores.json";
let scores = {};

// Lade Scores aus Datei beim Start
if (fs.existsSync(SCORE_FILE)) {
  try {
    scores = JSON.parse(fs.readFileSync(SCORE_FILE, "utf-8"));
  } catch (err) {
    console.error("Fehler beim Laden von scores.json:", err);
    scores = {};
  }
}

app.get("/tasks", (req, res) => {
  const operatorParam = (req.query.operator || "+").trim();
  let operators = operatorParam.split(",").map(op => op.trim()).filter(Boolean);
  if (operators.length === 0) operators = ["+"];

  const klasse = parseInt(req.query.klasse) || 3;
  const count = parseInt(req.query.count) || 10;

  const tasks = Array.from({ length: count }, () => {
    const op = operators[Math.floor(Math.random() * operators.length)];
    return generateTasks(1, op, klasse)[0];
  });

  res.json(tasks);
});

// 1️⃣ Session starten
app.post("/test/start", (req, res) => {
  const { modus = "Test", timerSek = 300, anzahlAufgaben = 10, klasse = 3, operator = "+" } = req.body;

  const tasks = Array.from({ length: anzahlAufgaben }, () => {
    return generateTasks(1, operator, klasse)[0];
  });

  const sessionId = "s" + Date.now();
  sessions[sessionId] = {
    modus,
    timerSek,
    tasks,
    aktuelleNummer: 0,
    punkte: 0
  };

  res.json({
    sessionId,
    modus,
    timerSek,
    anzahlAufgaben
  });
});


// 2️⃣ Antwort prüfen
app.post("/test/answer", (req, res) => {
  const { sessionId, taskId, antwort, dauerSek = 0 } = req.body;
  const session = sessions[sessionId];

  if (!session) {
    return res.status(404).json({ message: "Session not found" });
  }

  const task = session.tasks.find(t => t.id === taskId);
  if (!task) {
    return res.status(404).json({ message: "Task not found" });
  }

  const korrekt = antwort == task.korrekteLoesung;
  if (korrekt) session.punkte += 10;

  res.json({
    korrekt,
    korrekteLoesung: task.korrekteLoesung,
    erklaerung: `${task.frage} ergibt ${task.korrekteLoesung}`,
    punkteDelta: korrekt ? 10 : 0,
    gesamtpunkte: session.punkte
  });
});

// 3️⃣ Punkte speichern
app.post("/save", (req, res) => {
  const { spieler, punkte, klasse = 3, modus = "Test" } = req.body;
  if (!spieler) {
    return res.status(400).json({ message: "Spielername fehlt" });
  }

  // Speichern im Speicher
  scores[spieler] = {
    spieler,
    punkte,
    klasse,
    modus,
    datum: new Date().toISOString()
  };

  // Persistieren in Datei
  fs.writeFileSync(SCORE_FILE, JSON.stringify(scores, null, 2));

  res.json({ status: "saved" });
});

// 4️⃣ Punktestand laden
app.get("/load", (req, res) => {
  const { spieler } = req.query;
  if (!spieler || !scores[spieler]) {
    return res.status(404).json({ message: "Spieler nicht gefunden" });
  }
  res.json(scores[spieler]);
});

// 5️⃣ Leaderboard
app.get("/leaderboard", (req, res) => {
  const limit = parseInt(req.query.limit) || 10;

  const sorted = Object.values(scores)
    .sort((a, b) => b.punkte - a.punkte)
    .slice(0, limit)
    .map((s, i) => ({
      ...s,
      rang: i + 1
    }));

  res.json(sorted);
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`✅ Server läuft auf Port ${PORT}`);
});
