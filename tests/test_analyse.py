"""analyse.py: alles, was Lernende im Test lesen, muss in texte_de.json landen."""
import io
import json
import os
import sys
import tarfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import analyse  # noqa: E402

FRAGEN = '''<?xml version="1.0" encoding="UTF-8"?>
<question_categories><question_category id="1"><questions><question id="7">
<name>Schuhe</name><questiontext>Was ziehst du an?</questiontext>
<generalfeedback>Sicherheitsschuhe sind Pflicht.</generalfeedback>
<plugin_qtype_multichoice_question><multichoice>
<correctfeedback>Richtig!</correctfeedback>
<partiallycorrectfeedback>Teilweise richtig.</partiallycorrectfeedback>
<incorrectfeedback>Leider falsch.</incorrectfeedback>
</multichoice></plugin_qtype_multichoice_question>
<question_hints><question_hint id="1"><hint>Denk an deine Füße.</hint></question_hint></question_hints>
</question></questions></question_category></question_categories>'''


def test_rueckmeldungen_und_hinweise_der_testfragen_werden_erfasst(tmp_path):
    mbz = tmp_path / "kurs.mbz"
    with tarfile.open(mbz, "w:gz") as t:
        for name, inhalt in (("files.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<files></files>'),
                             ("questions.xml", FRAGEN)):
            daten = inhalt.encode("utf-8")
            info = tarfile.TarInfo(name)
            info.size = len(daten)
            t.addfile(info, io.BytesIO(daten))
    analyse.main(str(mbz), str(tmp_path / "arbeit"))
    texte = {t["text"] for t in json.load(open(tmp_path / "arbeit" / "texte_de.json", encoding="utf-8"))}
    for erwartet in ("Was ziehst du an?", "Sicherheitsschuhe sind Pflicht.", "Richtig!", "Teilweise richtig.",
                     "Leider falsch.", "Denk an deine Füße."):
        assert erwartet in texte, erwartet
