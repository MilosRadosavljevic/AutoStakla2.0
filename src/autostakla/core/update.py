"""Update iz zip paketa.

Paket (pravi ga build.ps1):
    manifest.json        {"app_id": "AutoStakla", "edition": "...", "version": "x.y.z"}
    app/AutoStakla.exe
    app/Updater.exe
    app/_internal/...

Tok: validate_package -> prepare -> launch_updater -> program se zatvara.
Updater zameni root\\app i ponovo pokrene program.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from autostakla import version
from autostakla.core import paths

log = logging.getLogger(__name__)

# Ključ u tabeli podesavanja: verzija na koju je update pokrenut (proverava se pri sledećem startu)
KEY_UPDATE_IN_PROGRESS = "update_u_toku"

EXE_NAME = "AutoStakla.exe"
UPDATER_NAME = "Updater.exe"


class UpdateError(Exception):
    """Greška sa porukom razumljivom korisniku."""


@dataclass
class PackageInfo:
    zip_path: Path
    app_id: str
    edition: str
    version: str

    @property
    def comparison(self) -> int:
        """-1 starija, 0 ista, 1 novija od trenutne."""
        new, cur = version.version_tuple(self.version), version.version_tuple(version.VERSION)
        return (new > cur) - (new < cur)


def validate_package(zip_path: Path) -> PackageInfo:
    if not zipfile.is_zipfile(zip_path):
        raise UpdateError("Izabrani fajl nije ispravan zip paket.")
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        for n in names:
            p = PurePosixPath(n.replace("\\", "/"))
            if p.is_absolute() or ".." in p.parts or (p.parts and ":" in p.parts[0]):
                raise UpdateError("Paket sadrži neispravne putanje.")
        if "manifest.json" not in names:
            raise UpdateError("Ovo nije paket za AutoStakla (nema manifest.json).")
        try:
            manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
            info = PackageInfo(
                zip_path=zip_path,
                app_id=str(manifest["app_id"]),
                edition=str(manifest["edition"]),
                version=str(manifest["version"]),
            )
            version.version_tuple(info.version)
        except (KeyError, ValueError) as e:
            raise UpdateError(f"manifest.json u paketu nije ispravan ({e}).") from e
        if info.app_id != version.APP_ID:
            raise UpdateError(f"Paket je za program '{info.app_id}', ne za AutoStakla.")
        for required in (f"app/{EXE_NAME}", f"app/{UPDATER_NAME}"):
            if required not in names:
                raise UpdateError(f"Paket nije potpun (nedostaje {required}).")
        bad = zf.testzip()
        if bad:
            raise UpdateError(f"Paket je oštećen (fajl {bad}). Pošaljite ga ponovo.")
    return info


def prepare(info: PackageInfo) -> tuple[Path, Path]:
    """Raspakuje paket u root\\update\\staging i kopira Updater van app foldera.

    Vraća (putanja do Updater.exe, putanja do novog app foldera).
    """
    upd = paths.update_dir()
    if upd.exists():
        shutil.rmtree(upd, ignore_errors=True)
    staging = upd / "staging"
    staging.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(info.zip_path) as zf:
        zf.extractall(staging)
    new_app = staging / "app"
    updater = upd / UPDATER_NAME
    shutil.copy2(new_app / UPDATER_NAME, updater)
    log.info("Update %s pripremljen u %s", info.version, staging)
    return updater, new_app


def launch_updater(updater: Path, new_app: Path) -> None:
    args = [
        str(updater),
        "--root", str(paths.root_dir()),
        "--staging", str(new_app),
        "--pid", str(os.getpid()),
        "--exe", EXE_NAME,
    ]
    log.info("Pokrećem updater: %s", args)
    flags = 0
    if sys.platform == "win32":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(args, creationflags=flags, close_fds=True)


def cleanup_after_update() -> None:
    """Pri startu: ukloni ostatke prethodnog update-a (ako ih ima)."""
    for p in (paths.update_dir(), paths.root_dir() / "app_old"):
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)
