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

    # Aufgaben-Modus
    in_aufgabe: bool = False
    expected_answer: Optional[str] = None

    # Namens- & Operatoren-Dialoge
    name_dialog_aktiv: bool = False
    operator_dialog_aktiv: bool = False

    # Spielername
    player_name: Optional[str] = None

    # 📊 Session-Statistiken
    session_stats: Dict[str, int] = field(default_factory=lambda: {
        "aufgabenGesamt": 0,
        "aufgabenGeloest": 0,
        "punkte": 0
    })


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
    num_map = {"1": "+", "2": "-", "3": "×", "4": "÷"}
    if t in num_map:
        return num_map[t]
    sym = (
        t.replace("x", "×").replace("X", "×").replace("*", "×")
         .replace("/", "÷").replace(":", "÷")
         .replace("−", "-").replace("–", "-")
    )
    return sym if sym in {"+", "-", "×", "÷"} else t


def _normalize_operator_value(raw: str) -> str:
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
        v = _normalize_operator_value(v)
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
# Aufgaben-Helfer
# ======================

def _is_numeric_answer(s: str) -> bool:
    t = s.strip()
    if not t:
        return False
    if "/" in t:
        num_den = t.split("/", 1)
        if len(num_den) == 2:
            a, b = num_den[0].strip(), num_den[1].strip()
            return a.replace("-", "", 1).isdigit() and b.replace("-", "", 1).isdigit()
        return False
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
        return "♻️ Alle Standards zurückgesetzt."

    # Merken-Dialog
    if state.merk_dialog_aktiv:
        choice = t
        if choice in ("1", "2", "3"):
            key = state.merk_dialog_key
            value = state.pending_value
            state.merk_dialog_aktiv = False
            state.merk_dialog_key = None
            state.pending_value = None

            if not key or value is None:
                return "🔓 Abgebrochen."

            if key == "Operatoren":
                value = _normalize_operator_value(value)
            elif key == "Schwierigkeit":
                value = _normalize_schwierigkeit(value)
            elif key == "Modus":
                value = _normalize_modus(value)
            elif key == "Name":
                value = value.strip()

            if choice == "1":
                if key == "Name":
                    state.player_name = value
                return "🔓 Alles klar – nur jetzt gültig."
            if choice == "2":
                if key == "Name":
                    state.player_name = value
                else:
                    state.session_standards[key] = value
                return "🗂️ Gemerkt für diese Sitzung."
            persistent[key] = value
            save_persistent(persistent)
            return "📌 Standard gespeichert."
        return "👉 Antworte mit „1“, „2“ oder „3“."

    # Während einer Aufgabe
    if state.in_aufgabe:
        if not _is_numeric_answer(t):
            return (
                "Bitte gib **nur die Antwort als Zahl** ein (z. B. 12, -3, 3/4 oder 2,5)."
            )

        given = t.replace(",", ".")
        exp = (state.expected_answer or "").replace(",", ".")
        state.in_aufgabe = False
        state.expected_answer = None

        state.session_stats["aufgabenGesamt"] += 1
        if given == exp:
            state.session_stats["aufgabenGeloest"] += 1
            state.session_stats["punkte"] += 10
            feedback = f"✅ Richtig, aye! ⚓\nDie Lösung ist {exp}."
        else:
            feedback = f"❌ Leider falsch. Erwartet war: {exp}"

        if state.session_stats["aufgabenGesamt"] >= 10:
            richtig = state.session_stats["aufgabenGeloest"]
            falsch = state.session_stats["aufgabenGesamt"] - richtig
            punkte = state.session_stats["punkte"]

            note = "1 (Sehr gut)" if richtig == 10 else \
                   "2 (Gut)" if richtig >= 8 else \
                   "3 (Befriedigend)" if richtig >= 6 else \
                   "4 (Ausreichend)" if richtig >= 4 else "5 (Ungenügend)"

            return (
                f"{feedback}\n\n"
                f"👉 {state.player_name or 'Piratenfreund'}, das war deine 10. Aufgabe – die Prüfung ist beendet! 🏴‍☠️\n\n"
                f"🏁 Prüfung beendet!\n"
                f"✅ Richtige Antworten: {richtig}\n"
                f"❌ Falsche Antworten: {falsch}\n"
                f"🏆 Gesamtpunkte: {punkte}\n"
                f"📖 Note: {note}\n"
                f"⏳ Dauer: ca. wenige Minuten\n\n"
                f"💾 Spielstand gespeichert für {state.player_name or 'Anonymer Matrose'}! ⚓\n"
                "👉 Was möchtest du tun?\n"
                "1️⃣ Nochmal spielen\n"
                "2️⃣ Schwierigkeit erhöhen\n"
                "3️⃣ Zurück zum Start"
            )

        return f"{feedback}\n\n⚔️ Nächste Aufgabe: {_generate_task(state)}"

    # Namensdialog
    if state.name_dialog_aktiv:
        candidate = t.strip()
        import re
        if not re.fullmatch(r"[A-Za-zÄÖÜäöüß\- ]{1,20}", candidate):
            return "Bitte gib nur deinen Namen ein (max. 20 Zeichen)."
        state.name_dialog_aktiv = False
        state.merk_dialog_aktiv = True
        state.merk_dialog_key = "Name"
        state.pending_value = candidate
        return format_confirmation_and_menu("Name", candidate)

    # Operatorendialog
    if state.operator_dialog_aktiv:
        digits = [ch for ch in t if ch in "1234"]
        if not digits:
            return "Bitte antworte mit Ziffern 1..4."
        mapping = {"1": "+", "2": "-", "3": "×", "4": "÷"}
        ops = []
        for d in digits:
            sym = mapping[d]
            if sym not in ops:
                ops.append(sym)
        value = ",".join(ops)
        state.operator_dialog_aktiv = False
        state.merk_dialog_aktiv = True
        state.merk_dialog_key = "Operatoren"
        state.pending_value = value
        return format_confirmation_and_menu("Operatoren", value)

    # Connector Key:Value
    parsed = parse_connector(t_raw)
    if parsed:
        key, value = parsed
        state.merk_dialog_aktiv = True
        state.merk_dialog_key = key
        state.pending_value = value
        return format_confirmation_and_menu(key, value)

    # Befehle ohne Doppelpunkt
    low = t.lower()
    if low in {"name", "spieler", "name ändern", "name aendern"}:
        if state.in_aufgabe:
            return "Beantworte zuerst die aktuelle Aufgabe."
        current_name = persistent.get("Name") or state.player_name
        hint = f"(Aktuell: {current_name})" if current_name else ""
        state.name_dialog_aktiv = True
        return f"Wie möchtest du genannt werden? {hint}".strip()

    if low in {"operatoren", "operator", "ops"}:
        if state.in_aufgabe:
            return "Beantworte zuerst die aktuelle Aufgabe."
        state.operator_dialog_aktiv = True
        return _operator_choice_menu()

    # Beispiel-Aufgabe
    if low == "demo":
        state.in_aufgabe = True
        state.expected_answer = "12"
        return "Demo-Aufgabe: 7 + 5 = ?"

    if low == "ahoi":
        return f"⚔️ Erste Aufgabe: {_generate_task(state)}"

    # Default → Einstellungen anzeigen
    merged = build_params_with_priority(None, state.session_standards, persistent)
    if not merged:
        return "Weiter ohne gesetzte Standards."
    lines = [f"{k}: {v}" for k, v in merged.items()]
    return "Weiter mit aktuellen Einstellungen:\n" + "\n".join(lines)
