// save.js

// ✅ Automatische Umschaltung: lokal oder online
const BASE_URL =
  window.location.hostname === "localhost"
    ? "http://localhost:3000"
    : "https://zahlenpirat-backend.onrender.com";


// ✅ Spielstand speichern
function saveSpielstand(autosave = true) {
  if (!aktuellerSpieler || aktuellerSpieler.trim() === "") {
    zeigeText("⚠️ Kein Spielername gesetzt – Speichern nicht möglich.");
    return;
  }

  const payload = {
    spieler: aktuellerSpieler.toLowerCase(),
    punkte: aktuellerPunktestand,
    klasse: aktuelleKlasse,
    modus: aktuellerModus,
    operatoren: aktuelleOperatoren || [],
    schwierigkeit: aktuelleSchwierigkeit || "Einfach",
    zahlenauswahl: aktuelleZahlenauswahl || "1-20",
    kategorie: aktuelleKategorie || 1,
    dauer: dauer || "–",
    autosave: autosave
  };

  // ⬇️ angepasst: neuer Backend-Endpoint
  const result = callAPI(`${BASE_URL}/api/saveScore`, payload);

  if (result) {
    zeigeText(`💾 Spielstand gespeichert für ${aktuellerSpieler}! ⚓  
🏆 Punkte: ${aktuellerPunktestand}`);
  } else {
    zeigeText(`⚠️ Fehler beim Speichern! Versuche es bitte später erneut, ${aktuellerSpieler}.`);
  }
}



// ✅ Letzte Spielstände anzeigen
function zeigeLetzteSpielstaende() {
  if (!aktuellerSpieler || aktuellerSpieler.trim() === "") {
    zeigeText("⚠️ Kein Spielername angegeben.");
    return;
  }

  const saveDataList = callAPI(`${BASE_URL}/load?spieler=${aktuellerSpieler.toLowerCase()}`);

  if (!saveDataList || saveDataList.length === 0) {
    zeigeText(`❌ Kein Speicherstand für ${aktuellerSpieler} gefunden, arrr! ⚓`);
  } else {
    let ausgabe = `📜 Letzte Spielstände für ${aktuellerSpieler}:\n\n`;

    saveDataList
      .slice()
      .reverse()
      .forEach((entry, index) => {
        let gespeicherteDauer = entry.dauer || "–";
        if (gespeicherteDauer && !gespeicherteDauer.includes("Min")) {
          gespeicherteDauer = `${gespeicherteDauer} Min`;
        }

        ausgabe += `#${index + 1} – ${entry.modus || "?"} | Punkte: ${entry.punkte} | Dauer: ${gespeicherteDauer} | Kategorie: ${entry.kategorie || "?"} | Autosave: ${entry.autosave ? "Ja" : "Nein"}\n`;
      });

    zeigeText(ausgabe);
  }
}


// ✅ Letzten Spielstand laden
function ladeLetztenSpielstand() {
  if (!aktuellerSpieler || aktuellerSpieler.trim() === "") {
    zeigeText("⚠️ Kein Spielername angegeben.");
    return;
  }

  const saveDataList = callAPI(`${BASE_URL}/load?spieler=${aktuellerSpieler.toLowerCase()}`);

  if (!saveDataList || saveDataList.length === 0) {
    zeigeText(`❌ Kein Speicherstand für ${aktuellerSpieler} gefunden, arrr! ⚓`);
    return;
  }

  const letzterStand = saveDataList[saveDataList.length - 1];

  aktuelleKlasse = letzterStand.klasse;
  aktuellerModus = letzterStand.modus;
  aktuelleOperatoren = letzterStand.operatoren;
  aktuelleSchwierigkeit = letzterStand.schwierigkeit;
  aktuelleZahlenauswahl = letzterStand.zahlenauswahl;
  aktuelleKategorie = letzterStand.kategorie;
  aktuellerPunktestand = letzterStand.punkte;

  let gespeicherteDauer = letzterStand.dauer || "–";
  if (gespeicherteDauer && !gespeicherteDauer.includes("Min")) {
    gespeicherteDauer = `${gespeicherteDauer} Min`;
  }

  zeigeText(`⚓ Letzter Spielstand geladen für ${aktuellerSpieler}!  
🔧 Geladene Standards:  
• Operatoren: ${letzterStand.operatoren?.join(", ") || "–"}  
• Modus: ${letzterStand.modus}  
• Klasse: ${letzterStand.klasse}  
• Schwierigkeit: ${letzterStand.schwierigkeit}  
• Zahlenauswahl: ${letzterStand.zahlenauswahl}  
• Kategorie: ${letzterStand.kategorie}  
🏆 Punkte: ${letzterStand.punkte}  
⏳ Dauer: ${gespeicherteDauer}`);
}
