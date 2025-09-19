    # C:\Users\mnold_t1ohvc3\Documents\zahlenpirat-backend\connector_routes.py
    from fastapi import APIRouter, Body, Query
    from typing import Dict, Any
    from engine import get_state
    import requests

    # Normalisierer aus der Engine (für Operatoren/Schwierigkeit/Modus)
    from engine import _normalize_operator_value, _normalize_schwierigkeit, _normalize_modus

    from settings_manager import (
        load_persistent,
        save_persistent,
        reset_persistent,
        normalize_keys_for_display,
    )

    # Engine-Import mit Fallback: wenn get_effective_settings noch nicht existiert
    try:
        from engine import handle_user_input, get_effective_settings
    except ImportError:
        from engine import handle_user_input, get_state  # type: ignore
        from settings_manager import load_persistent as _load_persistent  # type: ignore

        def get_effective_settings(session_id: str) -> Dict[str, Dict[str, str]]:
            """Fallback-Helfer: effective = Session > Persistent (nur gelistete Keys)."""
            state = get_state(session_id)  # aus engine
            persistent = _load_persistent()
            keys = ("Operatoren", "Modus", "Klasse", "Schwierigkeit", "Zahlenauswahl")
            effective: Dict[str, str] = {}
            for k in keys:
                v = state.session_standards.get(k) or persistent.get(k)
                if v:
                    effective[k] = v
            return {
                "effective": effective,
                "session": dict(state.session_standards),
                "persistent": dict(persistent),
            }

    # Optional: Plain-Ausgabe (emoji-/typografie-frei).
    # Wenn utils_text.py existiert, wird es genutzt; sonst einfacher Fallback.
    try:
        from utils_text import to_plain  # bevorzugt
    except Exception:  # pragma: no cover
        def to_plain(s: str) -> str:
            """Sehr einfacher Fallback: Emojis grob entfernen, typografische Zeichen normalisieren."""
            def _is_emoji(ch: str) -> bool:
                o = ord(ch)
                return (
                    0x1F300 <= o <= 0x1FAFF  # Emoji
                    or 0x2600 <= o <= 0x26FF  # Misc symbols
                    or 0x2700 <= o <= 0x27BF  # Dingbats
                    or o in (0xFE0F, 0x20E3)  # Variation selector, keycap
                )
            t = "".join(ch for ch in s if not _is_emoji(ch))
            return (
                t.replace("„", '"').replace("“", '"')
                .replace("‚", "'").replace("’", "'")
                .replace("–", "-").replace("—", "-")
                .replace("…", "...")
            )

    router = APIRouter()

    # --- HELFER: Eingabewerte reparieren/normalisieren ---------------------------
    def _repair_mojibake_str(s: str) -> str:
        """
        Repariert typische UTF-8/CP1252-Mojibake (z. B. 'Ã·' -> '÷').
        Versucht zuerst den sauberen latin-1 -> utf-8 Roundtrip.
        Danach noch zielgerichtete Fallbacks.
        """
        if "Ã" in s or "Â" in s:
            try:
                s2 = s.encode("latin-1").decode("utf-8")
                return s2
            except Exception:
                pass
        # zielgerichtete Fallbacks (falls Roundtrip oben nicht greift)
        s = (s
            .replace("Ã×", "×")
            .replace("Ã·", "÷")
            .replace("Ã,", "×,")   # spezieller Fall, der bei dir auftrat: 'Ã,Ã·'
            )
        return s

    def _normalize_for_key(key: str, raw: Any) -> str:
        v = str(raw)
        if key == "Operatoren":
            v = _repair_mojibake_str(v)
            v = _normalize_operator_value(v)        # z. B. "x,/" -> "×,÷"
        elif key == "Schwierigkeit":
            v = _normalize_schwierigkeit(v)
        elif key == "Modus":
            v = _normalize_modus(v)
        return v
    # ----------------------------------------------------------------------------

    @router.get("/settings")
    def get_settings() -> Dict[str, Any]:
        return load_persistent()

    # --------- NEU: Werte beim Speichern reparieren + kanonisieren ---------------
    @router.post("/settings")
    def set_settings(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
        """
        Mehrere Settings auf einmal setzen:
        - Repariert Mojibake (Ã… -> Umlaut/Operator)
        - Normalisiert je nach Schlüssel (Operatoren/Schwierigkeit/Modus)
        """
        current = load_persistent()
        for key, raw in (payload or {}).items():
            # nur bekannte Keys anfassen; andere einfach übernehmen
            if key in ("Operatoren", "Schwierigkeit", "Modus"):
                current[key] = _normalize_for_key(key, raw)
            else:
                current[key] = raw
        save_persistent(current)
        return {"status": "ok", "saved": current}

    @router.post("/settings/set")
    def set_single(key: str = Query(...), value: str = Query(...)) -> Dict[str, Any]:
        """
        Ein einzelnes Setting setzen (Query-Variante):
        - Repariert Mojibake
        - Normalisiert je nach Schlüssel
        """
        current = load_persistent()
        if key in ("Operatoren", "Schwierigkeit", "Modus"):
            v = _normalize_for_key(key, value)
        else:
            v = value
        current[key] = v
        save_persistent(current)
        return {"status": "ok", "saved": {key: v}}
    # ----------------------------------------------------------------------------

    @router.post("/settings/reset")
    def reset_settings() -> Dict[str, Any]:
        reset_persistent()
        return {"status": "ok", "message": "all standards reset"}

    @router.get("/start")
    def start(plain: bool = Query(True)) -> Dict[str, str]:  # plain standardmäßig an
        base_menu = (
            "1️⃣ 🧭 Test\n"
            "2️⃣ 🏴‍☠️ Zahlenspiele\n"
            "3️⃣ 🗺️ Lernen\n"
            "4️⃣ ⚓ Abenteuer & Extras\n"
        )
        persistent = load_persistent()
        if persistent:
            disp = normalize_keys_for_display(persistent)
            std = (
                "🔧 Geladene Standards:\n"
                f"• Operatoren: \"{disp['Operatoren']}\"\n"
                f"• Modus: \"{disp['Modus']}\"\n"
                f"• Klasse: \"{disp['Klasse']}\"\n"
                f"• Schwierigkeit: \"{disp['Schwierigkeit']}\"\n"
                f"• Zahlenauswahl: \"{disp['Zahlenauswahl']}\"\n"
            )
            out = base_menu + "\n" + std
        else:
            out = base_menu

        if plain:
            out = to_plain(out)
        return {"text": out}

    @router.get("/current")
    def current(sessionId: str = Query(...), plain: bool = Query(True)) -> Dict[str, Any]:
        """
        Zeigt die aktuell wirksamen Einstellungen (effective),
        plus die beiden Quellen: Session und Persistent.
        """
        data = get_effective_settings(sessionId)

        def _fmt_block(title: str, d: Dict[str, Any]) -> str:
            if not d:
                return f"{title}:\n- (leer)"
            order = ("Operatoren", "Modus", "Klasse", "Schwierigkeit", "Zahlenauswahl")
            lines = [f"{title}:"]
            for k in order:
                if k in d:
                    lines.append(f"- {k}: {d[k]}")
            return "\n".join(lines)

        text = "\n\n".join([
            _fmt_block("Effective (aktiv)", data.get("effective", {})),
            _fmt_block("Session (nur dieses Gespraech)", data.get("session", {})),
            _fmt_block("Persistent (immer)", data.get("persistent", {})),
        ])

        if plain:
            text = to_plain(text)
        return {"text": text, "data": data}


    import logging, traceback
    logging.basicConfig(level=logging.INFO)


    @router.post("/flow")
    def flow(
        sessionId: str = Body(...),
        text: str = Body(...),
        plain: bool = Query(True),
    ) -> Dict[str, Any]:
        try:
            logging.info(f"[FLOW] Eingabe erhalten – sessionId={sessionId}, text={text}")
            out = handle_user_input(sessionId, text)

            # --- NEU: Session speichern ---
            state = get_state(sessionId)  # akt. Session-Infos aus engine
            sessionData = {
                "spieler": sessionId,
                "modus": state.session_standards.get("Modus", "Test"),
                "klasse": state.session_standards.get("Klasse"),
                "schwierigkeit": state.session_standards.get("Schwierigkeit"),
                "operatoren": state.session_standards.get("Operatoren", []),
                "aufgabenGesamt": state.session_stats.get("aufgabenGesamt", 0),
                "aufgabenGeloest": state.session_stats.get("aufgabenGeloest", 0),
                "punkte": state.session_stats.get("punkte", 0),
                "status": "laufend",
                "sessionId": str(uuid.uuid4()),   # eindeutige ID
                "datum": datetime.datetime.utcnow().isoformat(),  # Zeitstempel
            }

            scores = _load_scores()
            if sessionId not in scores:
                scores[sessionId] = {"sessions": []}

            scores[sessionId]["sessions"].append(sessionData)
            _save_scores(scores)
            # -----------------------------

            if plain:
                out = to_plain(out)
            logging.info(f"[FLOW] Ausgabe: {out}")
            return {"text": out, "autoSaved": sessionData}

        except Exception as e:
            logging.error("Fehler im /flow", exc_info=True)
            return {"text": f"⚠️ Fehler: {str(e)}"}

    # --------------------------------------------------------------------
    # NEUE FUNKTIONEN: Session-Speichern und -Historie
    # --------------------------------------------------------------------
    import json, os, uuid, datetime

    SCORES_FILE = os.path.join("data", "scores.json")

    def _load_scores() -> dict:
        if os.path.exists(SCORES_FILE):
            with open(SCORES_FILE, "r", encoding="utf-8") as f:
                try:
                    return json.load(f)
                except Exception:
                    return {}
        return {}

    def _save_scores(data: dict):
        os.makedirs(os.path.dirname(SCORES_FILE), exist_ok=True)
        with open(SCORES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @router.post("/saveSession")
    def save_session(
        spieler: str = Body(...),
        sessionData: Dict[str, Any] = Body(...)
    ) -> Dict[str, Any]:
        """Speichert eine neue Session für den Spieler (anhängen an Historie)."""
        scores = _load_scores()

        if spieler not in scores:
            scores[spieler] = {"sessions": []}

        # Pflichtfelder ergänzen, falls nicht im Body mitgeschickt
        sessionData.setdefault("modus", "Test")
        sessionData.setdefault("klasse", None)
        sessionData.setdefault("schwierigkeit", None)
        sessionData.setdefault("operatoren", [])
        sessionData.setdefault("status", "abgebrochen")  # Default: abgebrochen
        sessionData.setdefault("aufgabenGesamt", 0)
        sessionData.setdefault("aufgabenGeloest", 0)
        sessionData.setdefault("punkte", 0)

        # Automatische Felder
        sessionData["sessionId"] = str(uuid.uuid4())
        sessionData["datum"] = datetime.datetime.utcnow().isoformat()

        scores[spieler]["sessions"].append(sessionData)
        _save_scores(scores)

        return {"status": "ok", "saved": sessionData}

    @router.get("/getHistory")
    def get_history(spieler: str = Query(...)) -> Dict[str, Any]:
        """Gibt alle Sessions des Spielers zurück."""
        scores = _load_scores()
        if spieler not in scores:
            return {"spieler": spieler, "sessions": []}
        return {"spieler": spieler, "sessions": scores[spieler]["sessions"]}

    # --------------------------------------------------------------------
    # NEU: Erweiterter Endpunkt für direkte Session-Speicherung
    # --------------------------------------------------------------------
    @router.post("/postSaveExtended")
    def post_save_extended(
        sessionData: Dict[str, Any] = Body(...),
    ) -> Dict[str, Any]:
        """Erweitertes Speichern: Sessiondaten direkt übernehmen + Pflichtfelder ergänzen."""
        try:
            logging.info(f"[SAVE] Anfrage erhalten: {sessionData}")

            scores = _load_scores()
            spieler = sessionData.get("spieler", "Anonym")

            if spieler not in scores:
                scores[spieler] = {"sessions": []}

            # Pflichtfelder ergänzen
            sessionData.setdefault("modus", "Test")
            sessionData.setdefault("klasse", None)
            sessionData.setdefault("schwierigkeit", None)
            sessionData.setdefault("operatoren", [])
            sessionData.setdefault("status", "abgebrochen")
            sessionData.setdefault("aufgabenGesamt", 0)
            sessionData.setdefault("aufgabenGeloest", 0)
            sessionData.setdefault("punkte", 0)

            # Automatische Felder
            sessionData["sessionId"] = str(uuid.uuid4())
            sessionData["datum"] = datetime.datetime.utcnow().isoformat()

            scores[spieler]["sessions"].append(sessionData)
            _save_scores(scores)

            logging.info(f"[SAVE] Erfolgreich gespeichert für Spieler={spieler}: {sessionData}")
            return {"status": "ok", "saved": sessionData}

        except Exception as e:
            logging.error("[SAVE] Fehler beim Speichern", exc_info=True)
            return {"status": "error", "error": str(e)}

    # --------------------------------------------------------------------
    # NEU: Save mit Fallback (/save → /postSaveExtended)
    # --------------------------------------------------------------------
    @router.post("/saveWithFallback")
    def save_with_fallback(sessionData: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
        """
        Versucht zuerst /save aufzurufen.
        Falls das fehlschlägt (Cloudflare 400/Timeout/etc.), dann /postSaveExtended.
        """
        base_url = "https://<dein-render-service>.onrender.com"

        try:
            # 1. Versuch: /save
            resp = requests.post(f"{base_url}/save", json=sessionData, timeout=5)
            if resp.ok:
                return {"status": "ok", "source": "/save", "data": resp.json()}
            else:
                raise Exception(f"/save fehlgeschlagen: {resp.status_code} {resp.text}")

        except Exception as e:
            # 2. Versuch: /postSaveExtended
            try:
                resp2 = requests.post(f"{base_url}/postSaveExtended", json=sessionData, timeout=5)
                if resp2.ok:
                    return {"status": "ok", "source": "/postSaveExtended", "data": resp2.json()}
                else:
                    return {"status": "error", "source": "/postSaveExtended", "error": resp2.text}
            except Exception as e2:
                return {"status": "error", "error": f"Fallback fehlgeschlagen: {str(e2)}"}

    @router.post("/endSession")
    def end_session(spieler: str = Body(...)) -> Dict[str, Any]:
        """
        Markiert die letzte Session des Spielers als 'abgeschlossen'.
        Falls keine laufende Session existiert, passiert nichts.
        """
        scores = _load_scores()
        if spieler not in scores or not scores[spieler]["sessions"]:
            return {"status": "error", "message": f"Keine Session für Spieler '{spieler}' gefunden."}

        # Letzte Session auswählen
        last_session = scores[spieler]["sessions"][-1]

        if last_session.get("status") == "laufend":
            last_session["status"] = "abgeschlossen"
            last_session["datumEnde"] = datetime.datetime.utcnow().isoformat()
            _save_scores(scores)
            return {"status": "ok", "message": "Session abgeschlossen", "session": last_session}
        else:
            return {"status": "ok", "message": f"Letzte Session ist bereits '{last_session.get('status')}'.", "session": last_session}


@router.post("/abortSession")
def abort_session(spieler: str = Body(...)) -> Dict[str, Any]:
    """
    Markiert die letzte Session des Spielers als 'abgebrochen'.
    Falls keine laufende Session existiert, passiert nichts.
    """
    scores = _load_scores()
    if spieler not in scores or not scores[spieler]["sessions"]:
        return {"status": "error", "message": f"Keine Session für Spieler '{spieler}' gefunden."}

    # Letzte Session auswählen
    last_session = scores[spieler]["sessions"][-1]

    if last_session.get("status") == "laufend":
        last_session["status"] = "abgebrochen"
        last_session["datumEnde"] = datetime.datetime.utcnow().isoformat()
        _save_scores(scores)
        return {"status": "ok", "message": "Session abgebrochen", "session": last_session}
    else:
        return {"status": "ok", "message": f"Letzte Session ist bereits '{last_session.get('status')}'.", "session": last_session}

@router.get("/")
def root():
    return {"status": "ok", "message": "Zahlenpirat Backend läuft 🎉"}
