"""Glavni prozor: meni Alati (provera baze, backup, update, dijagnostika)."""
from __future__ import annotations

import logging
import os
import sqlite3
from pathlib import Path

from datetime import datetime

from PySide6.QtCore import QStandardPaths, Qt
from PySide6.QtGui import QAction, QActionGroup, QFont
from PySide6.QtWidgets import (
    QPlainTextEdit,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QVBoxLayout,
)

from autostakla import version
from autostakla.core import audit, backup, db, diagnostics, paths, update
from autostakla.lager import repo, stampa
from autostakla.ui.lager_view import LagerView
from autostakla.ui import tema
from autostakla.ui.skladista_dialog import SkladistaDialog


class StaJeNovoDialog(QDialog):
    """Prikaz OBAVEZNO_PROCITAJ.txt koji ide uz ovu verziju programa."""

    def __init__(self, parent, text: str):
        super().__init__(parent)
        self.setWindowTitle(f"Šta je novo – {version.APP_NAME} {version.VERSION}")
        view = QPlainTextEdit(text)
        view.setReadOnly(True)
        f = QFont("Consolas")
        f.setPointSize(10)
        view.setFont(f)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.button(QDialogButtonBox.StandardButton.Close).setText("Zatvori")
        bb.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addWidget(view)
        lay.addWidget(bb)
        self.resize(760, 600)

    @staticmethod
    def tekst() -> str | None:
        f = paths.docs_dir() / paths.PROCITAJ_TXT
        return f.read_text(encoding="utf-8-sig") if f.exists() else None

    @classmethod
    def prikazi(cls, parent) -> bool:
        t = cls.tekst()
        if t is None:
            QMessageBox.information(parent, "Šta je novo", "Opis izmena nije pronađen uz program.")
            return False
        cls(parent, t).exec()
        return True


class StampaDialog(QDialog):
    """Izbor skladišta za štampu spiska."""

    def __init__(self, parent, conn):
        super().__init__(parent)
        self.setWindowTitle("Štampa spiska po skladištima")
        self.lst = QListWidget()
        for s in repo.list_skladista(conn):
            it = QListWidgetItem(s["naziv"])
            it.setData(Qt.ItemDataRole.UserRole, s["id"])
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Checked)
            self.lst.addItem(it)
        self.nova = QCheckBox("svako skladište na novoj strani")
        self.nova.setChecked(True)
        sve = QCheckBox("izaberi sve")
        sve.setChecked(True)
        sve.toggled.connect(lambda on: [self.lst.item(i).setCheckState(
            Qt.CheckState.Checked if on else Qt.CheckState.Unchecked) for i in range(self.lst.count())])
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.button(QDialogButtonBox.StandardButton.Ok).setText("Napravi PDF")
        bb.button(QDialogButtonBox.StandardButton.Cancel).setText("Otkaži")
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Koja skladišta da odštampam?"))
        lay.addWidget(sve)
        lay.addWidget(self.lst)
        lay.addWidget(self.nova)
        lay.addWidget(bb)
        self.resize(380, 460)

    def values(self) -> tuple[list[int], bool]:
        ids = [self.lst.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.lst.count())
               if self.lst.item(i).checkState() == Qt.CheckState.Checked]
        return ids, self.nova.isChecked()

log = logging.getLogger(__name__)

KEY_UPDATE_IN_PROGRESS = update.KEY_UPDATE_IN_PROGRESS


class MainWindow(QMainWindow):
    def __init__(self, conn: sqlite3.Connection) -> None:
        super().__init__()
        self.conn = conn
        self.closing_for_update = False
        self.setWindowTitle(f"{version.APP_NAME} {version.VERSION}")
        self.resize(1280, 800)
        self._build_menu()
        self._build_central()
        self.refresh_status()

    # ---------- izgled ----------
    def _build_menu(self) -> None:
        mb = self.menuBar()

        m_file = mb.addMenu("&Datoteka")
        m_file.addAction(self._action("Izlaz", self.close, "Ctrl+Q"))

        m_sif = mb.addMenu("&Šifarnici")
        m_sif.addAction(self._action("Skladišta i police…", self.skladista))

        if version.is_better():
            m_pos = mb.addMenu("P&oslovanje")
            m_pos.addAction(self._action("Prodaja…", self.prodaja, "Ctrl+R"))
            m_pos.addAction(self._action("Reklamacije…", self.reklamacije))
            m_pos.addAction(self._action("Analitika…", self.analitika))
            m_pos.addSeparator()
            m_pos.addAction(self._action("Predračuni i otpremnice…", self.dokumenti))
            m_pos.addSeparator()
            m_pos.addAction(self._action("Dobavljači…", self.dobavljaci))
            m_pos.addAction(self._action("Cene izabranog stakla po dobavljačima…", self.cene))
            m_pos.addAction(self._action("Vozila iz naziva stakla…", self.vozila))
            m_pos.addSeparator()
            m_pos.addAction(self._action("Podaci o firmi i PDV…", self.firma))

        m_print = mb.addMenu("Š&tampa")
        m_print.addAction(self._action("Spisak po skladištima (PDF)…", self.print_spisak, "Ctrl+P"))
        m_print.addAction(self._action("Trenutni prikaz (PDF)", self.print_prikaz))

        m_view = mb.addMenu("&Prikaz")
        grp = QActionGroup(self)
        self.tema_akcije = {}
        for key, text in (("svetla", "Svetla tema"), ("tamna", "Tamna tema")):
            a = QAction(text, self, checkable=True)
            a.triggered.connect(lambda _=False, k=key: self.set_tema(k))
            grp.addAction(a)
            m_view.addAction(a)
            self.tema_akcije[key] = a
        self.tema_akcije[tema.trenutna(self.conn)].setChecked(True)

        m_tools = mb.addMenu("&Alati")
        m_tools.addAction(self._action("Provera baze…", self.check_database))
        m_tools.addAction(self._action("Napravi backup sada", self.backup_now))
        m_tools.addAction(self._action("Otvori folder sa backup-ima", self.open_backup_folder))
        m_tools.addSeparator()
        m_tools.addAction(self._action("Ažuriraj iz fajla…", self.update_from_file))
        m_tools.addSeparator()
        m_tools.addAction(self._action("Napravi dijagnostiku…", self.make_diagnostics))

        m_help = mb.addMenu("&Pomoć")
        m_help.addAction(self._action("Korisničko uputstvo (PDF)", self.uputstvo, "F1"))
        m_help.addAction(self._action("Šta je novo u ovoj verziji", self.sta_je_novo))
        m_help.addSeparator()
        m_help.addAction(self._action("O programu", self.about))

    def _action(self, text: str, slot, shortcut: str | None = None) -> QAction:
        a = QAction(text, self)
        a.triggered.connect(slot)
        if shortcut:
            a.setShortcut(shortcut)
        return a

    def _build_central(self) -> None:
        self.lager = LagerView(self.conn, self)
        self.setCentralWidget(self.lager)
        self.lager.search.setFocus()

    def set_tema(self, key: str) -> None:
        tema.promeni(self.conn, key)
        audit.write(self.conn, "PODESAVANJE", opis=f"Tema: {key}")
        self.tema_akcije[key].setChecked(True)

    # ---------- lager ----------
    def skladista(self) -> None:
        d = SkladistaDialog(self, self.conn)
        d.exec()
        if d.changed:
            self.lager.reload_filters()

    # ---------- poslovanje (Better) ----------
    def prodaja(self) -> None:
        from autostakla.ui.better.prodaja_window import ProdajaDialog
        ProdajaDialog(self, self.conn).exec()

    def reklamacije(self) -> None:
        from autostakla.ui.better.prodaja_window import ReklamacijeDialog
        ReklamacijeDialog(self, self.conn).exec()

    def analitika(self) -> None:
        from autostakla.ui.better.analitika_window import AnalitikaDialog
        AnalitikaDialog(self, self.conn).exec()

    def dokumenti(self) -> None:
        from autostakla.ui.better.ostalo import DokumentiDialog
        DokumentiDialog(self, self.conn).exec()

    def dobavljaci(self) -> None:
        from autostakla.ui.better.dobavljaci_dialog import DobavljaciDialog
        DobavljaciDialog(self, self.conn).exec()

    def cene(self) -> None:
        from autostakla.ui.better.dobavljaci_dialog import CeneDialog
        r = self.lager.selected()
        if not r:
            QMessageBox.information(self, "Cene", "Izaberite staklo u tabeli, pa ponovo otvorite cene.")
            return
        CeneDialog(self, self.conn, r["staklo_id"]).exec()

    def vozila(self) -> None:
        from autostakla.ui.better.ostalo import VozilaDialog
        if VozilaDialog(self, self.conn).exec():
            self.lager.refresh()

    def firma(self) -> None:
        from autostakla.ui.better.ostalo import FirmaDialog
        FirmaDialog(self, self.conn).exec()

    def _open_pdf(self, path: Path) -> None:
        try:
            os.startfile(path)  # type: ignore[attr-defined]
        except OSError:
            log.exception("PDF ne može da se otvori")
            QMessageBox.information(
                self, "Štampa",
                f"PDF je napravljen, ali Windows ne zna čime da ga otvori:\n\n{path}\n\n"
                "Otvorite ga u internet pregledaču (Edge ili Chrome) – prevucite fajl u pregledač.")

    def _pdf_target(self, name: str) -> Path:
        folder = paths.root_dir() / "stampa"
        folder.mkdir(parents=True, exist_ok=True)
        return folder / f"{name}_{datetime.now():%Y-%m-%d_%H%M%S}.pdf"

    def print_spisak(self) -> None:
        d = StampaDialog(self, self.conn)
        if not d.exec():
            return
        ids, nova_strana = d.values()
        if not ids:
            QMessageBox.information(self, "Štampa", "Niste izabrali nijedno skladište.")
            return
        target = stampa.write_pdf(stampa.html_spisak(self.conn, ids, nova_strana),
                                  self._pdf_target("Spisak"), "Spisak stakala po skladištima")
        audit.write(self.conn, "STAMPA", opis=f"Spisak po skladištima ({len(ids)}) → {target.name}")
        self._open_pdf(target)

    def print_prikaz(self) -> None:
        rows = self.lager.model.rows
        if not rows:
            QMessageBox.information(self, "Štampa", "Trenutno nema ništa za štampu.")
            return
        naslov = "Stakla" + (f" – pretraga: {self.lager.search.text()}" if self.lager.search.text() else "")
        target = stampa.write_pdf(stampa.html_prikaz(rows, naslov), self._pdf_target("Prikaz"), naslov)
        audit.write(self.conn, "STAMPA", opis=f"Trenutni prikaz ({len(rows)}) → {target.name}")
        self._open_pdf(target)

    def refresh_status(self) -> None:
        last = backup.last_backup()
        self.statusBar().showMessage(
            f"Verzija {version.VERSION}   |   Baza v{db.current_version(self.conn)}   |   "
            f"Poslednji backup: {last.stem.removeprefix(backup.PREFIX) if last else 'nema'}"
        )

    # ---------- akcije ----------
    def check_database(self) -> None:
        st = db.status(self.conn)
        text = (
            f"Verzija programa:  {st.app_version}\n"
            f"Verzija baze:  {st.db_version}  (očekivana {st.expected_version})\n"
            f"Provera integriteta:  {'ispravna' if st.integrity == 'ok' else st.integrity}\n"
            f"Veličina baze:  {st.db_size_bytes / 1024:.0f} KB\n"
            f"Poslednji backup:  {st.last_backup or 'nema'}\n"
            f"Folder:  {paths.root_dir()}"
        )
        audit.write(self.conn, "PROVERA_BAZE", opis=f"v{st.db_version}, integritet={st.integrity}")
        if st.pending:
            names = ", ".join(f"{m.number:03d}_{m.name}" for m in st.pending)
            r = QMessageBox.question(
                self, "Provera baze",
                f"{text}\n\nBaza NIJE poslednja verzija. Nedostaje: {names}\n\nPrimeniti sada?",
            )
            if r == QMessageBox.StandardButton.Yes:
                backup.make_backup(self.conn, "pre_migracije")
                db.apply_migrations(self.conn)
                audit.write(self.conn, "MIGRACIJA", opis=f"Ručno primenjeno: {names}")
                QMessageBox.information(self, "Provera baze", "Baza je ažurirana.")
        elif st.integrity != "ok":
            QMessageBox.warning(
                self, "Provera baze",
                f"{text}\n\nBaza ima problem! Ne radite ništa dalje – napravite dijagnostiku "
                "sa kopijom baze i pošaljite je Milošu.",
            )
        else:
            QMessageBox.information(self, "Provera baze", f"{text}\n\nSve je u redu ✔")
        self.refresh_status()

    def backup_now(self) -> None:
        target = backup.make_backup(self.conn, "rucno")
        audit.write(self.conn, "BACKUP", opis=target.name)
        self.refresh_status()
        QMessageBox.information(self, "Backup", f"Backup je napravljen:\n{target}")

    def open_backup_folder(self) -> None:
        paths.backup_dir().mkdir(parents=True, exist_ok=True)
        os.startfile(paths.backup_dir())  # type: ignore[attr-defined]

    def make_diagnostics(self) -> None:
        r = QMessageBox.question(
            self, "Dijagnostika",
            "Da li da u dijagnostiku stavim i kopiju baze?\n\n"
            "(Preporučeno ako program pravi probleme sa podacima.)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            | QMessageBox.StandardButton.Cancel,
        )
        if r == QMessageBox.StandardButton.Cancel:
            return
        desktop = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation))
        target = diagnostics.create_zip(self.conn, desktop, r == QMessageBox.StandardButton.Yes)
        audit.write(self.conn, "DIJAGNOSTIKA", opis=target.name)
        QMessageBox.information(
            self, "Dijagnostika",
            f"Napravljen je fajl na desktopu:\n\n{target.name}\n\nPošaljite ga Milošu (Viber/mejl).",
        )

    def update_from_file(self) -> None:
        start = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation))
        file, _ = QFileDialog.getOpenFileName(
            self, "Izaberite paket za ažuriranje", str(start), "AutoStakla paket (*.zip)"
        )
        if not file:
            return
        try:
            info = update.validate_package(Path(file))
        except update.UpdateError as e:
            log.warning("Neispravan paket %s: %s", file, e)
            QMessageBox.warning(self, "Ažuriranje", str(e))
            return

        if info.comparison < 0:
            QMessageBox.warning(
                self, "Ažuriranje",
                f"Paket je STARIJA verzija ({info.version}) od trenutne ({version.VERSION}).\n"
                "Ažuriranje je prekinuto.",
            )
            return
        edition_note = ""
        if info.edition != version.EDITION:
            edition_note = f"\nIzdanje se menja: {version.EDITION} → {info.edition}\n"
        same = "\n(Ista verzija – program će biti ponovo instaliran.)\n" if info.comparison == 0 else ""
        r = QMessageBox.question(
            self, "Ažuriranje",
            f"Trenutna verzija: {version.VERSION}\nNova verzija: {info.version}\n{edition_note}{same}\n"
            "Program će napraviti backup, zatvoriti se i ponovo pokrenuti.\nNastaviti?",
        )
        if r != QMessageBox.StandardButton.Yes:
            return

        try:
            backup.make_backup(self.conn, f"pre_update_{info.version}")
            updater, new_app = update.prepare(info)
            self.conn.execute(
                "INSERT OR REPLACE INTO podesavanja (kljuc, vrednost) VALUES (?, ?)",
                (KEY_UPDATE_IN_PROGRESS, info.version),
            )
            audit.write(self.conn, "UPDATE", opis=f"Pokrenuto {version.VERSION} → {info.version}")
            update.launch_updater(updater, new_app)
        except Exception as e:
            log.exception("Priprema update-a nije uspela")
            self.conn.execute("DELETE FROM podesavanja WHERE kljuc = ?", (KEY_UPDATE_IN_PROGRESS,))
            QMessageBox.critical(self, "Ažuriranje", f"Ažuriranje nije uspelo:\n{e}")
            return
        self.closing_for_update = True
        self.close()

    def uputstvo(self) -> None:
        pdf = paths.docs_dir() / paths.UPUTSTVO_PDF
        if not pdf.exists():
            QMessageBox.information(self, "Uputstvo", "Uputstvo nije pronađeno uz program.")
            return
        self._open_pdf(pdf)

    def sta_je_novo(self) -> None:
        StaJeNovoDialog.prikazi(self)

    def about(self) -> None:
        QMessageBox.about(
            self, "O programu",
            f"<b>{version.APP_NAME}</b> {version.VERSION}<br>"
            "Evidencija lagera auto stakala<br><br>"
            f"Folder: {paths.root_dir()}",
        )
