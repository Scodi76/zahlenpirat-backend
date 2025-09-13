function generateRandomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function generateTasks(count, operator, klasse) {
  const tasks = [];

  for (let i = 0; i < count; i++) {
    let a, b, frage, loesung;

    // Zahlenbereich nach Klassenstufe
    let max = 100;
    if (klasse === 1) max = 20;
    if (klasse === 2) max = 50;

    a = generateRandomInt(1, max);
    b = generateRandomInt(1, max);

    switch (operator) {
      case "+":
        frage = `${a} + ${b} = ?`;
        loesung = a + b;
        break;
      case "-":
        if (b > a) [a, b] = [b, a]; // keine negativen Ergebnisse
        frage = `${a} - ${b} = ?`;
        loesung = a - b;
        break;
      case "×":
      case "*":
        frage = `${a} × ${b} = ?`;
        loesung = a * b;
        break;
      case "÷":
      case "/":
        loesung = generateRandomInt(2, 12);
        b = generateRandomInt(2, 12);
        a = loesung * b; // garantiert teilbar
        frage = `${a} ÷ ${b} = ?`;
        break;
      default:
        frage = "Ungültiger Operator";
        loesung = 0;
    }

    // Antwortmöglichkeiten generieren
    const wahlAntworten = new Set();
    wahlAntworten.add(loesung.toString());

    while (wahlAntworten.size < 4) {
      let fake = loesung + generateRandomInt(-10, 10);
      if (fake < 0) fake = Math.abs(fake); // keine negativen Zahlen
      if (fake !== loesung) {
        wahlAntworten.add(fake.toString());
      }
    }

    tasks.push({
      id: `t${i + 1}`,
      typ: "rechnung",
      frage,
      wahlAntworten: Array.from(wahlAntworten).sort(() => Math.random() - 0.5), // Antworten mischen
      korrekteLoesung: loesung.toString(),
      freieAntwort: true,
      metadaten: {
        klasse,
        operatoren: [operator],
        kategorie: 1,
        schwierigkeit: "Einfach"
      }
    });
  }

  return tasks;
}

module.exports = { generateTasks, generateRandomInt };
