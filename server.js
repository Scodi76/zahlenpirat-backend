const express = require("express");
const { generateTasks } = require("./generateTasks");

const app = express();

// Render gibt den Port über process.env.PORT vor, lokal nutzen wir 3000
const PORT = process.env.PORT || 3000;

app.get("/tasks", (req, res) => {
  const operatorParam = (req.query.operator || "+").trim();
  let operators = operatorParam
    .split(",")
    .map(op => op.trim())
    .filter(Boolean);

  // Falls keine gültigen Operatoren gefunden → Standard "+"
  if (operators.length === 0) {
    operators = ["+"];
  }

  const klasse = parseInt(req.query.klasse) || 3;
  const count = parseInt(req.query.count) || 10;

  // Für jede Aufgabe zufällig einen Operator aus der Liste wählen
  const tasks = Array.from({ length: count }, () => {
    const op = operators[Math.floor(Math.random() * operators.length)];
    return generateTasks(1, op, klasse)[0];
  });

  res.json(tasks);
});

app.listen(PORT, () => {
  console.log(`✅ Server läuft auf Port ${PORT}`);
});
