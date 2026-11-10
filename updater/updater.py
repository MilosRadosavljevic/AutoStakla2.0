"""Updater.exe – zamenjuje root\\app novom verzijom i ponovo pokreće program.

Pokreće ga AutoStakla.exe (iz root\\update\\Updater.exe) pa se program zatvara:
    Updater.exe --root C:\\AutoStakla --staging C:\\AutoStakla\\update\\staging\\app --pid 1234 --exe AutoStakla.exe

Namerno bez zavisnosti od ostatka programa (samo standardna biblioteka).
"""
from __future__ import annotations

import argparse
import ctypes
import logging
import shutil
import subprocess
import sys
import time
from pathlib import Path

log = logging.getLogger("updater")


def wait_for_pid(pid: int, timeout: float = 60.0) -> bool:
    """Čeka da se proces završi. True ako se završio."""
    if sys.platform != "win32" or pid <= 0:
        return True
    SYNCHRONIZE = 0x00100000
    handle = ctypes.windll.kernel32.OpenProcess(SYNCHRONIZE, False, pid)
    if not handle:
        return True  # proces više ne postoji
    try:
        WAIT_OBJECT_0 = 0
        return ctypes.windll.kernel32.WaitForSingleObject(handle, int(timeout * 1000)) == WAIT_OBJECT_0
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)


def _retry(fn, what: str, attempts: int = 15, delay: float = 1.0):
    """Antivirus/indeksiranje zna kratko da zaključa fajlove – pokušaj više puta."""
    for i in range(1, attempts + 1):
        try:
            return fn()
        except OSError as e:
            log.warning("%s – pokušaj %d/%d nije uspeo: %s", what, i, attempts, e)
            if i == attempts:
                raise
            time.sleep(delay)


def perform_update(root: Path, staging: Path, *, delay: float = 1.0) -> None:
    """Zameni root\\app sa staging. Ako ne uspe, vrati staru verziju i podigne izuzetak."""
    app = root / "app"
    old = root / "app_old"
    if not staging.is_dir():
        raise RuntimeError(f"Nema nove verzije u {staging}")
    if old.exists():
        _retry(lambda: shutil.rmtree(old), "Brisanje starog app_old", delay=delay)

    if app.exists():
        _retry(lambda: app.rename(old), "Preimenovanje app -> app_old", delay=delay)
    try:
        _retry(lambda: shutil.move(str(staging), str(app)), "Premeštanje nove verzije", delay=delay)
    except Exception:
        log.exception("Nova verzija nije postavljena – vraćam staru")
        if app.exists():
            shutil.rmtree(app, ignore_errors=True)
        if old.exists():
            _retry(lambda: old.rename(app), "Vraćanje stare verzije", delay=delay)
        raise
    log.info("Nova verzija postavljena")
    if old.exists():
        shutil.rmtree(old, ignore_errors=True)


def message_box(text: str, title: str = "AutoStakla – ažuriranje") -> None:
    if sys.platform == "win32":
        ctypes.windll.user32.MessageBoxW(None, text, title, 0x10)  # MB_ICONERROR


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True, type=Path)
    p.add_argument("--staging", required=True, type=Path)
    p.add_argument("--pid", type=int, default=0)
    p.add_argument("--exe", default="AutoStakla.exe")
    a = p.parse_args(argv)

    (a.root / "logs").mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=a.root / "logs" / "updater.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        encoding="utf-8",
    )
    log.info("Updater start: %s", vars(a))
    ok = True
    try:
        if not wait_for_pid(a.pid):
            raise RuntimeError("Program se nije zatvorio na vreme.")
        time.sleep(1)  # da Windows otpusti fajlove
        perform_update(a.root, a.staging)
    except Exception as e:
        ok = False
        log.exception("Ažuriranje nije uspelo")
        message_box(
            "Ažuriranje nije uspelo, vraćena je prethodna verzija programa.\n\n"
            f"Detalji: {e}\n\nPošaljite dijagnostiku Milošu."
        )
    exe = a.root / "app" / a.exe
    if exe.exists():
        log.info("Pokrećem %s", exe)
        subprocess.Popen([str(exe)] + ([] if ok else ["--update-failed"]), cwd=str(exe.parent))
    else:
        log.error("Ne postoji %s – program ne može da se pokrene", exe)
        message_box(f"Program ne postoji na putanji:\n{exe}\n\nPozovite Miloša.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
