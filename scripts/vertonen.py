"""Schritt 4 - Sprechtexte vertonen (Microsoft Edge TTS, kostenlos, braucht Internet).

Erzeugt je Video eine Tonaufnahme in audio_<code>/. Bereits vorhandene Dateien werden
NICHT ueberschrieben - wer eigene Aufnahmen hat (HeyGen, selbst gesprochen), legt sie
vorher unter demselben Dateinamen dort ab.

Aufruf:  python vertonen.py <arbeitsordner> <sprachcode> <stimme> [--tempo +10%]
         Stimmen auflisten:  edge-tts --list-voices | grep ^fr-FR

Stimme passend zum Avatar waehlen (maennlich/weiblich) - der Ton liegt spaeter auf dem
Originalbild. Tempo nur im Notfall aendern: langsam ist fuer Sprachlernende besser.
"""
import json
import os
import re
import subprocess
import sys


def main(ordner, code, stimme, tempo=None):
    quelle = os.path.join(ordner, "sprechtexte_%s.json" % code)
    if not os.path.exists(quelle):
        sys.exit("Fehlt: %s - erst vorbereiten.py und uebersetzen." % quelle)
    texte = json.load(open(quelle, encoding="utf-8"))
    zielordner = os.path.join(ordner, "audio_%s" % code)
    os.makedirs(zielordner, exist_ok=True)

    offen = [k for k, v in texte.items() if not v.get("text")]
    if offen:
        sys.exit("Noch nicht uebersetzt: %d von %d Sprechtexten (%s ...)" %
                 (len(offen), len(texte), offen[0]))

    for name in sorted(texte, key=lambda k: texte[k]["nr"]):
        e = texte[name]
        ziel = os.path.join(zielordner, os.path.splitext(name)[0] + ".mp3")
        if os.path.exists(ziel) and os.path.getsize(ziel) > 5000:
            print("vorhanden, bleibt:", os.path.basename(ziel))
            continue
        text = re.sub(r"[\U0001F300-\U0001FAFF☀-➿️]", "", e["text"])
        text = re.sub(r"\s+", " ", text).strip()
        befehl = ["edge-tts", "--voice", stimme, "--text", text, "--write-media", ziel]
        if tempo:
            befehl += ["--rate", tempo]
        r = subprocess.run(befehl, capture_output=True, text=True)
        ok = r.returncode == 0 and os.path.exists(ziel)
        print("%-34s %s %s" % (os.path.basename(ziel), "ok" if ok else "FEHLER",
                               "%d KB" % (os.path.getsize(ziel) // 1024) if ok else r.stderr[:120]))


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
