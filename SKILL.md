---
name: moodle-kurs-uebersetzen
description: Use when a Moodle course backup (.mbz) with narrated videos or an H5P virtual tour must be made available in another language - translating hotspot labels, quiz questions and spoken video audio, or asked to "Kurs übersetzen", "mehrsprachiger Moodle-Kurs", "Sicherheitsbelehrung in weiteren Sprachen", "H5P-Rundgang auf Französisch/Ukrainisch/Arabisch".
---

# Moodle-Kurs in eine weitere Sprache bringen

## Überblick

Eine fertige Moodle-Sicherung wird zur Vorlage: Bild und Kursstruktur bleiben, Ton und
Texte werden ausgetauscht. Das spart die Neuproduktion der Videos — bei einem Kurs mit
zwei Dutzend Avatar-Videos ist das der Unterschied zwischen einem Nachmittag und einer
Woche Arbeit.

**Kernprinzip: Der Ton bestimmt, das Bild folgt.** Die neue Aufnahme wird nie
beschleunigt, um ins Bild zu passen — das Bild wird an die Tonlänge angepasst.
Zielgruppe solcher Kurse sind Lernende mit geringen Sprachkenntnissen; Verständlichkeit
schlägt Bildtempo. Lippensynchron wird es beim Tonaustausch ohnehin nicht.

## Wann dieser Skill passt

- Ein Kurs existiert und funktioniert — es fehlt nur die Sprache
- Die Videos sind Avatar- oder Screencast-Aufnahmen (kein Gesicht, das Deutsch spricht)
- H5P-Inhalte (Virtual Tour 360°, Interactive Video), Tests, Textseiten
- Auch für Kurse ohne H5P: dann entfallen nur die Rundgang-Schritte

**Nicht geeignet, wenn:**

- im Bild deutscher Text steht (Beschriftungen im Video, eingeblendete Folien) — das
  lässt sich nicht austauschen, hier muss neu produziert werden
- die Videos von YouTube oder Vimeo eingebettet sind statt in der Sicherung zu liegen
- der H5P-Inhalt aus **`mod_h5pactivity`** stammt (Moodles eingebaute H5P-Variante).
  Dort liegt der Inhalt als gepackte `.h5p`-Datei, nicht als Text im XML. `analyse.py`
  meldet das und schreibt es nach `hinweise.md`. Bearbeitbar ist nur **`mod_hvp`**,
  das separat installierte Plugin — daran erkennbar, dass die Aktivitätsordner
  `activities/hvp_<nummer>` heißen.

## Voraussetzungen

Vor dem ersten Lauf `python scripts/einrichten.py` aufrufen: das prüft, ob alles unten Genannte da ist. Fehlt etwas, den Nutzer fragen und erst nach seinem Ja mit `python scripts/einrichten.py --installieren` nachziehen.

| Werkzeug | Wofür | Installation |
|---|---|---|
| Python 3.10+ | alle Skripte | vorhanden |
| ffmpeg + ffprobe | Ton abtrennen, Video und Ton zusammenfügen | `winget install --id Gyan.FFmpeg -e` |
| faster-whisper | Sprechtexte aus den Videos holen (lokal, offline) | `pip install faster-whisper` |
| edge-tts | Vertonung (kostenlos, braucht Internet) | `pip install edge-tts` |

Beim ersten Lauf lädt faster-whisper sein Modell (~1,5 GB bei `medium`).

## Ablauf

Alle Skripte liegen in `scripts/`, arbeiten auf **einem Arbeitsordner** und sind mehrfach
aufrufbar — fertige Zwischenergebnisse werden nicht überschrieben.

```
python analyse.py        kurs.mbz arbeitsordner
python transkribieren.py arbeitsordner
python vorbereiten.py    arbeitsordner fr
        → uebersetzung_fr.json und sprechtexte_fr.json ausfüllen (siehe unten)
python vertonen.py       arbeitsordner fr fr-FR-HenriNeural
python videos_bauen.py   arbeitsordner fr
python kurs_bauen.py     arbeitsordner fr fertig-fr.mbz --kursname "..." --quizid 12345
python pruefen.py        fertig-fr.mbz arbeitsordner
```

Läuft der Zielkurs schon und darf nicht neu importiert werden, tritt an die Stelle von
`kurs_bauen.py` der Zusatz `aktivitaet_bauen.py` — er löst eine einzelne Aktivität
heraus, sodass die übrigen Modulnummern des Kurses erhalten bleiben.

`--help` gibt es nicht; jedes Skript zeigt seine Aufrufform, wenn Argumente fehlen.

### Nach der Analyse: einmal kurz nachfragen

`analyse.py` zeigt, was gefunden wurde. **Bevor du übersetzt, die Liste durchsehen und
den Nutzer fragen, was in der Ausgangssprache bleiben soll.** Typische Kandidaten:

- Seiten, die sich an die Lehrkraft richten, nicht an die Lernenden
- Hinweise auf deutsches Recht, Schulordnung, Ansprechpersonen mit Namen
- unbenutzte Altbestände in der Fragensammlung
- Fassungen, die schon in einer anderen Sprache vorliegen

Das ist die einzige Stelle, an der Rückfragen nötig sind — die Kursstruktur selbst wird
nicht angetastet und muss nicht besprochen werden. Der Skill übersetzt einen Kurs, er
baut keinen: Was hineingeht, kommt mit identischer Struktur in der neuen Sprache heraus.

### Das Übersetzen selbst

`vorbereiten.py` legt zwei Dateien mit leeren Zielfeldern an. **Diese füllst du (Claude)
aus** — nicht per Skript, weil hier Sprachgefühl und Fachkenntnis nötig sind:

- `uebersetzung_<code>.json` — Oberflächentexte: `"deutscher Text": ""`. HTML-Gerüst
  (`<p>`, `<strong>`, Farb-Styles) unverändert übernehmen, nur den Fließtext ersetzen.
- `sprechtexte_<code>.json` — je Video `"deutsch"` als Vorlage, `"text"` ausfüllen.

Leere Felder bleiben in der Ausgangssprache stehen — so lässt sich bewusst etwas
auslassen (etwa eine Seite, die sich an die deutschsprachige Lehrkraft richtet).

**Sprachniveau:** einfache Sätze, direkte Anrede (tu / ти / tú), keine Schachtelsätze.
Diese Kurse richten sich an Sprachlernende.

**Nacharbeit durch Menschen:** Bei Sprachen mit schwacher maschineller Qualität
(Somali, Paschtu, Kurdisch) die JSON-Dateien einer Muttersprachlerin geben, dann
`kurs_bauen.py` erneut laufen lassen. Die Dateien sind genau dafür da.

### Stimme wählen

```bash
edge-tts --list-voices | grep ^fr-FR
```

Geschlecht der Stimme zum sichtbaren Avatar passend wählen — der neue Ton liegt auf dem
alten Bild. Ob das Original männlich oder weiblich ist, verrät die Grundfrequenz:
männlich etwa 85–155 Hz, weiblich 165–255 Hz.

## Quick Reference

| Schritt | Skript | Dauer bei 20 Min Video |
|---|---|---|
| Sicherung einlesen, Videos und Ton herausziehen | `analyse.py` | 1–2 min |
| Sprechtexte transkribieren | `transkribieren.py` | 20–40 min |
| Übersetzungsdateien anlegen | `vorbereiten.py` | Sekunden |
| Vertonen | `vertonen.py` | 2–3 min |
| Videos neu zusammensetzen | `videos_bauen.py` | 10–15 min |
| Sicherung schreiben | `kurs_bauen.py` | 1 min |
| Prüfen | `pruefen.py` | 1–2 min |

## Häufige Fehler

| Fehler | Folge | Vermeidung |
|---|---|---|
| Ton beschleunigen, damit er ins Bild passt | Zielgruppe versteht weniger | Bild anpassen, nie den Ton |
| Fest verdrahtete Links übersehen | Lernende landen im deutschen Kurs | `hinweise.md` lesen, `--quizid` setzen |
| Nur den Kurs prüfen, den man sieht | H5P-Bedienknöpfe bleiben deutsch | `pruefen.py` mit Arbeitsordner aufrufen |
| Neu importieren statt Aktivität tauschen | Verweise zeigen auf den alten Kurs | siehe `references/fallstricke.md` |
| Sicherung ungeprüft weitergeben | Import scheitert beim Kollegen | immer `pruefen.py` vor der Übergabe |

## Weiterführend

- `references/fallstricke.md` — was beim Wiederherstellen schiefgeht und warum
- `references/aufbau-mbz.md` — wie eine .mbz aufgebaut ist, für eigene Eingriffe

**Verwandter Skill:** `moodle-testinstanz` spielt eine fertige Sicherung lokal
wirklich ein. Beachten: Ohne installiertes `mod_hvp` überspringt Moodle den H5P-Inhalt
stillschweigend — ein erfolgreicher Restore beweist dann noch nicht, dass der Rundgang
funktioniert.
