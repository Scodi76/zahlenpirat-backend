function generateRandomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function getNumberRangeForClass(klasse) {
  switch (klasse) {
    case 1: return [1, 20];
    case 2: return [1, 50];
    case 3: return [1, 100];
    case 4: return [10, 500];
    case 5: return [50, 1000];
    case 6: return [100, 5000];
    default: return [1, 50];
  }
}

function generateTask(id, operator, klasse) {
  const [min, max] = getNumberRangeForClass(klasse);
  let a = generateRandomInt(min, max);
  let b = generateRandomInt(min, max);
  let frage, loesung;

  switch (operator) {
    case "+":
      frage = `${a} + ${b} = ?`;
      loesung = a + b;
      break;
    case "-":
      if (b > a) [a, b] = [b, a];
      frage = `${a} - ${b} = ?`;
      loesung = a - b;
      break;
    case "×":
      frage = `${a} × ${b} = ?`;
      loesung = a * b;
      break;
    case "÷":
      loesung = generateRandomInt(2, 12);
      b = generateRandomInt(2, 12);
      a = loesung * b;
      frage = `${a} ÷ ${b} = ?`;
      break;
  }

  const wrongAnswers = [
    loesung + generateRandomInt(1, 5),
    loesung - generateRandomInt(1, 5),
    loesung + generateRandomInt(6, 10),
  ];
  const wahlAntworten = [loesung, ...wrongAnswers].sort(() => Math.random() - 0.5);

  return {
    id: `t${id}`,
    typ: "rechnung",
    frage,
    wahlAntworten: wahlAntworten.map(String),
    korrekteLoesung: String(loesung),
    freieAntwort: true,
    metadaten: {
      klasse,
      operatoren: [operator],
      kategorie: 1,
      schwierigkeit: "Einfach"
    }
  };
}

function generateTasks(count, operator, klasse) {
  return Array.from({ length: count }, (_, i) => generateTask(i + 1, operator, klasse));
}

module.exports = { generateTasks };
