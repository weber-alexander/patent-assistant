# anspruchs_checker.py
# Regelbasierte Prüfung von Patentansprüchen – ganz ohne KI.
# Test im Terminal: python anspruchs_checker.py

import re
from dataclasses import dataclass


@dataclass
class Befund:
    stufe: str          # "Fehler", "Warnung" oder "Hinweis"
    anspruch: int       # Nummer des Anspruchs (0 = ganzer Anspruchssatz)
    text: str


# Unklare Begriffe, die Prüfer typischerweise beanstanden
UNKLARE_WOERTER = [
    "schlechter", "besser", "signifikant", "erheblich", "ungefähr", "etwa",
    "möglichst", "vorzugsweise", "beispielsweise", "z. B.", "insbesondere",
    "relativ", "deutlich",
]

# Anfang eines Anspruchs: Zeile beginnt mit "1. ", "2. " ...
ANSPRUCH_START = re.compile(r"(?m)^\s*(\d+)\.\s+")

# "ein Sensor", "einer Steuereinheit" ... = Einführung eines Begriffs
EINFUEHRUNG = re.compile(
    r"\b(?i:ein|eine|einen|einem|einer|eines)\s+([A-ZÄÖÜ][\w-]+)")

# "der Sensor", "die Abtastrate" ... = Verweis auf einen eingeführten Begriff
BEZUG = re.compile(
    r"\b(?i:der|die|das|den|dem|des)\s+([A-ZÄÖÜ][\w-]+)")

AUSNAHMEN = {"anspruch", "ansprüche", "ansprüchen", "erfindung"}


# ---------- Hilfsfunktionen ----------

def zerlegen(text):
    """Teilt den Anspruchssatz in [(nummer, text), ...]."""
    treffer = list(ANSPRUCH_START.finditer(text))
    ergebnis = []
    for i, m in enumerate(treffer):
        ende = treffer[i + 1].start() if i + 1 < len(treffer) else len(text)
        inhalt = " ".join(text[m.end():ende].split())
        ergebnis.append((int(m.group(1)), inhalt))
    return ergebnis


def rueckbezuege(nr, text):
    """Findet, auf welche Ansprüche sich ein Anspruch bezieht."""
    kopf = re.split(r"dadurch gekennzeichnet|wobei", text)[0]
    if re.search(r"nach einem der vorhergehenden Ansprüche", kopf):
        return list(range(1, nr))
    m = re.search(r"nach einem der Ansprüche (\d+) bis (\d+)", kopf)
    if m:
        return list(range(int(m.group(1)), int(m.group(2)) + 1))
    # "Anspruch" (u) UND "Ansprüche/Ansprüchen" (ü) erkennen
    m = re.search(r"nach (?:einem der |den )?Anspr(?:uch|üchen|üche) "
                  r"((?:\d+(?:\s*,\s*|\s+oder\s+|\s+und\s+)?)+)", kopf)
    if m:
        return [int(z) for z in re.findall(r"\d+", m.group(1))]
    return []


def gleich(a, b):
    """Vergleicht Begriffe tolerant gegenüber Endungen (Sensor/Sensors)."""
    a, b = a.lower(), b.lower()
    if a == b:
        return True
    kurz, lang = sorted([a, b], key=len)
    return lang.startswith(kurz) and len(lang) - len(kurz) <= 3


def enthalten(wort, menge):
    return any(gleich(wort, x) for x in menge)


# ---------- Hauptfunktion ----------

def pruefen(text):
    """Prüft einen Anspruchssatz und gibt eine Liste von Befunden zurück."""
    befunde = []
    ansprueche = zerlegen(text)
    if not ansprueche:
        if text.strip():
            befunde.append(Befund("Fehler", 0, "Keine nummerierten Ansprüche erkannt. "
                                  "Jeder Anspruch muss mit '1.', '2.' ... beginnen."))
        return befunde

    nummern = [nr for nr, _ in ansprueche]

    # 1) Nummerierung
    if nummern != list(range(1, len(nummern) + 1)):
        befunde.append(Befund("Fehler", 0,
                              f"Nummerierung nicht fortlaufend: {nummern}."))

    # Wo wird jeder Begriff irgendwo eingeführt? (für bessere Meldungen)
    eingefuehrt_in = {}
    for nr, t in ansprueche:
        for m in EINFUEHRUNG.finditer(t):
            eingefuehrt_in.setdefault(m.group(1), nr)

    verfuegbar = {}          # Anspruch -> Begriffe, die dort bekannt sind
    nie_gemeldet = set()     # nie eingeführte Begriffe nur einmal melden

    for nr, t in ansprueche:
        refs = rueckbezuege(nr, t)

        # 2) Rückbezüge
        if nr == 1 and refs:
            befunde.append(Befund("Fehler", nr,
                                  "Anspruch 1 darf sich auf keinen anderen Anspruch beziehen."))
        gueltige = []
        for r in refs:
            if r not in nummern:
                befunde.append(Befund("Fehler", nr,
                                      f"Rückbezug auf Anspruch {r}, den es nicht gibt."))
            elif r >= nr:
                befunde.append(Befund("Fehler", nr,
                                      f"Rückbezug auf Anspruch {r}. Rückbezüge sind nur "
                                      "auf vorhergehende Ansprüche zulässig."))
            else:
                gueltige.append(r)

        # 3) Unabhängiger Anspruch: Zahlen und zweiteilige Form
        if not refs:
            zahlen = re.findall(r"\d+(?:[.,]\d+)?\s*(?:°C|%|[a-zA-Zµ]{1,3}\b)?", t)
            if zahlen:
                befunde.append(Befund("Warnung", nr,
                                      f"Enthält Zahlenwerte ({', '.join(z.strip() for z in zahlen)}). "
                                      "Das engt den Schutz ein. Besser in Unteransprüche verschieben."))
            if "dadurch gekennzeichnet" not in t and "wobei" not in t:
                befunde.append(Befund("Hinweis", nr,
                                      "Keine zweiteilige Form ('dadurch gekennzeichnet, dass' "
                                      "oder 'wobei') erkannt."))

        # 4) Unklare Wörter
        for wort in UNKLARE_WOERTER:
            if re.search(r"\b" + re.escape(wort) + r"\b", t, re.IGNORECASE):
                befunde.append(Befund("Warnung", nr,
                                      f"Unklarer Begriff '{wort}'. Prüfer verlangen "
                                      "bestimmte Angaben (z. B. Schwellenwert)."))

        # 5) Begriffseinführung: bekannt ist nur, was in ALLEN bezogenen
        #    Ansprüchen verfügbar ist (bei "nach einem der Ansprüche ...")
        geerbt = None
        for r in gueltige:
            s = verfuegbar.get(r, set())
            geerbt = set(s) if geerbt is None else {x for x in geerbt if enthalten(x, s)}
        geerbt = geerbt or set()

        einfuehrungen = [(m.start(), m.group(1)) for m in EINFUEHRUNG.finditer(t)]
        bekannt_hier = set(geerbt)
        # 6) Doppelte Einführung: "ein X", obwohl X schon bekannt ist
        gesehen = set(geerbt)
        for _, wort in einfuehrungen:
            if enthalten(wort, gesehen):
                befunde.append(Befund("Warnung", nr,
                                      f"'{wort}' wird erneut mit 'ein/eine' eingeführt, obwohl "
                                      "der Begriff schon bekannt ist. Das wirkt, als wäre ein "
                                      f"anderer {wort} gemeint. Hier 'der/die/das' verwenden."))
            gesehen.add(wort)

        for m in BEZUG.finditer(t):
            wort = m.group(1)
            if wort.lower() in AUSNAHMEN:
                continue
            bekannt = bekannt_hier | {w for pos, w in einfuehrungen if pos < m.start()}
            if enthalten(wort, bekannt):
                continue

            irgendwo = next((n for w, n in eingefuehrt_in.items() if gleich(w, wort)), None)
            if irgendwo:
                befunde.append(Befund("Fehler", nr,
                                      f"'{m.group(0)}' verweist auf einen Begriff, der erst in "
                                      f"Anspruch {irgendwo} eingeführt wird und nicht in allen "
                                      "bezogenen Ansprüchen vorkommt (Rückbezugsproblem)."))
            elif not enthalten(wort, nie_gemeldet):
                befunde.append(Befund("Warnung", nr,
                                      f"'{m.group(0)}' wird nie mit 'ein/eine' eingeführt. "
                                      f"Beim ersten Auftreten sollte es z. B. 'ein/eine {wort}' heißen."))
                nie_gemeldet.add(wort)
            bekannt_hier.add(wort)   # nur einmal pro Kette melden

        verfuegbar[nr] = bekannt_hier | {w for _, w in einfuehrungen}

    return befunde


