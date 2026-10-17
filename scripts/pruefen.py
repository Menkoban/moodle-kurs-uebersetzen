"""Schritt 7 - Fertige Sicherung pruefen, bevor sie jemand einspielt.

Prueft Archiv, XML, Dateiverweise, Pruefsummen, H5P-Medien und sucht nach Texten,
die in der Ausgangssprache stehengeblieben sind.

Aufruf:  python pruefen.py <fertig.mbz> [arbeitsordner]
         Mit Arbeitsordner wird zusaetzlich gegen die Uebersetzungsliste geprueft.

Rueckgabe: 0 = sauber, 1 = Probleme gefunden
"""
import hashlib
import json
import os
import re
import sys
import tarfile
import xml.etree.ElementTree as ET


def main(pfad, ordner=None):
    probleme, hinweise = [], []
    mitglieder, blobs, xmls = {}, {}, {}
    with tarfile.open(pfad, "r:gz") as t:
        for m in t:
            mitglieder[m.name] = m
            if m.isfile():
                if m.name.startswith("files/"):
                    blobs[m.name.rsplit("/", 1)[-1]] = m.size
                elif m.name.endswith(".xml") or m.name == ".ARCHIVE_INDEX":
                    xmls[m.name] = t.extractfile(m).read()
    print("Mitglieder: %d | Dateien: %d | XML: %d" % (len(mitglieder), len(blobs), len(xmls)))

    for n, d in xmls.items():
        if n.endswith(".xml"):
            try:
                ET.fromstring(d)
            except Exception as e:
                probleme.append("XML nicht lesbar: %s (%s)" % (n, e))

    root = ET.fromstring(xmls["files.xml"])
    verweise = set()
    for fe in root.findall("file"):
        ch, groesse = fe.findtext("contenthash"), int(fe.findtext("filesize") or 0)
        if groesse == 0:
            continue
        verweise.add(ch)
        if ch not in blobs:
            probleme.append("Datei fehlt im Archiv: %s" % fe.findtext("filename"))
        elif blobs[ch] != groesse:
            probleme.append("Groesse stimmt nicht: %s" % fe.findtext("filename"))
    print("Dateiverweise: %d" % len(verweise))
    if set(blobs) - verweise:
        hinweise.append("%d Dateien ohne Verweis (unkritisch)" % len(set(blobs) - verweise))

    with tarfile.open(pfad, "r:gz") as t:                      # Pruefsummen der grossen Dateien
        geprueft = 0
        for m in t:
            if not m.name.startswith("files/") or m.size < 1_000_000:
                continue
            h = hashlib.sha1()
            f = t.extractfile(m)
            for stueck in iter(lambda: f.read(1 << 20), b""):
                h.update(stueck)
            if h.hexdigest() != m.name.rsplit("/", 1)[-1]:
                probleme.append("Pruefsumme passt nicht: %s" % m.name)
            geprueft += 1
            if geprueft >= 30:
                break
    print("Pruefsummen: %d grosse Dateien" % geprueft)

    for n, d in xmls.items():                                   # H5P-Medien vorhanden?
        if not n.endswith(".xml"):
            continue
        jc = None
        try:
            jc = ET.fromstring(d).find(".//json_content")
        except Exception:
            pass
        if jc is None or not jc.text:
            continue
        inhalt = json.loads(jc.text)
        pfade = []

        def lauf(x):
            if isinstance(x, dict):
                if isinstance(x.get("path"), str):
                    pfade.append(x["path"].split("#")[0])
                for v in x.values():
                    lauf(v)
            elif isinstance(x, list):
                for v in x:
                    lauf(v)
        lauf(inhalt)
        vorhanden = {(fe.findtext("filepath") + fe.findtext("filename")).lstrip("/")
                     for fe in root.findall("file") if fe.findtext("filearea") == "content"}
        fehlend = [p for p in set(pfade) if p not in vorhanden]
        print("H5P %s: %d Medienverweise" % (n.split("/")[-2] if "/" in n else n, len(set(pfade))))
        if fehlend:
            probleme.append("H5P verweist auf fehlende Datei: %s" % fehlend[:3])

    idx = xmls[".ARCHIVE_INDEX"].decode("utf-8").splitlines()
    anzahl = int(re.search(r"Count: (\d+)", idx[0]).group(1))
    if not (anzahl == len(idx) - 1 == len(mitglieder) - 1):
        probleme.append("Archivindex passt nicht (%d/%d/%d)" % (anzahl, len(idx) - 1, len(mitglieder) - 1))
    print("Archivindex: %d Eintraege" % anzahl)

    if ordner:                                                  # unuebersetzte Texte finden
        datei = os.path.join(ordner, "texte_de.json")
        if os.path.exists(datei):
            original = {t["text"] for t in json.load(open(datei, encoding="utf-8"))}
            gefunden = set()
            for n, d in xmls.items():
                if not n.endswith(".xml") or n in ("files.xml", "moodle_backup.xml"):
                    continue
                if n.endswith("hvp_libraries.xml"):
                    # Sprachkatalog der H5P-Bibliothek, keine Kursinhalte. Die im Inhalt
                    # gesetzten l10n-Werte gehen vor - siehe references/fallstricke.md
                    continue
                s = d.decode("utf-8", "ignore")
                for o in original:
                    kern = re.sub(r"<[^>]+>", "", o).strip()
                    if len(kern) > 12 and kern in s:
                        gefunden.add((n.split("/")[-1], kern[:60]))
            if gefunden:
                print("\nNoch in Ausgangssprache (%d Stellen):" % len(gefunden))
                for datei_name, txt in sorted(gefunden)[:15]:
                    print("   %-16s %s" % (datei_name, txt))

    print()
    for h in hinweise:
        print("Hinweis:", h)
    if probleme:
        print("\nPROBLEME:")
        for p in probleme:
            print("  -", p)
        return 1
    print("Keine strukturellen Probleme gefunden.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
