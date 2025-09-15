# C:\Users\mnold_t1ohvc3\Documents\zahlenpirat-backend\engine.py
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from settings_manager import load_persistent, save_persistent


@dataclass
class SessionState:
    # Merken-Dialog (1/2/3)
    merk_dialog_aktiv: bool = False
    merk_dialog_key: Optional[str] = None
    pending_value: Optional[str] = None
    session_standards: Dict[str, str] = field(default_factory=dict)

    # Aufgaben-Modus (falls genutzt)
    in_aufgabe: bool = False
    expected_answer: Optional[str] = None

    # NEU: Namens-Dialog & Operatoren-Auswahl
    name_dialog_aktiv: bool = False
    operator_dialog_aktiv: bool = False

    # Optional: aktueller Spielername in der Session (persistenter Key ist "Name")
    player_name: Optional[str] = None


# In-Memory-Sessionstore
SESSIONS: Dict[str, SessionState] = {}


def get_state(session_id: str) -> SessionState:
    if session_id not in SESSIONS:
        SESSIONS[session_id] = SessionState()
    return SESSIONS[session_id]


# ======================
# Normalisierungen
# ======================

def _normalize_operator_token(tok: str) -> str:
    t = tok.strip()
    if not t:
        return t
    # Zahl → Operator
    num_map = {"1": "+", "2": "-", "3": "×", "4": "÷"}
    if t in num_map:
        return num_map[t]
    # Synonyme / Varianten
    sym = (
        t.replace("x", "×").replace("X", "×").replace("*", "×")
         .replace("/", "÷").replace(":", "÷")
         .replace("−", "-").replace("–", "-")  # verschiedene Minus-Zeichen
    )
    return sym if sym in {"+", "-", "×", "÷"} else t


def _normalize_operator_value(raw: str) -> str:
    # Komma- oder Leerzeichen-getrennt; Duplikate raus; nur gültige Operatoren
    parts = [p for chunk in raw.split(",") for p in chunk.split() if p]
    out: list[str] = []
    for p in parts:
        n = _normalize_operator_token(p)
        if n and n in {"+", "-", "×", "÷"} and n not in out:
            out.append(n)
    return ",".join(out) if out else raw.strip()


def _normalize_schwierigkeit(raw: str) -> str:
    v = raw.strip().lower()
    if v in {"1", "leicht"}:
        return "Leicht"
    if v in {"2", "mittel"}:
        return "Mittel"
    if v in {"3", "schwer"}:
        return "Schwer"
    if v in {"4", "extrem", "extrem schwer", "sehr schwer"}:
        return "Extrem schwer"
    return raw.strip()


def _normalize_modus(raw: str) -> str:
    v = raw.strip()
    map_num = {
        "1": "Prüfung der Zahlen",
        "2": "Zahlenspiele",
        "3": "Lernen",
        "4": "Abenteuer & Extras",
        "5": "Erinnerung",
        "6": "Piraten-Minigames",
    }
    return map_num.get(v, v)


# ======================
# Parser
# ======================

def parse_connector(text: str) -> Optional[Tuple[str, str]]:
    t = text.strip()
    low = t.lower()

    if low.startswith("operatoren:"):
        v = t.split(":", 1)[1].strip()
        v = _normalize_operator_value(v)   # normalisiert hinein
        return ("Operatoren", v)

    if low.startswith("modus:"):
        v = t.split(":", 1)[1].strip()
        v = _normalize_modus(v)
        return ("Modus", v)

    if low.startswith("klasse:"):
        v = t.split(":", 1)[1].strip()
        return ("Klasse", v)

    if low.startswith("schwierigkeit:"):
        v = t.split(":", 1)[1].strip()
        v = _normalize_schwierigkeit(v)
        return ("Schwierigkeit", v)

    if low.startswith("zahlenauswahl:"):
        v = t.split(":", 1)[1].strip()
        return ("Zahlenauswahl", v)

    if low.startswith("name:"):
        v = t.split(":", 1)[1].strip()
        return ("Name", v)

    return None


def build_params_with_priority(
    explicit: Optional[Dict[str, str]],
    session: Dict[str, str],
    persistent: Dict[str, str],
) -> Dict[str, str]:
    """Priorität: explizit > Sitzung > persistent."""
    out: Dict[str, str] = {}
    explicit = explicit or {}
    keys = {"Operatoren", "Modus", "Klasse", "Schwierigkeit", "Zahlenauswahl"}
    for k in keys:
        if explicit.get(k):
            out[k] = explicit[k]
        elif session.get(k):
            out[k] = session[k]
        elif persistent.get(k):
            out[k] = persistent[k]
    return out


# ======================
# Helper für Routen
# ======================

def get_effective_settings(session_id: str) -> Dict[str, Dict[str, str]]:
    """
    Liefert die effektiv genutzten Einstellungen (Session > Persistent),
    plus die Rohquellen; Anzeige ist stets normalisiert.
    """
    state = get_state(session_id)
    persistent = load_persistent()

    def _canon(d: Dict[str, str]) -> Dict[str, str]:
        out = dict(d)
        if "Operatoren" in out:
            out["Operatoren"] = _normalize_operator_value(out["Operatoren"])
        if "Schwierigkeit" in out:
            out["Schwierigkeit"] = _normalize_schwierigkeit(out["Schwierigkeit"])
        if "Modus" in out:
            out["Modus"] = _normalize_modus(out["Modus"])
        return out

    eff_raw = build_params_with_priority(
        explicit=None,
        session=state.session_standards,
        persistent=persistent,
    )
    effective = _canon(eff_raw)
    session_norm = _canon(state.session_standards)
    persistent_norm = _canon(persistent)

    return {
        "effective": effective,
        "session": session_norm,
        "persistent": persistent_norm,
    }


# ======================
# Ausgabe + Dialog
# ======================

def format_confirmation_and_menu(key: str, value: str) -> str:
    # Für die freundliche Anzeige normalisieren
    if key == "Operatoren":
        value = _normalize_operator_value(value)

    friendly = None
    if key == "Operatoren":
        mapping = {
            "+": "➕ Addition („+“) – Der Schatz wird größer!",
            "-": "➖ Subtraktion („−“) – Teile gerecht!",
            "×": "✖️ Multiplikation („×“) – Segel setzen!",
            "÷": "➗ Division („÷“) – gerecht aufteilen!",
        }
        parts = [p.strip() for p in value.split(",") if p.strip()]
        if len(parts) > 1:
            friendly = "\n".join(mapping.get(p, f"Operator „{p}“") for p in parts)
        elif parts:
            friendly = mapping.get(parts[0], f"{key}: {value}")

    prefix = friendly if friendly else f"{key}: {value}"
    return (
        f"{prefix}\n\n"
        "🧩 Möchtest du diese Auswahl merken?\n"
        "1️⃣ Nur dieses Mal\n"
        "2️⃣ Für dieses Gespräch merken\n"
        "3️⃣ Immer zulassen (Standard setzen)\n\n"
        "👉 Antworte mit „1“, „2“ oder „3“."
    )


def _operator_choice_menu() -> str:
    return (
        "Welche Operatoren möchtest du verwenden?\n"
        "1) +  (Addition)\n"
        "2) -  (Subtraktion)\n"
        "3) ×  (Multiplikation)\n"
        "4) ÷  (Division)\n\n"
        "Mehrere möglich – antworte z. B. mit „13“ oder „1,3“."
    )


# ======================
# Aufgaben-Helfer (falls genutzt)
# ======================

def _is_numeric_answer(s: str) -> bool:
    """Erlaubte Antworten im Aufgabenmodus: Ganzzahl, Dezimal (Punkt/Komma), einfacher Bruch."""
    t = s.strip()
    if not t:
        return False
    # Bruch
    if "/" in t:
        num_den = t.split("/", 1)
        if len(num_den) == 2:
            a, b = num_den[0].strip(), num_den[1].strip()
            return a.replace("-", "", 1).isdigit() and b.replace("-", "", 1).isdigit()
        return False
    # Dezimal mit Komma/Punkt → in Zahl verwandelbar?
    t2 = t.replace(",", ".")
    if t2.replace("-", "", 1).replace(".", "", 1).isdigit():
        return True
    return False

# ======================
# Neue Aufgabe generieren
# ======================
def _generate_task(state) -> str:
    import random
    a, b = random.randint(1, 10), random.randint(1, 10)
    op = "+"
    result = a + b

    state.in_aufgabe = True
    state.expected_answer = str(result)

    return f"{a} + {b} = ?"


# ======================
# Hauptlogik
# ======================

def handle_user_input(session_id: str, text: str) -> str:
    state = get_state(session_id)
    persistent = load_persistent()
    t_raw = text or ""
    t = t_raw.strip()

    # Reset
    if t.lower() == "standard zurücksetzen":
        state.session_standards.clear()
        save_persistent({})
        return "♻️ Alle Standards zurückgesetzt. Nutze wieder deine nächsten Eingaben."

    # Merken-Dialog (1/2/3)
    if state.merk_dialog_aktiv:
        choice = t
        if choice in ("1", "2", "3"):
            key = state.merk_dialog_key
            value = state.pending_value

            # Cleanup (immer)
            state.merk_dialog_aktiv = False
            state.merk_dialog_key = None
            state.pending_value = None

            if not key or value is None:
                return "🔓 Abgebrochen. Nutze deine nächste Auswahl."

            # Vor dem Speichern normalisieren
            if key == "Operatoren":
                value = _normalize_operator_value(value)
            elif key == "Schwierigkeit":
                value = _normalize_schwierigkeit(value)
            elif key == "Modus":
                value = _normalize_modus(value)
            # Name wird nicht verändert, nur getrimmt
            elif key == "Name":
                value = value.strip()

            if choice == "1":
                # nur diesmal
                if key == "Name":
                    state.player_name = value
                return "🔓 Alles klar – ich nutze diese Auswahl nur jetzt."
            if choice == "2":
                # Sitzung
                if key == "Name":
                    state.player_name = value
                else:
                    state.session_standards[key] = value
                return "🗂️ Gemerkt für dieses Gespräch. Gilt bis zum Ende der Sitzung."
            # choice == "3" → persistent
            persistent[key] = value
            save_persistent(persistent)
            return "📌 Standard gespeichert. Beim nächsten Start automatisch aktiv."
        return "👉 Antworte mit „1“, „2“ oder „3“."

    # Während einer Aufgabe: nur numerische Antworten erlauben
    if state.in_aufgabe:
        if not _is_numeric_answer(t):
            return (
                "Bitte gib **nur die Antwort als Zahl** ein (z. B. 12, -3, 3/4 oder 2,5). "
                "Texte wie \"richtig\", \"zurueck\", \"vertippt\" usw. werden nicht akzeptiert.\n\n"
                "Tipp: Einstellungen setzt du im Format \"Operatoren: +\" oder \"Schwierigkeit: Mittel\"."
            )
        # (Hier Beispielbewertung, falls du Aufgaben nutzt)
        given = t.replace(",", ".")
        exp = (state.expected_answer or "").replace(",", ".")
        state.in_aufgabe = False
        state.expected_answer = None
        if given == exp:
            return "✅ Richtig!"
        return f"❌ Leider falsch. Erwartet war: {exp}"

    # NEU: Namensdialog aktiv?
    if state.name_dialog_aktiv:
        candidate = t.strip()
        # einfache Validierung (nur Buchstaben/Leer-/Bindestrich, 1..20)
        import re
        if not re.fullmatch(r"[A-Za-zÄÖÜäöüß\- ]{1,20}", candidate):
            return "Bitte gib nur deinen Namen ein (max. 20 Zeichen, nur Buchstaben, Leer- oder Bindestrich)."
        state.name_dialog_aktiv = False
        # gleich Merken-Dialog starten (Key = "Name")
        state.merk_dialog_aktiv = True
        state.merk_dialog_key = "Name"
        state.pending_value = candidate
        return format_confirmation_and_menu("Name", candidate)

    # NEU: Operatoren-Auswahldialog aktiv?
    if state.operator_dialog_aktiv:
        # Erlaube z. B. "13", "1,3", "1 3"
        digits = [ch for ch in t if ch in "1234"]
        if not digits:
            return "Bitte antworte mit Ziffern 1..4 (z. B. 13 oder 1,3)."
        mapping = {"1": "+", "2": "-", "3": "×", "4": "÷"}
        ops = []
        for d in digits:
            sym = mapping[d]
            if sym not in ops:
                ops.append(sym)
        value = ",".join(ops)
        state.operator_dialog_aktiv = False
        # Danach direkt Merken-Dialog für Operatoren
        state.merk_dialog_aktiv = True
        state.merk_dialog_key = "Operatoren"
        state.pending_value = value
        return format_confirmation_and_menu("Operatoren", value)

    # Neuer Connektor (Key:Value)
    parsed = parse_connector(t_raw)
    if parsed:
        key, value = parsed
        # Start Merken-Dialog
        state.merk_dialog_aktiv = True
        state.merk_dialog_key = key
        state.pending_value = value
        return format_confirmation_and_menu(key, value)

    # NEU: Befehle ohne Doppelpunkt
    low = t.lower()
    if low in {"name", "spieler", "name ändern", "name aendern"}:
        if state.in_aufgabe:
            return "Beantworte zuerst die aktuelle Aufgabe, dann ändern wir den Namen."
        # starte Namensdialog
        current_name = persistent.get("Name") or state.player_name
        hint = f"(Aktuell: {current_name})" if current_name else ""
        state.name_dialog_aktiv = True
        return f"Wie möchtest du genannt werden? Schreib nur deinen Namen. {hint}".strip()

    if low in {"operatoren", "operator", "ops"}:
        if state.in_aufgabe:
            return "Beantworte zuerst die aktuelle Aufgabe, dann ändern wir die Operatoren."
        state.operator_dialog_aktiv = True
        return _operator_choice_menu()

    # Beispiel-Aufgabe starten (falls gewünscht)
    if low == "demo":
        state.in_aufgabe = True
        state.expected_answer = "12"
        return "Demo-Aufgabe: 7 + 5 = ?"

        # 🚀 NEU: Startsignal "Ahoi" -> erste Aufgabe generieren
    if low == "ahoi":
        return f"⚔️ Erste Aufgabe: {_generate_task(state)}"
        # Beispiel: Einfache Aufgabe im Bereich 1–10
        import random
        a, b = random.randint(1, 10), random.randint(1, 10)
        op = "+"
        result = a + b

        # Session merkt sich, dass wir jetzt im Aufgabenmodus sind
        state.in_aufgabe = True
        state.expected_answer = str(result)

        return f"⚔️ Erste Aufgabe: {a} + {b} = ?"


    # Normale Fortsetzung → aktuelle Parameter (zur Kontrolle ausgeben)
    merged = build_params_with_priority(None, state.session_standards, persistent)
    if not merged:
        return "Weiter ohne gesetzte Standards. Setze z. B. „Operatoren: +“ oder tippe „Operatoren“ für eine Auswahl."
    lines = [f"{k}: {v}" for k, v in merged.items()]
    return "Weiter mit aktuellen Einstellungen:\n" + "\n".join(lines)
