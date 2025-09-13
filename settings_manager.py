# C:\Users\mnold_t1ohvc3\Documents\zahlenpirat-backend\settings_manager.py
import json, os, threading
from typing import Dict, Any

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SETTINGS_PATH = os.path.join(DATA_DIR, "settings.json")

_lock = threading.RLock()

DEFAULT_KEYS = ["Operatoren", "Modus", "Klasse", "Schwierigkeit", "Zahlenauswahl"]


def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


# --- Kleiner Reparatur-Helper gegen Mojibake in bereits gespeicherten Strings ---
_MOJI_FIX = {
    "Ã—": "×",
    "Ã·": "÷",
    # (optional weitere, falls nötig)
    "Ã„": "Ä", "Ã–": "Ö", "Ãœ": "Ü",
    "Ã¤": "ä", "Ã¶": "ö", "Ã¼": "ü",
    "ÃŸ": "ß",
}

def _fix_mojibake_in_str(s: str) -> str:
    out = s
    for bad, good in _MOJI_FIX.items():
        if bad in out:
            out = out.replace(bad, good)
    return out

def _fix_mojibake(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _fix_mojibake(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_fix_mojibake(v) for v in obj]
    if isinstance(obj, str):
        return _fix_mojibake_in_str(obj)
    return obj
# -------------------------------------------------------------------------------


def load_persistent() -> Dict[str, Any]:
    with _lock:
        if not os.path.exists(SETTINGS_PATH):
            return {}
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    return {}
                # Repariere evtl. falsch angezeigte UTF-8/Mojibake-Sequenzen:
                return _fix_mojibake(data)
        except json.JSONDecodeError:
            return {}


def save_persistent(data: Dict[str, Any]) -> None:
    with _lock:
        _ensure_dir()
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            # ensure_ascii=False => echte UTF-8 Zeichen (×, ÷, …) landen im File
            json.dump(data, f, ensure_ascii=False, indent=2)


def reset_persistent() -> None:
    save_persistent({})


def normalize_keys_for_display(persistent: dict) -> dict:
    """
    Nur Defaults setzen, NICHT an Werten rumformatieren.
    (Keine ASCII-Downconverts o.ä. – Werte bleiben wie gespeichert.)
    """
    def _val(d: dict, k: str) -> str:
        v = d.get(k, "–")
        if v is None or str(v).strip() == "":
            return "–"
        return str(v)

    return {
        "Operatoren":    _val(persistent, "Operatoren"),
        "Modus":         _val(persistent, "Modus"),
        "Klasse":        _val(persistent, "Klasse"),
        "Schwierigkeit": _val(persistent, "Schwierigkeit"),
        "Zahlenauswahl": _val(persistent, "Zahlenauswahl"),
    }
