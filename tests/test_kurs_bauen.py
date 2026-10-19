"""kurs_bauen.py: Kursname setzen darf die uebrigen Texte der Kursdatei nicht auslassen."""
import io
import json
import os
import sys
import tarfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import kurs_bauen  # noqa: E402

KURS_XML = ('<?xml version="1.0" encoding="UTF-8"?>\n<course id="1" contextid="2">'
            '<shortname>sb_test_de</shortname><fullname>DE: Sicherheit</fullname>'
            '<summary>Bitte immer die Schutzbrille tragen.</summary></course>')


def _mbz(pfad):
    with tarfile.open(pfad, "w:gz") as t:
        for name, inhalt in (("files.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<files></files>'),
                             ("moodle_backup.xml", "<moodle_backup></moodle_backup>"),
                             ("course/course.xml", KURS_XML)):
            daten = inhalt.encode("utf-8")
            info = tarfile.TarInfo(name)
            info.size = len(daten)
            t.addfile(info, io.BytesIO(daten))


def _kursdatei(mbz):
    with tarfile.open(mbz, "r:gz") as t:
        return t.extractfile("course/course.xml").read().decode("utf-8")


def test_kursbeschreibung_wird_auch_mit_neuem_kursnamen_uebersetzt(tmp_path):
    quelle = tmp_path / "quelle.mbz"
    _mbz(quelle)
    (tmp_path / "kurs.json").write_text(json.dumps({"quelle": str(quelle), "videos": []}), encoding="utf-8")
    (tmp_path / "uebersetzung_fr.json").write_text(json.dumps(
        {"Bitte immer die Schutzbrille tragen.": "Porte toujours tes lunettes de protection."}), encoding="utf-8")
    ziel = tmp_path / "fertig.mbz"
    kurs_bauen.main(str(tmp_path), "fr", str(ziel), kursname="FR: Sécurité", kurzname="sb_test_fr")
    xml = _kursdatei(ziel)
    assert "<fullname>FR: Sécurité</fullname>" in xml
    assert "<shortname>sb_test_fr</shortname>" in xml
    assert "Porte toujours tes lunettes de protection." in xml
    assert "Schutzbrille" not in xml
