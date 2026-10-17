"""Schritt 2 - Sprechtexte aus den Videos holen (laeuft lokal, nichts geht ins Netz).

Transkribiert die in Schritt 1 abgetrennten Tonspuren mit faster-whisper und legt ab:

    sprechtexte_de.json   Text je Video, mit Dauer
    sprechtexte_de.md     dasselbe zum Lesen

Aufruf:  python transkribieren.py <arbeitsordner> [sprachkuerzel] [modell]
         sprachkuerzel: Sprache der Originalvideos (Vorgabe de)
         modell: tiny|base|small|medium|large-v3 (Vorgabe medium)

Dauer: etwa das Doppelte der Spielzeit auf einer normalen CPU.
"""
import json
import os
import sys
import time


def main(ordner, sprache="de", modellname="medium"):
    from faster_whisper import WhisperModel

    kurs = json.load(open(os.path.join(ordner, "kurs.json"), encoding="utf-8"))
    ziel = os.path.join(ordner, "sprechtexte_%s.json" % sprache)
    ergebnis = json.load(open(ziel, encoding="utf-8")) if os.path.exists(ziel) else {}

    modell = WhisperModel(modellname, device="cpu", compute_type="int8", cpu_threads=os.cpu_count())
    for v in kurs["videos"]:
        if not v["hat_ton"] or v["datei"] in ergebnis:
            continue
        pfad = os.path.join(ordner, "audio_%s" % sprache, v["ton"])
        t0 = time.time()
        teile, info = modell.transcribe(pfad, language=sprache, beam_size=5, vad_filter=True)
        text = " ".join(s.text.strip() for s in teile).strip()
        ergebnis[v["datei"]] = {"nr": v["nr"], "dauer": round(info.duration, 1), "text": text}
        with open(ziel, "w", encoding="utf-8") as fh:
            json.dump(ergebnis, fh, ensure_ascii=False, indent=1)
        print("[%3.0fs] %-34s %4.0fs  %s" % (time.time() - t0, v["datei"][:34], info.duration, text[:70]),
              flush=True)

    md = ["# Sprechtexte der Videos (%s)\n" % sprache.upper()]
    for k in sorted(ergebnis, key=lambda k: ergebnis[k]["nr"]):
        e = ergebnis[k]
        md.append("\n## %02d - %s\n*%.0f Sekunden*\n\n%s\n" % (e["nr"], k, e["dauer"], e["text"]))
    with open(os.path.join(ordner, "sprechtexte_%s.md" % sprache), "w", encoding="utf-8") as fh:
        fh.write("\n".join(md))
    print("\nFertig: %d Videos, %.1f Minuten" % (len(ergebnis), sum(e["dauer"] for e in ergebnis.values()) / 60))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(*sys.argv[1:4])
