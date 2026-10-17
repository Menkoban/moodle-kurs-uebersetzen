# moodle-kurs-uebersetzen

Ein Skill für [Claude Code](https://claude.com/claude-code): Er bringt einen fertigen
Moodle-Kurs in eine weitere Sprache, ohne die Videos neu zu drehen.

Die Moodle-Sicherung (`.mbz`) dient als Vorlage. Bild und Kursaufbau bleiben gleich,
ausgetauscht werden der gesprochene Ton der Videos, die Texte, die Testfragen und
die Beschriftungen eines H5P-Rundgangs (Virtual Tour 360°).

Entstanden für die Sicherheitsbelehrungen (UVV) an einer berufsbildenden Schule.
So wurde zum Beispiel aus dem deutschen Kurs Hauswirtschaft mit 24 Videos je eine
Fassung auf Französisch, Ukrainisch und Spanisch.

## Was man braucht

| Werkzeug | Wofür | Installation (Windows) |
|---|---|---|
| Claude Code | führt den Skill aus | siehe claude.com/claude-code |
| Python 3.10 oder neuer | alle Skripte | `winget install Python.Python.3.12` |
| ffmpeg | Ton abtrennen, Video und Ton zusammenfügen | `winget install Gyan.FFmpeg` |
| faster-whisper, edge-tts | Sprechtexte erkennen, neu vertonen | `pip install -r requirements.txt` |

Ausführlich, auch für macOS und Linux und mit Hinweisen zu Platz, Zeit und
Datenschutz: [`references/installation.md`](references/installation.md).

## Einrichten

```
git clone https://github.com/Menkoban/moodle-kurs-uebersetzen.git %USERPROFILE%\.claude\skills\moodle-kurs-uebersetzen
pip install -r %USERPROFILE%\.claude\skills\moodle-kurs-uebersetzen\requirements.txt
```

Ob alles da ist (Python, ffmpeg, Pakete), zeigt `python scripts/einrichten.py` im
Skill-Ordner; fehlt etwas, holt `python scripts/einrichten.py --installieren` es nach.

Danach Claude Code neu starten. Der Skill meldet sich von selbst, sobald man zum
Beispiel schreibt: *„Übersetze diesen Kurs ins Französische"* und die `.mbz` nennt.

## Ablauf in Kürze

```
analyse.py → transkribieren.py → vorbereiten.py → (Claude übersetzt) →
vertonen.py → videos_bauen.py → kurs_bauen.py → pruefen.py
```

Was jeder Schritt tut, wie lange er dauert und welche Fehler typisch sind, steht in
[`SKILL.md`](SKILL.md) und [`references/fallstricke.md`](references/fallstricke.md).

## Kurs vor der Weitergabe testen (empfohlen)

Ob eine erzeugte Sicherung sich in Moodle wirklich einspielen lässt, prüft der
Schwester-Skill [moodle-testinstanz](https://github.com/Menkoban/moodle-testinstanz).
Er richtet ein kleines Moodle auf dem eigenen Rechner ein (nur Windows, ohne Docker).
Wichtig: Ohne das Plugin `mod_hvp` in diesem Test-Moodle überspringt Moodle den
H5P-Rundgang stillschweigend.

## Grenzen

- Steht deutscher Text **im Bild** des Videos, muss neu produziert werden.
- Videos, die von YouTube oder Vimeo eingebettet sind, liegen nicht in der Sicherung.
- H5P muss aus dem Plugin `mod_hvp` stammen, nicht aus Moodles eingebautem H5P.
- Der neue Ton ist nicht lippensynchron. Wer das braucht, erzeugt die Videos mit
  einem Avatar-Dienst (z. B. HeyGen) und legt die Aufnahmen vor `vertonen.py` in den
  Ton-Ordner. Vorhandene Dateien werden nicht überschrieben.
