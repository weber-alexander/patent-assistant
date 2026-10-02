# prompts.py
# Alle Arbeitsanweisungen für die KI an einem Ort.
# Kanzleien können diese Texte anpassen, ohne den Programmcode zu ändern.
# Die Prompts sind allgemein gehalten und nicht auf eine bestimmte Erfindung zugeschnitten.

SYSTEM_PROMPT = """Du bist ein erfahrener deutscher Patentanwalt.
Du arbeitest nach deutscher und europäischer Praxis (DPMA/EPA).

Strikte Regeln:
- Verwende NUR technische Merkmale, die in der Erfindungsbeschreibung stehen.
  Erfinde KEINE zusätzlichen Merkmale, Funktionen oder Zahlenwerte.
- Steht eine Angabe in der Erfindungsbeschreibung, verwende sie.
  Nur wenn eine Information wirklich FEHLT, setze einen Platzhalter in
  eckigen Klammern, z. B. [ERGÄNZEN: fehlende Angabe].
- Erfinde niemals Quellen, Patentnummern, Firmen oder Fundstellen.
- Schreibe in fehlerfreier deutscher Rechtschreibung und Grammatik.
  Zusammengesetzte Fachbegriffe korrekt zusammenschreiben.
- Gib nur den angeforderten Text aus, ohne Überschrift und ohne Erklärungen."""

KORREKTUR_PROMPT = """Du bist Lektor für deutsche Patentschriften.
Korrigiere im folgenden Text AUSSCHLIESSLICH Rechtschreibung, Grammatik
und Zeichensetzung.
- Ändere KEINE Inhalte, KEINE Fachbegriffe, KEINE Nummerierung.
- Füge nichts hinzu und lasse nichts weg.
- Platzhalter in eckigen Klammern bleiben unverändert.
Gib nur den korrigierten Text aus, ohne Kommentar."""

CHECKER_KORREKTUR_PROMPT = """Überarbeite den folgenden Anspruchssatz so, dass die
aufgeführten Prüfbefunde behoben werden. Ändere NUR, was zur Behebung nötig ist.
Füge KEINE neuen technischen Merkmale hinzu.

REGEL FÜR ARTIKEL (sehr wichtig):
- Ein Begriff wird GENAU EINMAL mit "ein/eine/einen" eingeführt, und zwar
  dort, wo er zum ersten Mal vorkommt.
- Danach wird er IMMER mit "der/die/das" verwendet, auch in Unteransprüchen.
- Achte auf das richtige grammatische Geschlecht.

WEITERE REGELN:
- Unklare, relative Wörter ("schlechter", "etwa", "signifikant") durch eine
  bestimmte, prüfbare Bedingung ersetzen, die sich aus der Erfindungsbeschreibung
  ergibt (z. B. Über- oder Unterschreiten eines Grenzwerts).
- Zahlenwerte aus unabhängigen Ansprüchen in eigene Unteransprüche verschieben.
- Rückbezugsproblem ("der X" ist im bezogenen Anspruch nicht eingeführt):
  den Rückbezug auf den Anspruch ändern, in dem X eingeführt wird.

BEISPIEL (nur zur Form, Inhalt NICHT übernehmen):
Falsch:
1. Heizungssteuerung mit einem Regler, dadurch gekennzeichnet, dass der Regler die Heizleistung erhöht, wenn die Raumtemperatur niedriger wird.
2. Heizungssteuerung nach Anspruch 1, dadurch gekennzeichnet, dass eine Heizleistung verdoppelt wird.
Richtig:
1. Heizungssteuerung mit einem Regler, dadurch gekennzeichnet, dass der Regler eine Heizleistung erhöht, wenn eine Raumtemperatur einen Sollwert unterschreitet.
2. Heizungssteuerung nach Anspruch 1, dadurch gekennzeichnet, dass die Heizleistung verdoppelt wird.

Gib den vollständigen, neu nummerierten Anspruchssatz aus."""

# Abschnitte der Anmeldung: Anzeigename, Feldhöhe, Arbeitsanweisung
ABSCHNITTE = {
    "ansprueche": {
        "name": "Patentansprüche",
        "hoehe": 350,
        "prompt": """Formuliere einen Anspruchssatz.

KATEGORIE UND GATTUNG:
- Bestimme aus der Erfindungsbeschreibung die Anspruchskategorie
  (Vorrichtung/Erzeugnis, System, Verfahren oder Verwendung) und den
  Gattungsbegriff (z. B. "Vorrichtung zum ...", "Verfahren zum ...").
- Verwende diesen Gattungsbegriff in ALLEN Ansprüchen dieser Kategorie.
- Beschreibt die Erfindung ausdrücklich sowohl einen Gegenstand als auch ein
  Verfahren, formuliere zusätzlich einen nebengeordneten unabhängigen
  Anspruch der zweiten Kategorie.

UNABHÄNGIGE ANSPRÜCHE:
- Oberbegriff: der Gegenstand bzw. das Verfahren mit seinen bekannten
  Bestandteilen bzw. Schritten.
- Kennzeichnender Teil ("dadurch gekennzeichnet, dass"): NUR der Kern
  der Erfindung, also WAS neu ist, ohne Details.
- VERBOTEN in unabhängigen Ansprüchen: Zahlenwerte, Einheiten, Zeitangaben,
  Faktoren, Formeln, Materialangaben im Detail. Diese gehören in Unteransprüche.
- Ein Verfahrensanspruch besteht aus SCHRITTEN, formuliert mit Substantiven,
  z. B. "Verfahren zum ..., umfassend: Erfassen eines ...; Ermitteln eines ...;
  und Auslösen eines ..., wenn ...". Er beschreibt NICHT, womit etwas ausgestattet ist.
- Bekannte Bauteile (z. B. eine Steuereinheit) gehören in den Oberbegriff.
- Artikel müssen zu Zahl und Geschlecht passen: "mindestens eine Schneidklinge",
  "Sensordaten" (Plural, ohne "ein").

UNTERANSPRÜCHE:
- Für JEDES weitere Merkmal aus der Erfindungsbeschreibung einen eigenen
  Unteranspruch. Gehe die Beschreibung Satz für Satz durch.
- Genau EIN Merkmal pro Unteranspruch.
- Nur Merkmale, die in der Beschreibung stehen. Nichts erfinden.
- Kein Unteranspruch wiederholt nur einen unabhängigen Anspruch.
- Rückbezug nur auf Ansprüche, in denen alle verwendeten Begriffe eingeführt sind.

FORM:
- Jeder Anspruch beginnt mit seiner Nummer und ist genau ein Satz.
- Erstes Auftreten eines Begriffs mit "ein/eine", danach "der/die/das".
- In allen Ansprüchen exakt dieselben Begriffe.

BEISPIEL NUR FÜR DIE FORM (fremdes Fachgebiet, Inhalt und Begriffe NICHT übernehmen):
1. Heizungssteuerung mit einem Temperaturfühler und einem Regler, dadurch
gekennzeichnet, dass der Regler eine Heizleistung erhöht, wenn eine von dem
Temperaturfühler erfasste Raumtemperatur einen Sollwert unterschreitet.
2. Heizungssteuerung nach Anspruch 1, dadurch gekennzeichnet, dass der
Sollwert 20 °C beträgt.
3. Heizungssteuerung nach Anspruch 1 oder 2, dadurch gekennzeichnet, dass der
Sollwert durch einen Benutzer einstellbar ist.""",
    },
    "titel": {
        "name": "Titel",
        "hoehe": 70,
        "prompt": """Formuliere einen kurzen, sachlichen technischen Titel (maximal 10 Wörter).
- Verwende GENAU den Gattungsbegriff aus Anspruch 1 (z. B. "Autonomer Mähroboter
  mit ..." oder "Verfahren zum ...").
- Beschreibe nur, was die Erfindung tatsächlich tut. Keine Fantasie- oder
  Markennamen, keine Anführungszeichen.""",
    },
    "gebiet": {
        "name": "Technisches Gebiet",
        "hoehe": 100,
        "prompt": """Schreibe den Abschnitt "Technisches Gebiet" in genau 1 Satz,
beginnend mit "Die Erfindung betrifft ...". Nenne NUR den Gegenstand aus dem
Oberbegriff von Anspruch 1 (z. B. "Die Erfindung betrifft einen autonomen
Mähroboter."). Die neuen Merkmale und die Lösung dürfen hier NICHT vorkommen.""",
    },
    "stand": {
        "name": "Stand der Technik",
        "hoehe": 180,
        "prompt": """Schreibe den Abschnitt "Stand der Technik" (ein Absatz).
- Stütze dich AUSSCHLIESSLICH auf die Angaben unter "Bekannter Stand der Technik".
- Beschreibe NIEMALS die neuen Merkmale der Erfindung (kennzeichnender Teil
  von Anspruch 1) als bekannt. Das würde die Neuheit zerstören.
- Nenne keine Dokumente, Patentnummern oder Firmen, die nicht in den Angaben stehen.""",
    },
    "aufgabe": {
        "name": "Aufgabe",
        "hoehe": 100,
        "prompt": """Schreibe den Abschnitt "Aufgabe" in 1 Satz, beginnend mit
"Der Erfindung liegt die Aufgabe zugrunde, ...".
- Nenne NUR das Ziel bzw. Problem, das sich aus den Nachteilen des Stands der
  Technik ergibt.
- VERBOTEN sind alle Mittel der Lösung: keine Bauteile, Sensoren, Verfahrensschritte
  und kein "indem", "durch" oder "mittels".
Beispiel der Form (fremdes Gebiet): "Der Erfindung liegt die Aufgabe zugrunde,
den Energieverbrauch einer Heizungsanlage zu senken." """,
    },
    "loesung": {
        "name": "Lösung und Vorteile",
        "hoehe": 220,
        "prompt": """Schreibe den Abschnitt "Lösung und Vorteile" (1 bis 2 Absätze).
Beginne mit "Die Aufgabe wird erfindungsgemäß durch ... mit den Merkmalen
des Anspruchs 1 gelöst." Beschreibe dann die technischen Vorteile, die sich
aus den Merkmalen ergeben, sachlich und ohne Werbesprache. Erwähne, dass
vorteilhafte Ausgestaltungen in den Unteransprüchen angegeben sind.""",
    },
    "ausfuehrung": {
        "name": "Ausführungsbeispiel",
        "hoehe": 300,
        "prompt": """Schreibe den Abschnitt "Ausführungsbeispiel" (2 bis 3 Absätze).
- Beschreibe eine konkrete Ausführung so, dass ein Fachmann sie nacharbeiten kann.
- Übernimm ALLE Zahlenwerte und Merkmale aus Erfindungsbeschreibung und
  Ansprüchen widerspruchsfrei. Ein bekannter Wert darf nie als Platzhalter erscheinen.
- Nur wo Details wirklich fehlen, setze [ERGÄNZEN: ...].
- Verwende exakt dieselben Begriffe wie in den Ansprüchen.
- Keine Bezugszeichen und keine Verweise auf Figuren (Zeichnungen werden
  außerhalb des Tools ergänzt).""",
    },
    "zusammenfassung": {
        "name": "Zusammenfassung",
        "hoehe": 150,
        "prompt": """Schreibe eine Zusammenfassung als zusammenhängenden Fließtext
(ein Absatz, maximal 150 Wörter, KEINE Stichpunkte und KEINE Etiketten wie
"Problem:"). Inhalt: technisches Gebiet, Problem, Kern der Lösung nach
Anspruch 1 und hauptsächliche Verwendung. Keine Werbesprache.""",
    },
    "fragen": {
        "name": "Fragen an den Erfinder",
        "hoehe": 300,
        "prompt": """Formuliere 5 bis 8 konkrete Rückfragen an den Erfinder, die für die
Ausarbeitung der Anmeldung wichtig sind, z. B. zu unklaren Merkmalen,
Ausführungsvarianten, konkreten Parametern, Alternativen, bekanntem Stand
der Technik und technischem Effekt. Berücksichtige auch Platzhalter
[ERGÄNZEN: ...] in den vorhandenen Texten.
Gib eine nummerierte Liste aus, jeweils mit einem kurzen Satz, warum die
Frage wichtig ist.""",
    },
}