# Aufbau einer Moodle-Sicherung (.mbz)

Nötig, wenn die Skripte nicht ausreichen und von Hand eingegriffen werden muss.

## Das Archiv

Eine `.mbz` ist ein **gzip-gepacktes tar-Archiv**. Umbenennen in `.tar.gz` genügt zum
Öffnen. Aufbau:

```
.ARCHIVE_INDEX              Verzeichnis aller Mitglieder (Moodle 4.3+)
moodle_backup.xml           Was ist drin, aus welchem Moodle, welche Einstellungen
files.xml                   Jede Datei mit Prüfsumme, Größe, Kontext, Komponente
course/course.xml           Kursname, Kurzname, Beschreibung, Format
sections/section_<id>/      je Abschnitt: Titel, Einleitungstext, Reihenfolge
activities/<art>_<id>/      je Aktivität: Inhalt, Modulangaben, Rollen, Dateiverweise
questions.xml               Fragensammlung (bei Kursen mit Test)
files/<xx>/<prüfsumme>      die eigentlichen Dateien, benannt nach ihrem SHA-1
```

## Wichtige Felder

**`moodle_backup.xml`** — `<type>` ist `course` oder `activity`. Bei `activity` steht
unter `<contents><activities>` genau ein Eintrag mit `moduleid`, `sectionid`, `modulename`
und `directory`. `<backup_version>` und `<moodle_release>` beschreiben die Quelle; ein
neueres Moodle kann ältere Sicherungen einspielen, umgekehrt nicht zuverlässig.

**`files.xml`** — jeder `<file>`-Eintrag trägt `contextid` (welcher Aktivität die Datei
gehört), `component` (`mod_hvp`, `mod_label`, `course`), `filearea` (`content`,
`intro`, `libraries`), `filepath`, `filename`, `filesize`, `contenthash`. Einträge mit
`filesize` 0 sind Verzeichnismarken.

**H5P-Aktivität (`mod_hvp`)** — `<json_content>` enthält den gesamten Inhalt als
JSON-Zeichenkette, XML-maskiert. Beim Bearbeiten: parsen, ändern, wieder als Text
einsetzen. Struktur bei Virtual Tour:

```
threeImage.scenes[]              je Raum
  .scenename                     Name der Szene
  .scenesrc.path                 das 360°-Bild
  .interactions[]                die anklickbaren Punkte
    .labelText                   Beschriftung des Punktes
    .action.library              H5P.Video / H5P.AdvancedText / H5P.Image / H5P.GoToScene
    .action.params.sources[].path   die Videodatei
    .action.params.text          bei Textfeldern der Inhalt
l10n                             Bedienknöpfe der Tour
```

## Platzhalter, die Moodle beim Import ersetzt

| Platzhalter | Bedeutung |
|---|---|
| `$@COURSESECTIONBYID*<id>@$` | Verweis auf einen Abschnitt desselben Kurses |
| `$@COURSEVIEWBYID*<id>@$` | Verweis auf einen Kurs |
| `@@PLUGINFILE@@/<name>` | Datei aus derselben Aktivität |
| `$@NULL@$` | leeres Feld (nicht als Text behandeln) |

Diese Platzhalter beim Übersetzen **unverändert lassen** — sie sind der Grund, warum
Moodle-eigene Links den Import überstehen und H5P-Links nicht.

## Selbst eine Sicherung schreiben

Reihenfolge beim Neupacken:

1. `.ARCHIVE_INDEX` als **erstes** Mitglied
2. alle übrigen Dateien in beliebiger Reihenfolge

Sinnvoll ist der Streaming-Weg: Originalarchiv sequenziell lesen, dabei das neue
schreiben und einzelne Mitglieder ersetzen. So braucht man nie 1 GB Zwischenspeicher.
`kurs_bauen.py` macht genau das — inklusive des Zweitdurchlaufs, der den fertigen Index
vorne einfügt.

## Prüfen ohne Moodle

Was sich statisch feststellen lässt:

- jedes XML ist wohlgeformt
- jede in `files.xml` genannte Prüfsumme liegt als Datei im Archiv, mit passender Größe
- die Prüfsumme stimmt mit dem Inhalt überein (sonst lehnt Moodle die Datei ab)
- jeder Medienverweis im H5P-Inhalt hat einen Eintrag in `files.xml`
- der Archivindex zählt richtig

Was sich **nicht** statisch feststellen lässt: ob Moodles Restore-Code zufrieden ist.
Dafür braucht es eine echte Instanz — siehe Skill `moodle-testinstanz`.
