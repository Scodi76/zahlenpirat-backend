const express = require("express");
const { generateTasks } = require("./generateTasks");

const app = express();
const PORT = 3000;

app.get("/tasks", (req, res) => {
  // Operatoren einlesen (z. B. "+,-,×,÷")
  const operatorParam = (req.query.operator || "+").trim();
  const operators = operatorParam.split(","); // wird zu Array ["+", "-", "×", "÷"]

  const klasse = parseInt(req.query.klasse) || 3;
  const count = parseInt(req.query.count) || 10;

  // Für jede Aufgabe zufällig einen Operator aus der Liste wählen
  const tasks = Array.from({ length: count }, (_, i) => {
    const op = operators[Math.floor(Math.random() * operators.length)];
    return generateTasks(1, op, klasse)[0]; // eine Aufgabe generieren
  });

  res.json(tasks);
});

app.listen(PORT, () => {
  console.log(`Server läuft auf http://localhost:${PORT}`);
});
