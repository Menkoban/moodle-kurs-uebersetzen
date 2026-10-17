"""Tests für scripts/einrichten.py (nur Prüfen, nie --installieren)."""
import os
import subprocess
import sys
from pathlib import Path

SKRIPT = Path(__file__).resolve().parent.parent / "scripts" / "einrichten.py"


def _platzhalter_werkzeuge(ordner: Path) -> Path:
    """Legt leere ffmpeg/ffprobe-Dateien an, die als 'vorhanden' gelten."""
    ordner.mkdir(parents=True, exist_ok=True)
    for name in ("ffmpeg", "ffprobe"):
        if os.name == "nt":
            datei = ordner / f"{name}.exe"
            datei.write_bytes(b"")
        else:
            datei = ordner / name
            datei.write_text("#!/bin/sh\n")
            datei.chmod(0o755)
    return ordner


def _starten(tmp_path, requirements_zeilen, suchpfad):
    req = tmp_path / "requirements-test.txt"
    req.write_text("\n".join(requirements_zeilen) + "\n", encoding="utf-8")
    env = dict(os.environ)
    env["EINRICHTEN_SUCHPFAD"] = str(suchpfad)
    env["EINRICHTEN_REQUIREMENTS"] = str(req)
    return subprocess.run(
        [sys.executable, str(SKRIPT)],
        capture_output=True, text=True, encoding="utf-8", env=env,
    )


def test_ffmpeg_fehlt_gibt_exit_1(tmp_path):
    leer = tmp_path / "leer"
    leer.mkdir()
    erg = _starten(tmp_path, ["pip"], leer)
    assert erg.returncode == 1, erg.stdout + erg.stderr
    zeilen = [z for z in erg.stdout.splitlines() if "ffmpeg" in z.lower() and "fehlt" in z]
    assert zeilen, erg.stdout


def test_erfundenes_paket_fehlt_gibt_exit_1(tmp_path):
    werkzeuge = _platzhalter_werkzeuge(tmp_path / "bin")
    erg = _starten(tmp_path, ["pip", "gibt-es-nicht-xyz-4711>=1.0"], werkzeuge)
    assert erg.returncode == 1, erg.stdout + erg.stderr
    zeilen = [z for z in erg.stdout.splitlines() if "gibt-es-nicht-xyz-4711" in z]
    assert zeilen and "fehlt" in zeilen[0], erg.stdout


def test_alles_vorhanden_gibt_exit_0(tmp_path):
    werkzeuge = _platzhalter_werkzeuge(tmp_path / "bin")
    erg = _starten(tmp_path, ["# Kommentar", "", "pip"], werkzeuge)
    assert erg.returncode == 0, erg.stdout + erg.stderr
    assert "fehlt" not in erg.stdout


def test_paketname_wird_auf_importnamen_abgebildet():
    sys.path.insert(0, str(SKRIPT.parent))
    try:
        import einrichten
    finally:
        sys.path.pop(0)
    assert einrichten.importname("faster-whisper") == "faster_whisper"
    assert einrichten.importname("edge-tts") == "edge_tts"
    # Paketname weicht vom Importnamen ab: über importlib.metadata gelöst
    assert einrichten.importname("pip") == "pip"
