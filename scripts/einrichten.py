"""Prüft, ob auf diesem Rechner alles für den Skill da ist — und zieht auf Wunsch nach.

Aufruf:
    python scripts/einrichten.py               # nur prüfen und Liste ausgeben
    python scripts/einrichten.py --installieren  # Fehlendes nachinstallieren

Exit-Code 0: alles da. Exit-Code 1: etwas fehlt.

Für Tests lassen sich zwei Dinge von außen ersetzen, ohne das System zu ändern:
    EINRICHTEN_SUCHPFAD      Ordnerliste, in der nach ffmpeg/ffprobe gesucht wird
                             (Standard: der normale PATH)
    EINRICHTEN_REQUIREMENTS  Paketliste statt der requirements.txt des Skills
Nur Standardbibliothek.
"""
from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import os
import platform
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

SKILL_ORDNER = Path(__file__).resolve().parent.parent
MIN_PYTHON = (3, 10)
WERKZEUGE = ("ffmpeg", "ffprobe")


@dataclass
class Punkt:
    name: str
    ok: bool
    abhilfe: str = ""
    art: str = ""  # "python", "werkzeug", "paket"


def requirements_pfad() -> Path:
    eigener = os.environ.get("EINRICHTEN_REQUIREMENTS")
    return Path(eigener) if eigener else SKILL_ORDNER / "requirements.txt"


def suchpfad() -> str | None:
    """None heißt: normaler PATH."""
    return os.environ.get("EINRICHTEN_SUCHPFAD")


def pakete_lesen(pfad: Path) -> list[str]:
    """Paketnamen aus einer requirements-Datei, ohne Versionsangaben und Kommentare."""
    namen = []
    for zeile in pfad.read_text(encoding="utf-8").splitlines():
        zeile = zeile.split("#", 1)[0].strip()
        if not zeile or zeile.startswith("-"):
            continue
        name = re.split(r"[\s\[<>=!~;@]", zeile, maxsplit=1)[0]
        if name:
            namen.append(name)
    return namen


def _normalisieren(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def importname(paketname: str) -> str:
    """Paketname (pip) → Name, unter dem man es importiert.

    Ist das Paket installiert, sagt importlib.metadata, welche Module es
    mitbringt. Sonst gilt die übliche Regel: Bindestriche werden Unterstriche.
    """
    gesucht = _normalisieren(paketname)
    kandidaten = []
    try:
        zuordnung = importlib.metadata.packages_distributions()
    except Exception:
        zuordnung = {}
    for modul, verteilungen in zuordnung.items():
        if any(_normalisieren(v) == gesucht for v in verteilungen):
            if not modul.startswith("_") and modul.isidentifier():
                kandidaten.append(modul)
    if kandidaten:
        bevorzugt = gesucht.replace("-", "_")
        if bevorzugt in kandidaten:
            return bevorzugt
        return sorted(kandidaten)[0]
    return paketname.replace("-", "_").replace(".", "_").lower()


def _paket_vorhanden(paketname: str) -> bool:
    try:
        return importlib.util.find_spec(importname(paketname)) is not None
    except (ImportError, ValueError):
        return False


def ffmpeg_befehl() -> str:
    system = platform.system()
    if system == "Windows":
        return ("winget install --id Gyan.FFmpeg -e "
                "--accept-source-agreements --accept-package-agreements")
    if system == "Darwin":
        return "brew install ffmpeg"
    return "sudo apt install ffmpeg   (bzw. das Paketprogramm Ihrer Linux-Ausgabe)"


def pip_befehl(req: Path) -> list[str]:
    return [sys.executable, "-m", "pip", "install", "-r", str(req)]


def pruefen(req: Path | None = None, pfad: str | None = None) -> list[Punkt]:
    req = req or requirements_pfad()
    pfad = pfad if pfad is not None else suchpfad()
    punkte = []

    version = ".".join(map(str, sys.version_info[:3]))
    punkte.append(Punkt(
        f"Python {version} (nötig: {MIN_PYTHON[0]}.{MIN_PYTHON[1]} oder neuer)",
        sys.version_info[:2] >= MIN_PYTHON,
        "Neueres Python von https://www.python.org/downloads/ installieren",
        "python",
    ))
    for werkzeug in WERKZEUGE:
        gefunden = shutil.which(werkzeug, path=pfad) if pfad is not None else shutil.which(werkzeug)
        punkte.append(Punkt(werkzeug, gefunden is not None, ffmpeg_befehl(), "werkzeug"))
    for paket in pakete_lesen(req):
        punkte.append(Punkt(
            f"Python-Paket {paket}", _paket_vorhanden(paket),
            " ".join(f'"{t}"' if " " in t else t for t in pip_befehl(req)), "paket",
        ))
    return punkte


def ausgeben(punkte: list[Punkt]) -> bool:
    print("Prüfung: Was braucht der Skill moodle-kurs-uebersetzen?\n")
    for p in punkte:
        print(f"  [{'ok   ' if p.ok else 'fehlt'}]  {p.name}")
        if not p.ok:
            print(f"           So beheben: {p.abhilfe}")
    alles_da = all(p.ok for p in punkte)
    print()
    if alles_da:
        print("Alles da. Der Skill kann loslegen.")
    else:
        print("Es fehlt etwas. Nachinstallieren mit:")
        print("    python scripts/einrichten.py --installieren")
    return alles_da


def installieren(punkte: list[Punkt], req: Path) -> None:
    if any(p.art == "paket" and not p.ok for p in punkte):
        print("\nInstalliere fehlende Python-Pakete …")
        subprocess.run(pip_befehl(req), check=False)
    if any(p.art == "werkzeug" and not p.ok for p in punkte):
        system = platform.system()
        if system == "Windows":
            print("\nInstalliere ffmpeg über winget …")
            subprocess.run(ffmpeg_befehl().split(), check=False)
            print("Hinweis: Nach winget ist oft ein NEUES Terminal (bzw. ein Neustart "
                  "von Claude Code) nötig, damit ffmpeg gefunden wird.")
        elif system == "Darwin":
            print("\nInstalliere ffmpeg über Homebrew …")
            subprocess.run(["brew", "install", "ffmpeg"], check=False)
        else:
            print("\nffmpeg bitte selbst installieren (braucht Administratorrechte):")
            print(f"    {ffmpeg_befehl()}")
    if any(p.art == "python" and not p.ok for p in punkte):
        print("\nPython selbst kann dieses Skript nicht erneuern — bitte von Hand "
              "installieren: https://www.python.org/downloads/")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--installieren", action="store_true",
                        help="fehlende Pakete und ffmpeg nachinstallieren")
    args = parser.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    req = requirements_pfad()
    punkte = pruefen(req)
    alles_da = ausgeben(punkte)
    if args.installieren and not alles_da:
        installieren(punkte, req)
        importlib.invalidate_caches()
        print("\n--- Erneute Prüfung ---\n")
        alles_da = ausgeben(pruefen(req))
    return 0 if alles_da else 1


if __name__ == "__main__":
    sys.exit(main())
