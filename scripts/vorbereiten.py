"""Schritt 3 - Uebersetzungsdateien anlegen (leer, zum Ausfuellen).

Fasst alle gefundenen Texte zu einer Liste ohne Doppelungen zusammen und legt fuer
die Zielsprache zwei Dateien an:

    uebersetzung_<code>.json   Oberflaechentexte: "deutsch": "" -> Zielsprache eintragen
    sprechtexte_<code>.json    Sprechtexte je Video: "text": "" -> Zielsprache eintragen

Beide werden von Claude ausgefuellt (oder von Hand, etwa von einer Muttersprachlerin).
Vorhandene Eintraege bleiben erhalten - erneuter Aufruf ergaenzt nur Fehlendes.

Aufruf:  python vorbereiten.py <arbeitsordner> <sprachcode>
"""
import json
import os
import sys


def main(ordner, code):
    texte = json.load(open(os.path.join(ordner, "texte_de.json"), encoding="utf-8"))

    # Oberflaechentexte: eindeutige Strings, nach Haeufigkeit sortiert
    eindeutig = {}
    for t in texte:
        eindeutig.setdefault(t["text"], []).append(t["feld"])
    ziel = os.path.join(ordner, "uebersetzung_%s.json" % code)
    alt = json.load(open(ziel, encoding="utf-8")) if os.path.exists(ziel) else {}
    neu = {k: alt.get(k, "") for k in eindeutig}
    with open(ziel, "w", encoding="utf-8") as fh:
        json.dump(neu, fh, ensure_ascii=False, indent=1)

    # Sprechtexte
    quelle = os.path.join(ordner, "sprechtexte_de.json")
    if os.path.exists(quelle):
        de = json.load(open(quelle, encoding="utf-8"))
        zielsp = os.path.join(ordner, "sprechtexte_%s.json" % code)
        altsp = json.load(open(zielsp, encoding="utf-8")) if os.path.exists(zielsp) else {}
        neusp = {k: {"nr": v["nr"], "dauer": v["dauer"],
                     "deutsch": v["text"], "text": altsp.get(k, {}).get("text", "")}
                 for k, v in de.items()}
        with open(zielsp, "w", encoding="utf-8") as fh:
            json.dump(neusp, fh, ensure_ascii=False, indent=1)
        offen_sp = sum(1 for v in neusp.values() if not v["text"])
    else:
        offen_sp = "(noch keine Transkripte)"

    offen = sum(1 for v in neu.values() if not v)
    print("uebersetzung_%s.json : %d Texte, davon %d offen" % (code, len(neu), offen))
    print("sprechtexte_%s.json  : %s offen" % (code, offen_sp))
    print("\nBeide Dateien ausfuellen, dann Schritt 4 (vertonen.py).")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
