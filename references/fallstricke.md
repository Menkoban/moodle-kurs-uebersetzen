# Fallstricke beim Übersetzen und Wiederherstellen

Gesammelt aus einem echten Durchlauf: Sicherheitskurs Hauswirtschaft der BBS Bersenbrück,
Moodle 5.1.6, H5P Virtual Tour mit 24 Avatar-Videos, übersetzt nach Französisch,
Ukrainisch und Spanisch.

## Fest verdrahtete Links in H5P

**Das Problem:** Moodle schreibt beim Wiederherstellen Verweise in seinen *eigenen*
Textfeldern automatisch um — dort stehen Platzhalter wie `$@COURSESECTIONBYID*37365@$`.
**In H5P-Inhalten passiert das nicht.** H5P ist für Moodle ein Datenblock. Eine Adresse
wie `https://schule.de/mod/quiz/view.php?id=45012` bleibt genau so stehen und schickt die
Lernenden des neuen Kurses in den alten.

**Erkennen:** `analyse.py` schreibt jeden gefundenen festen Link nach `hinweise.md`.

**Beheben:** Kurs einmal importieren, im neuen Kurs die Zielaktivität anklicken, Zahl
hinter `id=` ablesen, dann `kurs_bauen.py --quizid <Zahl>` — und die Datei erneut
einspielen. Die Zahl steht auch in der Adresse der Bearbeiten-Seite (`modedit.php?update=…`).

**Henne-Ei-Problem:** Beim Import als *neuer* Kurs bekommt die Zielaktivität wieder eine
neue Nummer. Der Ausweg ist die Aktivitätssicherung (siehe unten).

## Nur eine Aktivität austauschen statt den ganzen Kurs neu

Wenn der Zielkurs schon existiert und benutzt wird, darf man ihn nicht neu importieren —
alle Modulnummern ändern sich, Links zeigen ins Leere, Bewertungen sind weg.

Stattdessen eine **Aktivitätssicherung** bauen: dieselben Dateien, aber
`moodle_backup.xml` mit `<type>activity</type>` und nur dem Verzeichnis der einen
Aktivität. Einspielen über *Kurs wiederherstellen → in diesen Kurs, vorhandene Inhalte
beibehalten*; danach die alte Aktivität löschen.

Enthalten sein müssen:
- `activities/<modul>/` vollständig
- `activities/hvp_libraries.xml` (bei H5P) — sonst fehlen die Programmbibliotheken
- `files.xml` gefiltert auf den Kontext der Aktivität **plus Kontext `1`** (dort liegen
  die H5P-Bibliotheken, über 10.000 Dateien)
- die Wurzeldateien (`users.xml`, `roles.xml`, …) — am einfachsten aus einer echten
  Aktivitätssicherung desselben Moodle übernehmen

## Der Archivindex

Moodle 4.3+ legt als erstes Element `.ARCHIVE_INDEX` ins Archiv: eine Textdatei mit
`Pfad<TAB>Typ<TAB>Größe<TAB>Zeitstempel` je Zeile, Kopfzeile `Moodle archive file index.
Count: N`. Wer das Archiv neu packt, muss ihn **neu erzeugen** — die Zeilenzahl und `N`
müssen zur tatsächlichen Mitgliederzahl passen (ohne den Index selbst).

Typischer Fehler: Zwei Dateien werden durch dieselbe neue Datei ersetzt, beide bekommen
denselben Prüfsummen-Pfad — das Archiv enthält den Eintrag dann doppelt. Beim Schreiben
mitzählen, welche Prüfsummen schon drin sind.

## Dateien werden über ihre Prüfsumme adressiert

In `files.xml` steht zu jeder Datei ein `contenthash` — der SHA-1 des Inhalts — und der
Ablageort im Archiv ist `files/<erste zwei Zeichen>/<hash>`. Tauscht man eine Videodatei
aus, müssen **drei** Dinge zusammenpassen: neuer Hash im Archivpfad, `contenthash` in
`files.xml`, `filesize` in `files.xml`. Der Dateiname (`filename`) bleibt unverändert —
darüber findet H5P sein Video, nicht über den Hash.

Praktische Folge: Die Pfade im H5P-Inhalt (`videos/sources-abc123.mp4`) müssen **nicht**
angefasst werden. Nur die Datei dahinter wird eine andere.

## H5P-Bedienknöpfe

Die Beschriftungen von „Tonspur abspielen", „Kamera zurücksetzen", „Dialog schließen"
stehen **zweimal**: im `l10n`-Block des Inhalts und im Sprachkatalog der Bibliothek
(`hvp_libraries.xml`). Der Inhalt gewinnt — es genügt, die `l10n`-Werte zu übersetzen.
`analyse.py` erfasst sie, `pruefen.py` ignoriert die Bibliotheksdatei bewusst.

In der englischen Fassung des Ausgangskurses waren diese Knöpfe deutsch geblieben — ein
verbreiteter blinder Fleck, weil sie beim Durchklicken kaum auffallen.

## Was der Restore-Test beweist und was nicht

`moodle-testinstanz` spielt die Sicherung mit Moodles eigenem Code ein. Aber: Ist
`mod_hvp` dort nicht installiert, überspringt Moodle die H5P-Aktivität **ohne Fehler**.
Ein grünes Ergebnis heißt dann nur, dass Kurs, Abschnitte, Test und Textseiten stimmen.

Ersatzprüfung für den H5P-Teil: XML-Struktur und JSON-Schlüsselbaum gegen das Original
vergleichen. Sind beide identisch und wurden nur Textwerte und Dateien getauscht, ist das
Risiko klein — beweisen lässt es sich nur in einem Moodle mit dem Plugin.

## Sprechzeit verschiebt sich

Gemessen an der deutschen Fassung (18,8 Minuten in 24 Videos):

| Sprache | Sprechzeit | Abweichung |
|---|---|---|
| Französisch | 18,2 min | −3 % |
| Spanisch | 19,6 min | +4 % |
| Ukrainisch | 21,4 min | +14 % |

Bei Ukrainisch überschritten 23 von 24 Aufnahmen ihr Video, die längste um 13 Sekunden.
Deshalb: Bild dehnen, Ton in Ruhe lassen.

## Kleinigkeiten, die leicht durchrutschen

- **Kursbeschreibung** (`summary` in `course.xml`) — steht in der Kursübersicht, wird
  beim Durchklicken des Kurses nie sichtbar und deshalb gern vergessen.
- **Texte mit ungewöhnlichem HTML** — ein Warnhinweis, der in `<span style="color:…">`
  steckt, fällt aus jedem simplen Textvergleich heraus. `pruefen.py` vergleicht deshalb
  gegen die vollständige Liste aus `texte_de.json`, nicht gegen Stichwörter.
- **Doppelte Videodateien** — manche Kurse enthalten eine ungenutzte Zweitkopie eines
  Videos. Wird sie nicht mitgetauscht, bleibt eine deutsche Tonspur im Kurs liegen.
- **Nicht verwendete Fragen** in der Fragensammlung müssen nicht übersetzt werden; sie
  tauchen im Test nicht auf. Im Prüfbericht erscheinen sie trotzdem — kein Fehler.

## Die zwei H5P-Varianten in Moodle

| | `mod_hvp` | `mod_h5pactivity` |
|---|---|---|
| Herkunft | separates Plugin (h5p.org) | in Moodle eingebaut |
| Ordner in der Sicherung | `activities/hvp_<nr>` | `activities/h5pactivity_<nr>` |
| Wo der Inhalt steckt | `<json_content>` als Text im XML | gepackte `.h5p`-Datei in `files/` |
| Von diesem Skill bearbeitbar | ja | **nein** |

Bei `mod_h5pactivity` müsste die `.h5p`-Datei entpackt (es ist ein ZIP), die enthaltene
`content/content.json` übersetzt, neu gepackt und mit neuer Prüfsumme eingesetzt werden.
Machbar, aber ungetestet — `analyse.py` bricht deshalb nicht ab, meldet die Aktivität
aber ausdrücklich als nicht übersetzbar.
