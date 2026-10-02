# wissensbasis.py
# Einfache, lokale Wissensbasis (RAG) ohne Datenbank.
# Dokumente (PDF/TXT) liegen im Ordner "wissen", der Index in wissen/index.json.

import json
import math
from pathlib import Path

import ollama

client = ollama.Client(host="http://127.0.0.1:11434")

EMBED_MODELL = "bge-m3"
WISSEN_ORDNER = Path("wissen")
INDEX_DATEI = WISSEN_ORDNER / "index.json"
WISSEN_ORDNER.mkdir(exist_ok=True)

RAG_PROMPT = """Du bist ein Assistent für deutsches und europäisches Patentrecht.
Beantworte die Frage AUSSCHLIESSLICH auf Grundlage der nummerierten Auszüge.
- Nenne nach jeder Aussage die Quelle in eckigen Klammern, z. B. [1] oder [2].
- Nenne Paragraphen oder Artikel nur, wenn sie in den Auszügen stehen.
- Steht die Antwort nicht in den Auszügen, schreibe genau:
  "Dazu enthalten die vorliegenden Dokumente keine Information."
- Antworte sachlich, kurz und in korrektem Deutsch. Kein Rechtsrat."""

_cache = {"zeit": None, "daten": []}


# ---------- Dokumente einlesen ----------

def wissens_dateien():
    """Alle PDF- und TXT-Dateien im Ordner 'wissen'."""
    return sorted(p for p in WISSEN_ORDNER.iterdir()
                  if p.suffix.lower() in (".pdf", ".txt"))


def text_laden(datei):
    if datei.suffix.lower() == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(str(datei))
        return "\n".join(seite.extract_text() or "" for seite in reader.pages)
    return datei.read_text(encoding="utf-8", errors="ignore")


def zerlegen(text, groesse=1000, ueberlappung=150):
    """Teilt einen langen Text in überlappende Abschnitte (möglichst am Satzende)."""
    text = " ".join(text.split())
    stuecke, start = [], 0
    while start < len(text):
        ende = min(start + groesse, len(text))
        if ende < len(text):
            punkt = text.rfind(". ", start + groesse // 2, ende)
            if punkt != -1:
                ende = punkt + 1
        stuecke.append(text[start:ende].strip())
        if ende >= len(text):
            break
        start = max(ende - ueberlappung, start + 1)
    return stuecke

def absaetze(text):
    """Für Regeldateien: jeder durch Leerzeile getrennte Block ist ein Abschnitt.
    Leerzeilen mit unsichtbaren Leerzeichen werden ebenfalls erkannt."""
    import re
    bloecke = re.split(r"\n\s*\n", text.replace("\r\n", "\n"))
    return [" ".join(b.split()) for b in bloecke if b.strip()]


def normieren(vektor):
    laenge = math.sqrt(sum(x * x for x in vektor)) or 1.0
    return [round(x / laenge, 5) for x in vektor]


# ---------- Index aufbauen ----------

def index_aufbauen(fortschritt=None, stapel=16):
    """Liest alle Dokumente, erzeugt Embeddings und speichert den Index.
    fortschritt: optionale Funktion, die einen Wert zwischen 0 und 1 bekommt."""
    abschnitte = []
    for datei in wissens_dateien():
        text = text_laden(datei)
        teile = absaetze(text) if datei.suffix.lower() == ".txt" else zerlegen(text)
        for teil in teile:
            abschnitte.append({"quelle": datei.stem, "text": teil})

    for i in range(0, len(abschnitte), stapel):
        gruppe = abschnitte[i:i + stapel]
        antwort = client.embed(model=EMBED_MODELL, input=[a["text"] for a in gruppe])
        for abschnitt, vektor in zip(gruppe, antwort["embeddings"]):
            abschnitt["vektor"] = normieren(vektor)
        if fortschritt:
            fortschritt(min(1.0, (i + stapel) / len(abschnitte)))

    INDEX_DATEI.write_text(json.dumps(abschnitte, ensure_ascii=False), encoding="utf-8")
    return len(abschnitte)


def index_laden():
    """Lädt den Index (mit Zwischenspeicher, solange die Datei unverändert ist)."""
    if not INDEX_DATEI.exists():
        return []
    zeit = INDEX_DATEI.stat().st_mtime
    if _cache["zeit"] != zeit:
        _cache["daten"] = json.loads(INDEX_DATEI.read_text(encoding="utf-8"))
        _cache["zeit"] = zeit
    return _cache["daten"]


def index_info():
    daten = index_laden()
    if not daten:
        return "Noch kein Index vorhanden."
    zaehler = {}
    for d in daten:
        zaehler[d["quelle"]] = zaehler.get(d["quelle"], 0) + 1
    teile = [f"{q}: {n}" for q, n in sorted(zaehler.items())]
    return f"Index: {len(daten)} Abschnitte ({', '.join(teile)})"


# ---------- Suchen ----------

def suchen(frage, k=4):
    """Gibt die k Abschnitte zurück, die inhaltlich am besten zur Frage passen."""
    daten = index_laden()
    if not daten:
        return []
    frage_vektor = normieren(client.embed(model=EMBED_MODELL, input=frage)["embeddings"][0])
    bewertet = [
        (sum(a * b for a, b in zip(frage_vektor, d["vektor"])), d) for d in daten
    ]
    bewertet.sort(key=lambda x: x[0], reverse=True)
    return [{"quelle": d["quelle"], "text": d["text"], "score": s}
            for s, d in bewertet[:k]]