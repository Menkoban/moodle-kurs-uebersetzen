"""Schritt 1 - Moodle-Sicherung einlesen.

Liest eine .mbz, ermittelt selbst Kursstruktur, H5P-Inhalte, Videos und alle
uebersetzbaren Texte. Legt im Arbeitsordner ab:

    kurs.json        Struktur (Aktivitaeten, Abschnitte, Kontexte, Videos)
    texte_de.json    alle uebersetzbaren Texte, adressierbar
    videos/          die Originalvideos (fuer den spaeteren Zusammenbau)
    audio_de/        deren Tonspuren (fuer die Transkription)
    hinweise.md      gefundene Fallstricke (fest verdrahtete Links usw.)

Aufruf:  python analyse.py <kurs.mbz> <arbeitsordner>
"""
import html as htmlmod
import json
import os
import re
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as ET

# Felder im H5P-Inhalt, die sichtbaren Text tragen
H5P_TEXTFELDER = {"labelText", "scenename", "scenedescription", "text", "alt",
                  "contentName", "audioTrackTitle", "title"}
# XML-Knoten mit sichtbarem Text, je Datei
XML_TEXTKNOTEN = {"name", "summary", "intro", "content", "questiontext", "answertext", "feedback"}
# Dateien ohne lernendensichtbaren Text
XML_UEBERSPRINGEN = {"gradebook.xml", "roles.xml", "users.xml", "groups.xml", "badges.xml",
                     "completion.xml", "outcomes.xml", "scales.xml", "grade_history.xml"}


def ist_konfiguration(s):
    """Erkennt Einstellungswerte, die nur wie Text aussehen (hiddensections, $@NULL@$, 0)."""
    k = s.strip()
    if not k or k == "$@NULL@$":
        return True
    if re.fullmatch(r"[-\d.,]+", k):
        return True
    if " " not in k and k == k.lower() and re.fullmatch(r"[a-z_]+", k):
        return True
    return False


def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s or "").replace("&nbsp;", " ").strip()


def sammle_h5p_texte(node, pfad, treffer):
    if isinstance(node, dict):
        for k, v in node.items():
            p = "%s/%s" % (pfad, k)
            if isinstance(v, str) and v.strip():
                if k in H5P_TEXTFELDER and not v.startswith("Unbenannt"):
                    treffer.append({"pfad": p, "feld": k, "text": v})
                elif k in ("path",):
                    pass
            elif k == "l10n" and isinstance(v, dict):
                for lk, lv in v.items():
                    if isinstance(lv, str) and lv.strip():
                        treffer.append({"pfad": "%s/%s" % (p, lk), "feld": "l10n:" + lk, "text": lv})
            else:
                sammle_h5p_texte(v, p, treffer)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            sammle_h5p_texte(v, "%s/%d" % (pfad, i), treffer)


def medienpfade(node, out):
    if isinstance(node, dict):
        if isinstance(node.get("path"), str):
            out.append(node["path"])
        for v in node.values():
            medienpfade(v, out)
    elif isinstance(node, list):
        for v in node:
            medienpfade(v, out)


def main(mbz, ordner):
    os.makedirs(ordner, exist_ok=True)
    os.makedirs(os.path.join(ordner, "videos"), exist_ok=True)
    os.makedirs(os.path.join(ordner, "audio_de"), exist_ok=True)

    xmls, blob_groesse = {}, {}
    with tarfile.open(mbz, "r:gz") as t:
        for m in t:
            if not m.isfile():
                continue
            if m.name.startswith("files/"):
                blob_groesse[m.name.rsplit("/", 1)[-1]] = m.size
            elif m.name.endswith(".xml"):
                xmls[m.name] = t.extractfile(m).read()

    if "files.xml" not in xmls:
        sys.exit("Keine files.xml gefunden - ist das eine Moodle-Sicherung?")

    # --- Dateien der Sicherung
    dateien = []
    for fe in ET.fromstring(xmls["files.xml"]).findall("file"):
        g = lambda tag: fe.findtext(tag) or ""
        dateien.append({"hash": g("contenthash"), "name": g("filename"), "pfad": g("filepath"),
                        "kontext": g("contextid"), "komponente": g("component"),
                        "bereich": g("filearea"), "groesse": int(g("filesize") or 0),
                        "typ": g("mimetype")})

    # --- Aktivitaeten
    aktivitaeten = []
    for name in sorted(xmls):
        if not re.match(r"activities/[^/]+/module\.xml$", name):
            continue
        verz = name.rsplit("/", 1)[0]
        modul = ET.fromstring(xmls[name])
        art = modul.findtext("modulename")
        datei = "%s/%s.xml" % (verz, art)
        titel, kontext = "", ""
        if datei in xmls:
            root = ET.fromstring(xmls[datei])
            titel = (root.findtext(".//name") or "").strip()
            kontext = root.get("contextid", "")
        aktivitaeten.append({"verzeichnis": verz, "art": art, "moduleid": modul.get("id"),
                             "sectionid": modul.findtext("sectionid"), "titel": titel,
                             "kontext": kontext, "datei": datei})

    # --- Abschnitte
    abschnitte = []
    for name in sorted(xmls):
        if not re.match(r"sections/[^/]+/section\.xml$", name):
            continue
        s = ET.fromstring(xmls[name])
        abschnitte.append({"datei": name, "id": s.get("id"), "nummer": s.findtext("number"),
                           "titel": s.findtext("name") or ""})

    # --- Kurs
    kursname = ""
    if "course/course.xml" in xmls:
        kursname = ET.fromstring(xmls["course/course.xml"]).findtext(".//fullname") or ""

    # --- H5P-Aktivitaeten samt Texten und Medien
    texte, h5p_infos, hinweise = [], [], []
    for a in aktivitaeten:
        if a["art"] not in ("hvp", "h5pactivity"):
            continue
        root = ET.fromstring(xmls[a["datei"]])
        jc = root.find(".//json_content")
        if jc is None or not jc.text:
            # mod_h5pactivity legt den Inhalt als gepackte .h5p-Datei ab, nicht als Text.
            # Dieser Skill kann sie nicht bearbeiten - siehe references/fallstricke.md.
            hinweise.append(
                "NICHT UEBERSETZBAR: %s (%s) - Inhalt liegt als .h5p-Datei vor, nicht im XML. "
                "Dieser Skill bearbeitet nur mod_hvp." % (a["verzeichnis"], a["art"]))
            print("  ACHTUNG: %s (%s) kann nicht uebersetzt werden - siehe hinweise.md"
                  % (a["verzeichnis"], a["art"]))
            continue
        inhalt = json.loads(jc.text)
        treffer = []
        sammle_h5p_texte(inhalt, "", treffer)
        for tr in treffer:
            tr.update(quelle=a["datei"], art="h5p")
        texte += treffer
        pfade = []
        medienpfade(inhalt, pfade)
        h5p_infos.append({"aktivitaet": a["verzeichnis"], "kontext": a["kontext"],
                          "medien": sorted(set(pfade)), "bibliothek": root.findtext(".//machine_name")})
        for tr in treffer:                                   # fest verdrahtete Links finden
            for m in re.finditer(r'href="([^"]*view\.php\?id=\d+[^"]*)"', tr["text"]):
                hinweise.append("Fester Link in H5P (%s): %s" % (tr["feld"], m.group(1)))

    # --- Texte aus XML-Dateien (Abschnitte, Aktivitaeten, Fragen)
    for name, data in sorted(xmls.items()):
        if name in ("files.xml", "moodle_backup.xml") or name.endswith("inforef.xml"):
            continue
        if name.rsplit("/", 1)[-1] in XML_UEBERSPRINGEN:
            continue
        try:
            root = ET.fromstring(data)
        except ET.ParseError:
            continue
        for el in root.iter():
            if el.tag in XML_TEXTKNOTEN and el.text and el.text.strip():
                if len(el.text) > 8000 or ist_konfiguration(el.text):
                    continue
                texte.append({"pfad": "%s:%s" % (name, el.tag), "feld": el.tag,
                              "text": el.text, "quelle": name, "art": "xml"})
        for m in re.finditer(r'view\.php\?id=(\d+)', data.decode("utf-8", "ignore")):
            if name.startswith("sections/") or name.startswith("activities/"):
                hinweise.append("Fester Link in %s: view.php?id=%s" % (name, m.group(1)))

    # --- Videos herausziehen und Ton abtrennen
    videos = []
    nach_name = {}
    for d in dateien:
        if d["name"].lower().endswith((".mp4", ".m4v", ".webm")):
            nach_name.setdefault(d["hash"], d)
    lauf = 0
    with tarfile.open(mbz, "r:gz") as t:
        for m in t:
            h = m.name.rsplit("/", 1)[-1]
            if not (m.isfile() and m.name.startswith("files/") and h in nach_name):
                continue
            d = nach_name[h]
            lauf += 1
            ziel = os.path.join(ordner, "videos", "%02d_%s" % (lauf, sicher(d["name"])))
            with open(ziel, "wb") as fh:
                fh.write(t.extractfile(m).read())
            ton = os.path.join(ordner, "audio_de", os.path.splitext(os.path.basename(ziel))[0] + ".mp3")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", ziel, "-vn",
                            "-ac", "1", "-ar", "16000", "-b:a", "48k", ton],
                           check=False)
            videos.append({"nr": lauf, "hash": h, "dateiname": d["name"], "pfad_in_h5p": d["pfad"],
                           "kontext": d["kontext"], "datei": os.path.basename(ziel),
                           "ton": os.path.basename(ton), "dauer": dauer(ziel),
                           "hat_ton": os.path.exists(ton) and os.path.getsize(ton) > 2000})

    kurs = {"quelle": os.path.abspath(mbz), "kursname": kursname, "abschnitte": abschnitte,
            "aktivitaeten": aktivitaeten, "h5p": h5p_infos, "videos": videos,
            "dateien_gesamt": len(dateien)}
    schreib(os.path.join(ordner, "kurs.json"), kurs)
    schreib(os.path.join(ordner, "texte_de.json"), texte)
    if hinweise:
        with open(os.path.join(ordner, "hinweise.md"), "w", encoding="utf-8") as fh:
            fh.write("# Gefundene Fallstricke\n\n")
            for h in sorted(set(hinweise)):
                fh.write("- %s\n" % h)
            fh.write("\nFeste Links zeigen nach dem Wiederherstellen weiter auf den Ursprungskurs.\n"
                     "Nach dem Import die Zielnummer pruefen und beim Bauen mitgeben.\n")

    print("Kurs      : %s" % (kursname or "(ohne Namen)"))
    print("Abschnitte: %d | Aktivitaeten: %d (%s)" %
          (len(abschnitte), len(aktivitaeten), ", ".join(sorted({a["art"] for a in aktivitaeten}))))
    print("H5P       : %d Inhalt(e), %s" % (len(h5p_infos), ", ".join(h["bibliothek"] or "?" for h in h5p_infos)))
    print("Videos    : %d (%d mit Ton), gesamt %.1f Minuten" %
          (len(videos), sum(1 for v in videos if v["hat_ton"]), sum(v["dauer"] for v in videos) / 60))
    print("Texte     : %d uebersetzbare Stellen" % len(texte))
    if hinweise:
        print("Hinweise  : %d (siehe hinweise.md)" % len(set(hinweise)))


def sicher(s):
    return re.sub(r"[^\w.-]", "_", s)


def dauer(p):
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "csv=p=0", p], capture_output=True, text=True)
        return round(float(r.stdout.strip()), 1)
    except Exception:
        return 0.0


def schreib(p, obj):
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
