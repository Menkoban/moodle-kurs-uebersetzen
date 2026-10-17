"""Schritt 5 - Neue Videos: Originalbild mit neuem Ton.

Der Ton bleibt unangetastet, das Bild wird auf die Tonlaenge gebracht (setpts).
Begruendung: Verstaendlichkeit geht vor Bildtempo; lippensynchron wird es beim
Tonaustausch ohnehin nicht.

    Ton laenger  -> Bild laeuft langsamer
    Ton kuerzer  -> Bild laeuft schneller (mit --grenze begrenzbar, Rest wird Stille)

Aufruf:  python videos_bauen.py <arbeitsordner> <sprachcode> [--grenze 0.85]
         --grenze: staerkste erlaubte Bildraffung (0.85 = hoechstens 15 % schneller)
"""
import json
import os
import subprocess
import sys
import time


def dauer(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", p], capture_output=True, text=True)
    return float(r.stdout.strip())


def main(ordner, code, grenze=None):
    kurs = json.load(open(os.path.join(ordner, "kurs.json"), encoding="utf-8"))
    aus = os.path.join(ordner, "videos_%s" % code)
    os.makedirs(aus, exist_ok=True)
    fehlt = []
    for v in kurs["videos"]:
        quelle = os.path.join(ordner, "videos", v["datei"])
        ton = os.path.join(ordner, "audio_%s" % code, os.path.splitext(v["datei"])[0] + ".mp3")
        ziel = os.path.join(aus, v["datei"])
        if not os.path.exists(ton):
            fehlt.append(os.path.basename(ton))
            continue
        if os.path.exists(ziel) and os.path.getsize(ziel) > 100000:
            print("vorhanden, bleibt:", v["datei"])
            continue
        dv, da = dauer(quelle), dauer(ton)
        faktor = da / dv
        stille = 0.0
        if grenze and faktor < grenze:            # Bild nicht staerker raffen als erlaubt
            stille = dv * grenze - da
            faktor = grenze
        af = "apad=pad_dur=%.3f" % stille if stille > 0.05 else "anull"
        t0 = time.time()
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", quelle, "-i", ton,
                        "-filter_complex", "[0:v]setpts=%.6f*PTS,fps=25[v];[1:a]%s[a]" % (faktor, af),
                        "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "fast",
                        "-crf", "22", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
                        "-movflags", "+faststart", "-shortest", ziel], check=True)
        print("%-34s Bild %5.1f -> %5.1f s (%+3.0f%%)%s | %2.0fs | %d MB" %
              (v["datei"][:34], dv, dv * faktor, (faktor - 1) * 100,
               "  +%.1fs Stille" % stille if stille > 0.05 else "",
               time.time() - t0, os.path.getsize(ziel) // 1_000_000), flush=True)
    if fehlt:
        print("\nFEHLENDE Tonaufnahmen (%d): %s" % (len(fehlt), ", ".join(fehlt[:5])))
        sys.exit(1)
    print("\nFertig: %d Videos in %s" % (len(kurs["videos"]), aus))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    g = None
    if "--grenze" in sys.argv:
        g = float(sys.argv[sys.argv.index("--grenze") + 1])
    main(sys.argv[1], sys.argv[2], g)
