"""Schritt 6 - Neue Kurssicherung schreiben.

Liest die Originalsicherung im Stream, ersetzt Videos und Texte und schreibt eine
neue .mbz. Angefasst werden nur Textwerte und Videodateien - Struktur, IDs und
Verweise bleiben, wie Moodle sie erzeugt hat.

Aufruf:  python kurs_bauen.py <arbeitsordner> <sprachcode> <ziel.mbz>
                              [--kursname "..."] [--kurzname "..."] [--quizid 12345]
         --quizid: ersetzt in fest verdrahteten Links die Zielnummer (siehe hinweise.md)
"""
import hashlib
import io
import json
import os
import re
import sys
import tarfile
import time
import xml.etree.ElementTree as ET


def sha1(pfad):
    h = hashlib.sha1()
    with open(pfad, "rb") as fh:
        for stueck in iter(lambda: fh.read(1 << 20), b""):
            h.update(stueck)
    return h.hexdigest()


def main(ordner, code, ziel, kursname=None, kurzname=None, quizid=None):
    kurs = json.load(open(os.path.join(ordner, "kurs.json"), encoding="utf-8"))
    ueb = json.load(open(os.path.join(ordner, "uebersetzung_%s.json" % code), encoding="utf-8"))
    ueb = {k: v for k, v in ueb.items() if v}
    quelle = kurs["quelle"]
    videoordner = os.path.join(ordner, "videos_%s" % code)

    # altes Blob -> neue Videodatei
    neu = {}
    for v in kurs["videos"]:
        p = os.path.join(videoordner, v["datei"])
        if os.path.exists(p):
            neu[v["hash"]] = (sha1(p), os.path.getsize(p), p)
    print("Videos ersetzt : %d von %d" % (len(neu), len(kurs["videos"])))
    print("Texte ersetzt  : %d Eintraege" % len(ueb))

    def link_anpassen(text):
        if quizid and "view.php?id=" in text:
            return re.sub(r"view\.php\?id=\d+", "view.php?id=%s" % quizid, text)
        return text

    def h5p_uebersetzen(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if isinstance(v, str) and v in ueb:
                    node[k] = link_anpassen(ueb[v])
                else:
                    h5p_uebersetzen(v)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                if isinstance(v, str) and v in ueb:
                    node[i] = link_anpassen(ueb[v])
                else:
                    h5p_uebersetzen(v)

    def xml_raus(root):
        return b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="utf-8")

    def bearbeite(name, daten):
        if name == "files.xml":
            root = ET.fromstring(daten)
            n = 0
            for fe in root.findall("file"):
                ch = fe.findtext("contenthash")
                if ch in neu:
                    fe.find("contenthash").text = neu[ch][0]
                    fe.find("filesize").text = str(neu[ch][1])
                    n += 1
            print("files.xml      : %d Eintraege angepasst" % n)
            return xml_raus(root)

        if name == "moodle_backup.xml":
            s = daten.decode("utf-8")
            if kursname:
                s = re.sub(r"<original_course_fullname>.*?</original_course_fullname>",
                           "<original_course_fullname>%s</original_course_fullname>" % kursname, s)
            if kurzname:
                s = re.sub(r"<original_course_shortname>.*?</original_course_shortname>",
                           "<original_course_shortname>%s</original_course_shortname>" % kurzname, s)
            return s.encode("utf-8")

        if not name.endswith(".xml"):
            return None
        try:
            root = ET.fromstring(daten)
        except ET.ParseError:
            return None

        geaendert = False
        jc = root.find(".//json_content")
        if jc is not None and jc.text:
            inhalt = json.loads(jc.text)
            h5p_uebersetzen(inhalt)
            jc.text = json.dumps(inhalt, ensure_ascii=False, separators=(",", ":"))
            geaendert = True
        for el in root.iter():
            if el is jc or not el.text:
                continue
            if el.text in ueb:
                el.text = link_anpassen(ueb[el.text])
                geaendert = True
            elif el.text.strip() in ueb:
                el.text = el.text.replace(el.text.strip(), link_anpassen(ueb[el.text.strip()]))
                geaendert = True
            elif quizid and "view.php?id=" in el.text:
                el.text = link_anpassen(el.text)
                geaendert = True
        if name == "course/course.xml" and (kursname or kurzname):
            # erst nach der Uebersetzung: die Kursbeschreibung soll mit uebersetzt werden
            if kursname:
                root.find(".//fullname").text = kursname
            if kurzname:
                root.find(".//shortname").text = kurzname
            geaendert = True
        return xml_raus(root) if geaendert else None

    verzeichnis, geschrieben = [], set()
    zwischen = ziel + ".tmp"
    t0 = time.time()
    with tarfile.open(quelle, "r:gz") as ein, tarfile.open(zwischen, "w:gz", compresslevel=1) as aus:
        for m in ein:
            if m.name == ".ARCHIVE_INDEX":
                continue
            if m.isdir():
                aus.addfile(m)
                verzeichnis.append((m.name, "d", 0, "?"))
                continue
            blob = m.name.startswith("files/") and m.name.rsplit("/", 1)[-1]
            if blob in neu:
                nh, groesse, pfad = neu[blob]
                if nh in geschrieben:
                    continue
                geschrieben.add(nh)
                info = tarfile.TarInfo("files/%s/%s" % (nh[:2], nh))
                info.size, info.mtime, info.mode = groesse, m.mtime, m.mode
                with open(pfad, "rb") as fh:
                    aus.addfile(info, fh)
                verzeichnis.append((info.name, "f", groesse, int(info.mtime)))
                continue
            daten = ein.extractfile(m).read()
            ersatz = bearbeite(m.name, daten)
            inhalt = ersatz if ersatz is not None else daten
            info = tarfile.TarInfo(m.name)
            info.size, info.mtime, info.mode = len(inhalt), m.mtime, m.mode
            aus.addfile(info, io.BytesIO(inhalt))
            verzeichnis.append((m.name, "f", len(inhalt), int(info.mtime)))

    idx = "Moodle archive file index. Count: %d\n" % len(verzeichnis)
    idx += "".join("%s\t%s\t%s\t%s\n" % r for r in verzeichnis)
    idxb = idx.encode("utf-8")
    with tarfile.open(zwischen, "r:gz") as ein, tarfile.open(ziel, "w:gz", compresslevel=1) as aus:
        info = tarfile.TarInfo(".ARCHIVE_INDEX")
        info.size, info.mtime, info.mode = len(idxb), int(time.time()), 0o644
        aus.addfile(info, io.BytesIO(idxb))
        for m in ein:
            aus.addfile(m, ein.extractfile(m) if m.isfile() else None)
    os.remove(zwischen)
    print("\nFertig: %s (%d MB, %.0f s)" % (ziel, os.path.getsize(ziel) // 1_000_000, time.time() - t0))


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    hole = lambda f: sys.argv[sys.argv.index(f) + 1] if f in sys.argv else None
    main(sys.argv[1], sys.argv[2], sys.argv[3],
         hole("--kursname"), hole("--kurzname"), hole("--quizid"))
