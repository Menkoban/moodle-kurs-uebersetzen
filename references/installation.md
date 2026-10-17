# Einrichtung auf einem neuen Rechner

Für Kolleginnen und Kollegen, die den Skill weitergegeben bekommen haben.

## 1. Skill ablegen

Den Ordner `moodle-kurs-uebersetzen` nach `~/.claude/skills/` kopieren
(unter Windows: `C:\Users\<Name>\.claude\skills\`). Claude Code findet ihn beim
nächsten Start von selbst.

## 2. Werkzeuge installieren

**ffmpeg** — trennt Ton ab und setzt Videos neu zusammen:

```
winget install Gyan.FFmpeg
```

Danach ein neues Terminal öffnen und prüfen: `ffmpeg -version`.
Auf macOS: `brew install ffmpeg`. Auf Linux: `apt install ffmpeg`.

**Python-Pakete:**

```
pip install faster-whisper edge-tts
```

- `faster-whisper` holt die Sprechtexte aus den Videos. Läuft vollständig auf dem
  eigenen Rechner, es geht nichts ins Netz. Beim ersten Lauf lädt es sein Modell
  herunter (bei `medium` etwa 1,5 GB, einmalig).
- `edge-tts` erzeugt die Vertonung über den Sprachdienst von Microsoft Edge.
  Kostenlos, braucht aber eine Internetverbindung; der zu sprechende Text wird
  dorthin übertragen.

## 3. Platz und Zeit

| | Größenordnung |
|---|---|
| Arbeitsordner | etwa das Dreifache der Sicherung (Videos liegen mehrfach vor) |
| Transkription | rund das Doppelte der Spielzeit auf einer normalen CPU |
| Videos zusammensetzen | etwa 25 Sekunden je Minute Video |

Ein Kurs mit 20 Minuten Video und 600 MB Sicherung braucht also ungefähr 2 GB Platz
und eineinhalb Stunden Rechenzeit, verteilt auf mehrere Schritte.

## 4. Datenschutz

- Die Transkription läuft lokal.
- Die Vertonung schickt die **übersetzten Sprechtexte** an Microsoft. Bei Kursinhalten
  ist das unproblematisch; personenbezogene Daten gehören ohnehin nicht in Kurstexte.
- Sicherungen **ohne Nutzerdaten** exportieren (beim Export die Häkchen für
  Teilnehmer und Bewertungen abwählen). Die Skripte brauchen sie nicht, und die
  Datei wird deutlich kleiner.

## 5. Erster Lauf

Klein anfangen: einen Kurs mit wenigen Videos nehmen, `analyse.py` laufen lassen und
die erzeugte `kurs.json` ansehen. Steht dort die richtige Zahl an Videos, Abschnitten
und Texten, passt der Rest auch.
