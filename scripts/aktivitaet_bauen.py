"""Zusatz - eine einzelne Aktivitaet als Sicherung herausloesen.

Fuer den Fall, dass der Zielkurs schon existiert und benutzt wird: Statt den ganzen Kurs
neu zu importieren (wobei sich alle Modulnummern aendern), wird nur die uebersetzte
Aktivitaet eingespielt und die alte geloescht.

Aufruf:  python aktivitaet_bauen.py <fertig.mbz> <aktivitaetsverzeichnis> <ziel.mbz>
                                    [--muster <aktivitaetssicherung.mbz>] [--quizid 12345]

   aktivitaetsverzeichnis: z. B. activities/hvp_115106 (steht in kurs.json)
   --muster: eine echte Aktivitaetssicherung aus DEMSELBEN Moodle. Daraus werden die
             Wurzeldateien uebernommen. Ohne Muster werden sie erzeugt - das ist
             weniger sicher, weil Moodle-Versionen sich hier unterscheiden.

Einspielen: Kurs wiederherstellen -> in diesen Kurs, vorhandene Inhalte BEHALTEN.
Danach die alte Aktivitaet loeschen und die neue an ihre Stelle schieben.
"""
import io
import json
import os
import re
import sys
import tarfile
import time
import xml.etree.ElementTree as ET

LEERE_WURZEL = {
    "badges.xml": b'<?xml version="1.0" encoding="UTF-8"?>\n<badges>\n</badges>',
    "completion.xml": b'<?xml version="1.0" encoding="UTF-8"?>\n<course_completion>\n</course_completion>',
    "groups.xml": b'<?xml version="1.0" encoding="UTF-8"?>\n<groups>\n  <groupings>\n  </groupings>\n</groups>',
    "outcomes.xml": b'<?xml version="1.0" encoding="UTF-8"?>\n<outcomes_definition>\n</outcomes_definition>',
    "questions.xml": b'<?xml version="1.0" encoding="UTF-8"?>\n<question_categories>\n</question_categories>',
    "roles.xml": b'<?xml version="1.0" encoding="UTF-8"?>\n<roles_definition>\n</roles_definition>',
    "scales.xml": b'<?xml version="1.0" encoding="UTF-8"?>\n<scales_definition>\n</scales_definition>',
    "users.xml": b'<?xml version="1.0" encoding="UTF-8"?>\n<users>\n</users>',
    "moodle_backup.log": b"",
}


def backup_xml(quelle_meta, verzeichnis, moduleid, sectionid, modulename, titel, dateiname):
    einst = [("filename", dateiname), ("users", "0"), ("anonymize", "0"), ("role_assignments", "0"),
             ("activities", "1"), ("blocks", "1"), ("files", "1"), ("filters", "1"),
             ("comments", "0"), ("badges", "0"), ("calendarevents", "0"), ("userscompletion", "0"),
             ("logs", "0"), ("grade_histories", "0"), ("groups", "0"), ("competencies", "1"),
             ("customfield", "1"), ("contentbankcontent", "1"), ("xapistate", "1"), ("legacyfiles", "1")]
    z = ['<?xml version="1.0" encoding="UTF-8"?>', "<moodle_backup>", "  <information>",
         "    <name>%s</name>" % dateiname]
    for feld in ("moodle_version", "moodle_release", "backup_version", "backup_release",
                 "original_wwwroot", "original_site_identifier_hash", "original_course_id",
                 "original_course_format", "original_course_fullname", "original_course_shortname",
                 "original_course_startdate", "original_course_enddate", "original_course_contextid",
                 "original_system_contextid"):
        z.append("    <%s>%s</%s>" % (feld, quelle_meta.get(feld, ""), feld))
    z += ["    <backup_date>%d</backup_date>" % int(time.time()),
          "    <mnet_remoteusers>0</mnet_remoteusers>",
          "    <include_files>1</include_files>",
          "    <include_file_references_to_external_content>0</include_file_references_to_external_content>",
          "    <details>", '      <detail backup_id="%032x">' % int(time.time()),
          "        <type>activity</type>", "        <format>moodle2</format>",
          "        <interactive>1</interactive>", "        <mode>10</mode>",
          "        <execution>1</execution>", "        <executiontime>0</executiontime>",
          "      </detail>", "    </details>",
          "    <contents>", "      <activities>", "        <activity>",
          "          <moduleid>%s</moduleid>" % moduleid,
          "          <sectionid>%s</sectionid>" % sectionid,
          "          <modulename>%s</modulename>" % modulename,
          "          <title>%s</title>" % titel,
          "          <directory>%s</directory>" % verzeichnis,
          "          <insubsection></insubsection>",
          "        </activity>", "      </activities>", "    </contents>", "    <settings>"]
    for n, v in einst:
        z += ["      <setting>", "        <level>root</level>", "        <name>%s</name>" % n,
              "        <value>%s</value>" % v, "      </setting>"]
    for n, v in [("included", "1"), ("userinfo", "0")]:
        z += ["      <setting>", "        <level>activity</level>",
              "        <activity>%s_%s</activity>" % (modulename, moduleid),
              "        <name>%s_%s_%s</name>" % (modulename, moduleid, n),
              "        <value>%s</value>" % v, "      </setting>"]
    z += ["    </settings>", "  </information>", "</moodle_backup>"]
    return "\n".join(z).encode("utf-8")


def main(quelle, verzeichnis, ziel, muster=None, quizid=None):
    teile, wurzel_quelle = {}, {}
    with tarfile.open(quelle, "r:gz") as t:
        for m in t:
            if not m.isfile():
                continue
            if m.name.startswith(verzeichnis + "/") or m.name.endswith("hvp_libraries.xml"):
                teile[m.name] = t.extractfile(m).read()
            elif m.name in ("files.xml", "moodle_backup.xml"):
                wurzel_quelle[m.name] = t.extractfile(m).read()
    if not teile:
        sys.exit("Verzeichnis nicht gefunden: " + verzeichnis)

    art = verzeichnis.rsplit("/", 1)[-1].split("_")[0]
    inhalt_datei = "%s/%s.xml" % (verzeichnis, art)
    root = ET.fromstring(teile[inhalt_datei])
    kontext = root.get("contextid")
    titel = (root.findtext(".//name") or "").strip()
    modul = ET.fromstring(teile["%s/module.xml" % verzeichnis])

    if quizid:                                          # feste Links umbiegen
        geaendert = False
        for el in root.iter():
            if el.text and "view.php?id=" in el.text:
                el.text = re.sub(r"view\.php\?id=\d+", "view.php?id=%s" % quizid, el.text)
                geaendert = True
        if geaendert:
            teile[inhalt_datei] = b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="utf-8")
            print("Feste Links auf id=%s gesetzt" % quizid)

    # Dateien der Aktivitaet plus Systemkontext (H5P-Bibliotheken)
    alle = ET.fromstring(wurzel_quelle["files.xml"])
    behalten, hashes = ET.Element("files"), set()
    for fe in alle.findall("file"):
        if fe.findtext("contextid") in (kontext, "1"):
            behalten.append(fe)
            hashes.add(fe.findtext("contenthash"))
    print("Aktivitaet: %s (%s), Kontext %s" % (titel, art, kontext))
    print("Dateien   : %d Eintraege, %d Inhalte" % (len(behalten), len(hashes)))

    meta = {}
    mroot = ET.fromstring(wurzel_quelle["moodle_backup.xml"])
    for el in mroot.find("information"):
        if el.text and not len(el):
            meta[el.tag] = el.text

    mitglieder = dict(LEERE_WURZEL)
    if muster:                                          # Wurzeldateien aus echtem Muster
        with tarfile.open(muster, "r:gz") as t:
            for m in t:
                if m.isfile() and "/" not in m.name and m.name not in (
                        "moodle_backup.xml", "files.xml", ".ARCHIVE_INDEX"):
                    mitglieder[m.name] = t.extractfile(m).read()
        print("Wurzeldateien aus Muster uebernommen")
    mitglieder["moodle_backup.xml"] = backup_xml(
        meta, verzeichnis, modul.get("id"), modul.findtext("sectionid"), art, titel,
        os.path.basename(ziel))
    mitglieder["files.xml"] = b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(behalten, encoding="utf-8")
    mitglieder.update(teile)

    index, jetzt = [], int(time.time())
    zwischen = ziel + ".tmp"
    with tarfile.open(quelle, "r:gz") as ein, tarfile.open(zwischen, "w:gz", compresslevel=1) as aus:
        for name in sorted(mitglieder):
            daten = mitglieder[name]
            info = tarfile.TarInfo(name)
            info.size, info.mtime, info.mode = len(daten), jetzt, 0o644
            aus.addfile(info, io.BytesIO(daten))
            index.append((name, "f", len(daten), jetzt))
        for m in ein:
            if m.isfile() and m.name.startswith("files/") and m.name.rsplit("/", 1)[-1] in hashes:
                info = tarfile.TarInfo(m.name)
                info.size, info.mtime, info.mode = m.size, m.mtime, m.mode
                aus.addfile(info, ein.extractfile(m))
                index.append((m.name, "f", m.size, int(m.mtime)))

    idx = ("Moodle archive file index. Count: %d\n" % len(index)) + \
          "".join("%s\t%s\t%s\t%s\n" % r for r in index)
    idxb = idx.encode("utf-8")
    with tarfile.open(zwischen, "r:gz") as ein, tarfile.open(ziel, "w:gz", compresslevel=1) as aus:
        info = tarfile.TarInfo(".ARCHIVE_INDEX")
        info.size, info.mtime, info.mode = len(idxb), jetzt, 0o644
        aus.addfile(info, io.BytesIO(idxb))
        for m in ein:
            aus.addfile(m, ein.extractfile(m) if m.isfile() else None)
    os.remove(zwischen)
    print("\nFertig: %s (%d MB)" % (ziel, os.path.getsize(ziel) // 1_000_000))


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    hole = lambda f: sys.argv[sys.argv.index(f) + 1] if f in sys.argv else None
    main(sys.argv[1], sys.argv[2], sys.argv[3], hole("--muster"), hole("--quizid"))
