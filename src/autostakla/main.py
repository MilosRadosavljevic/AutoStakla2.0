"""Ulazna tačka programa AutoStakla."""
from __future__ import annotations

import logging
import sys

from PySide6.QtCore import QLockFile
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from autostakla import version
from autostakla.core import audit, backup, db, logging_setup, paths, update
from autostakla.ui import tema
from autostakla.ui.main_window import MainWindow, StaJeNovoDialog

log = logging.getLogger("autostakla.main")

KEY_UPDATE_IN_PROGRESS = update.KEY_UPDATE_IN_PROGRESS


def _show_error(text: str) -> None:
    QMessageBox.critical(
        None,
        version.APP_NAME,
        "Došlo je do greške:\n\n"
        f"{text}\n\n"
        "Detalji su sačuvani. Ako se greška ponavlja, napravite dijagnostiku\n"
        "(Alati → Napravi dijagnostiku) i pošaljite je Milošu.",
    )


def open_database():
    """Otvara bazu, pravi backup i primenjuje migracije koje fale."""
    conn = db.connect()
    pending = db.pending_migrations(conn)
    if pending:
        if db.current_version(conn) > 0:
            backup.make_backup(conn, "pre_migracije")
        applied = db.apply_migrations(conn, None)
        audit.write(
            conn, "MIGRACIJA",
            opis="Primenjene migracije: " + ", ".join(f"{m.number:03d}_{m.name}" for m in applied),
        )
    return conn


def _report_finished_update(conn, window) -> None:
    row = conn.execute(
        "SELECT vrednost FROM podesavanja WHERE kljuc = ?", (KEY_UPDATE_IN_PROGRESS,)
    ).fetchone()
    if not row:
        return
    conn.execute("DELETE FROM podesavanja WHERE kljuc = ?", (KEY_UPDATE_IN_PROGRESS,))
    if row[0] == version.VERSION:
        audit.write(conn, "UPDATE", opis=f"Uspešno ažurirano na verziju {version.VERSION}")
        QMessageBox.information(
            window, version.APP_NAME, f"Program je uspešno ažuriran na verziju {version.VERSION}.\n\n"
                                      "Sada će se prikazati šta je novo."
        )
        StaJeNovoDialog.prikazi(window)
    else:
        audit.write(conn, "UPDATE", opis=f"Ažuriranje na {row[0]} NIJE uspelo, radi {version.VERSION}")


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(version.APP_NAME)
    app.setApplicationVersion(version.VERSION)
    icon_file = paths.resource_dir() / "resources" / "icon.ico"
    if icon_file.exists():
        app.setWindowIcon(QIcon(str(icon_file)))

    paths.ensure_dirs()
    logging_setup.setup_logging()
    logging_setup.set_error_notifier(_show_error)

    # Ime koje instalacija proverava (AppMutex) – ne instalira se dok program radi.
    if sys.platform == "win32":
        import ctypes

        _mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "AutoStaklaMutex")  # noqa: F841

    lock = QLockFile(str(paths.root_dir() / "autostakla.lock"))
    lock.setStaleLockTime(0)
    if not lock.tryLock(100):
        QMessageBox.information(None, version.APP_NAME, "Program je već pokrenut.")
        return 0

    update.cleanup_after_update()

    try:
        conn = open_database()
    except db.DatabaseNewerError as e:
        log.error(str(e))
        QMessageBox.critical(
            None, version.APP_NAME,
            f"{e}\n\nPokrenite najnoviju verziju programa ili pozovite Miloša.",
        )
        return 1
    except Exception as e:
        log.exception("Baza ne može da se otvori")
        _show_error(f"Baza ne može da se otvori: {e}")
        return 1

    audit.write(conn, "START", opis=f"{version.APP_NAME} {version.VERSION}")
    tema.ucitaj(conn)
    window = MainWindow(conn)
    window.show()
    _report_finished_update(conn, window)

    rc = app.exec()

    if not window.closing_for_update:
        try:
            backup.make_backup(conn, "zatvaranje")
        except Exception:
            log.exception("Backup pri zatvaranju nije uspeo")
    audit.write(conn, "KRAJ")
    conn.close()
    lock.unlock()
    log.info("Kraj rada")
    return rc


if __name__ == "__main__":
    sys.exit(main())
