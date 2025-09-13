# C:\Users\mnold_t1ohvc3\Documents\zahlenpirat-backend\utils_text.py
import unicodedata

def _is_emoji(ch: str) -> bool:
    o = ord(ch)
    return (
        0x1F300 <= o <= 0x1FAFF  # Emoji Blocks
        or 0x2600 <= o <= 0x26FF # Misc symbols
        or 0x2700 <= o <= 0x27BF # Dingbats
        or o in (0xFE0F, 0x20E3) # Variation selector, keycap
    )

def strip_emoji(text: str) -> str:
    return "".join(ch for ch in text if not _is_emoji(ch))

# ! ASCII-sichere Plain-Funktion: Umlaute, Bullets, typografische Zeichen
def to_plain(text: str) -> str:
    t = strip_emoji(text)

    # gezielte Ersetzungen vor der ASCII-Normalisierung
    replacements = {
        # typografisch
        "„": '"', "“": '"', "‚": "'", "’": "'", "…": "...", "—": "-", "–": "-",
        "•": "- ", "·": "-", "×": "x", "÷": "/",
        # Pfeile/Symbole (falls mal auftauchen)
        "→": "->", "←": "<-", "±": "+/-",
        # deutsche Umlaute -> ASCII
        "Ä": "Ae", "Ö": "Oe", "Ü": "Ue", "ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss",
        # geschützte Leerzeichen
        "\u00A0": " ",
    }
    for src, dst in replacements.items():
        t = t.replace(src, dst)

    # Restliche Nicht-ASCII-Zeichen defensiv entfernen
    # (z. B. wenn etwas Ungewöhnliches durchrutscht)
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode("ascii")

    # Zeilenenden und Mehrfach-Leerzeichen hübsch machen
    # (ohne fancy Unicode, damit PS5.1 es sicher darstellt)
    t = "\n".join(line.rstrip() for line in t.splitlines())
    while "  " in t:
        t = t.replace("  ", " ")

    return t
