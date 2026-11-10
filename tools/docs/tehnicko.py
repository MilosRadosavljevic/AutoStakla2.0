"""Tehničko uputstvo -> dokumentacija/AutoStakla_Tehnicko_uputstvo.docx (+ .pdf)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from docx_util import Doc, mark_update_fields, to_pdf  # noqa: E402

from autostakla import version  # noqa: E402

d = Doc("AutoStakla", "Tehničko uputstvo", version.VERSION)
d.toc(page_break=False)  # sadržaj je duži od strane – tekst nastavlja odmah ispod

# ================================================================ 1
d.h1("1. Namena i obim")
d.p("AutoStakla je desktop aplikacija za Windows za vođenje lagera auto stakala: jedan korisnik, jedan laptop, "
    "lokalna baza. Ovaj dokument opisuje arhitekturu, bazu, poslovna pravila, logovanje, instalaciju, ažuriranje, "
    "razvoj i održavanje – dovoljno da neko drugi preuzme program.")
d.table(["Stavka", "Vrednost"], [
    ["Verzija", version.VERSION],
    ["Izdanje", f"{version.EDITION} ({version.APP_NAME}); planirano i „better“ (AutoStaklaBetter)"],
    ["Korisnik", "jedan, bez prijave"],
    ["Platforma", "Windows 10/11, 64-bit"],
    ["Izvorni kod", "D:\\Milos\\AutoStakla"],
    ["Instalacija kod korisnika", "C:\\AutoStakla"],
], [5.0, 11.5])

d.h2("1.1 Dva izdanja iz istog koda")
d.table(["Izdanje", "Sadržaj"], [
    ["AutoStakla (osnovna)", "Skladišta/police (CRUD), šifarnik stakala, ulaz/izlaz/ispravka/premeštanje količina, "
                             "pozicije, pretraga i filteri, PDF štampa, tema, backup, update, dijagnostika."],
    ["AutoStaklaBetter (plan)", "Sve iz osnovne + cene i zarada, kupci (kome je ugrađeno), razlog izlaza, analitika "
                                "(najprodavanija stakla, vozila), „šta naručiti“, dobavljači."],
], [4.5, 12.0])
d.p("Izdanje se bira konstantom ", ("EDITION", "code"), " u ", ("src\\autostakla\\version.py", "code"),
    ". Prelazak na Better je običan update: menja se samo ", ("app\\", "code"), ", migracije dodaju tabele, podaci "
    "ostaju. Exe se uvek zove ", ("AutoStakla.exe", "code"), " da prečica ostane ista.")

# ================================================================ 2
d.h1("2. Arhitektura")
d.h2("2.1 Tehnologije")
d.table(["Deo", "Izbor", "Razlog"], [
    ["Jezik", "Python 3.13", "brz razvoj, dobre biblioteke"],
    ["UI", "PySide6 (Qt 6.12)", "pravi Windows izgled, tabele, PDF bez dodatnih alata, svetla/tamna tema"],
    ["Baza", "SQLite (jedan fajl)", "bez instalacije i servisa; transakcije; backup = kopija fajla"],
    ["Pakovanje", "PyInstaller --onedir", "Python i SQLite su unutra – kod korisnika se ništa ne instalira"],
    ["Instalacija", "Inno Setup 6", "jedan Setup.exe, bez admin prava, poruke na srpskom"],
    ["PDF", "Qt QPdfWriter + QTextDocument", "HTML → PDF, otvara podrazumevani pregledač"],
    ["Testovi", "pytest", "jezgro, lager, update, UI (offscreen)"],
], [2.6, 4.4, 9.5])

d.h2("2.2 Folder kod korisnika")
d.code(r"""
C:\AutoStakla\
  app\                 program (AutoStakla.exe, Updater.exe). Update menja SAMO ovo.
  data\stakla.db       baza. Update i deinstalacija je NIKAD ne diraju.
  backup\              automatske kopije baze (poslednjih 30)
  logs\app.log         log grešaka (rotacija 5 x 1 MB)
  logs\updater.log     log ažuriranja
  stampa\              napravljeni PDF-ovi
  update\              privremeno, samo tokom ažuriranja
  autostakla.lock      zaključavanje – program radi u jednoj instanci
""")
d.p("Koren se određuje u ", ("core\\paths.py", "code"), ": spakovan program → roditelj foldera u kom je exe; "
    "razvoj → ", ("<projekat>\\dev_root", "code"), "; može se pregaziti promenljivom ",
    ("AUTOSTAKLA_ROOT", "code"), " (koriste je testovi i alati).")

d.h2("2.3 Struktura projekta")
d.code(r"""
D:\Milos\AutoStakla\
  src\autostakla\
    version.py            JEDINI izvor verzije i izdanja
    main.py               ulazna tačka: log, zaključavanje, baza, migracije, tema, prozor
    core\
      paths.py            folderi
      logging_setup.py    app.log + hvatanje neuhvaćenih grešaka
      db.py               konekcija, migracije, provera baze
      audit.py            upis u audit_log
      backup.py           backup + rotacija
      diagnostics.py      zip za podršku
      update.py           provera paketa, priprema, pokretanje Updater-a
      settings.py         tabela podesavanja (ključ -> vrednost)
    lager\
      repo.py             sva poslovna logika lagera (transakcije + audit)
      search.py           normalizacija i pretraga
      stampa.py           HTML -> PDF
    ui\                   prozori i dijalozi (main_window, lager_view, kretanje_dialogs,
                          staklo_dialog, skladista_dialog, tema, common)
    migrations\NNN_*.sql  izmene baze
    resources\icon.ico
  updater\updater.py      Updater.exe (samo standardna biblioteka)
  installer\AutoStakla.iss
  pocetno_stanje\         prekucan papir + Excel za proveru
  tools\                  pomoćni alati (ikonica, update zip, početno stanje, dokumentacija)
  tests\                  pytest
  build.ps1               build: testovi -> exe -> update zip -> Setup.exe
  ARHITEKTURA.md          kratak pregled
  dokumentacija\          ovi dokumenti + slike
""")

d.h2("2.4 Tok pokretanja (main.py)")
d.steps([
    "QApplication, ikonica; pravljenje foldera data/backup/logs.",
    "Log (app.log) i globalni hvatač grešaka (sys.excepthook, threading.excepthook) sa porukom korisniku.",
    "Mutex „AutoStaklaMutex“ (da Setup ne radi dok je program otvoren) i QLockFile (jedna instanca).",
    "Čišćenje ostataka prethodnog update-a (update\\, app_old\\).",
    "Otvaranje baze; ako ima migracija koje fale: backup „pre_migracije“, pa primena. Baza novija od programa → odbija rad.",
    "audit START, učitavanje sačuvane teme, glavni prozor, poruka o uspešnom update-u (ako je bio).",
    "Pri zatvaranju: backup „zatvaranje“ (osim kad se zatvara zbog update-a), audit KRAJ.",
])

# ================================================================ 3
d.h1("3. Baza podataka")
d.h2("3.1 Migracije")
d.bullets([
    ["Svaka izmena strukture ili početnih podataka je fajl ", ("migrations\\NNN_naziv.sql", "code"), "."],
    ["Tabela ", ("schema_version", "code"), " pamti primenjene migracije (broj, naziv, vreme, verzija programa)."],
    "Pri startu se primenjuju sve koje fale, svaka u svojoj transakciji (BEGIN … COMMIT); greška → ROLLBACK.",
    "Pre primene se pravi backup. Ako je baza na višoj verziji nego što program poznaje – program ne radi.",
    "Isporučene migracije se nikad ne menjaju – izmena = nova migracija.",
])
d.box("PRAVILO:", ["Svaki SQL mora moći da se pusti više puta bez greške i bez duplikata: ",
                   ("CREATE … IF NOT EXISTS", "code"), ", ", ("INSERT OR IGNORE", "code"), ", ",
                   ("INSERT … SELECT … WHERE NOT EXISTS", "code"), ", ", ("DROP … IF EXISTS", "code"),
                   ". SQLite nema ADD COLUMN IF NOT EXISTS – nova tabela + prepis ili provera PRAGMA table_info. "
                   "Test test_every_migration_can_run_twice to proverava za svaku migraciju."], color="FFF2CC")
d.table(["Migracija", "Sadržaj"], [
    ["001_osnova", "audit_log, podesavanja"],
    ["002_lager", "skladiste, polica, staklo, staklo_vozilo, lager_stavka, kretanje, view v_stanje"],
    ["003_pocetno_stanje", "GENERISANO alatom tools\\pocetno_stanje.py: 11 skladišta, police, 279 stakala, "
                           "329 mesta, 390 kom (kretanje POCETNO)"],
], [4.0, 12.5], code_cols=(0,))

d.h2("3.2 Tabele")
tabele = {
    "skladiste – skladište (stalak, „Dvorište“…)": [
        ["id", "INTEGER PK", ""], ["naziv", "TEXT NOT NULL UNIQUE NOCASE", "obavezan, jedinstven"],
        ["opis", "TEXT", ""], ["redosled", "INTEGER", "prikaz i štampa"],
        ["aktivno", "INTEGER 0/1", "0 = ugašeno (ima istoriju)"], ["kreirano / izmenjeno", "TEXT", "datum"]],
    "polica – deo skladišta": [
        ["id", "INTEGER PK", ""], ["skladiste_id", "FK skladiste", ""],
        ["naziv", "TEXT NOT NULL NOCASE", "UNIQUE(skladiste_id, naziv)"], ["opis, redosled, aktivno", "", "kao skladište"]],
    "staklo – šifarnik stakala": [
        ["id", "INTEGER PK", ""], ["naziv", "TEXT NOT NULL", "kako ga korisnik piše"],
        ["tip", "TEXT", "vetrobran | zadnje | bocno | ostalo"], ["senzor, senzor_opis", "0/1, TEXT", "romb, krug…"],
        ["kamera, kamera_opis", "0/1, TEXT", ""], ["plocica", "TEXT", "trougao, okrugla, niža, viša, bez…"],
        ["polovno", "0/1", ""], ["napomena, aktivno, kreirano, izmenjeno", "", ""]],
    "staklo_vozilo – za koja vozila odgovara (za Better)": [
        ["staklo_id", "FK staklo ON DELETE CASCADE", ""], ["marka, model, generacija", "TEXT", ""],
        ["godina_od, godina_do", "INTEGER", ""]],
    "lager_stavka – staklo na mestu": [
        ["id", "INTEGER PK", ""], ["staklo_id", "FK staklo", ""], ["polica_id", "FK polica", ""],
        ["pozicija", "INTEGER", "redni broj u skladištu; NULL = mesto ugašeno"], ["napomena", "TEXT", "napomena mesta"]],
    "kretanje – sve promene količina": [
        ["id", "INTEGER PK", ""], ["datum", "TEXT", "yyyy-mm-dd hh:mm:ss lokalno"],
        ["lager_stavka_id", "FK", ""], ["kolicina", "INTEGER ≠ 0", "+ ulaz, − izlaz"],
        ["vrsta", "TEXT", "POCETNO | ULAZ | IZLAZ | KOREKCIJA | PREMESTANJE"], ["napomena", "TEXT", ""],
        ["veza_id", "FK kretanje", "par kod premeštanja"]],
    "audit_log – šta je korisnik radio": [
        ["vreme", "TEXT", "sa milisekundama"], ["akcija", "TEXT", "vidi 5.1"], ["entitet, entitet_id", "", ""],
        ["opis", "TEXT", ""], ["staro_json, novo_json", "TEXT", "stanje pre/posle"], ["app_verzija", "TEXT", ""]],
    "podesavanja / schema_version": [
        ["podesavanja.kljuc, vrednost", "TEXT", "tema; update_u_toku"],
        ["schema_version.verzija, naziv, primenjeno, app_verzija", "", "primenjene migracije"]],
}
for naslov, rows in tabele.items():
    d.h3(naslov)
    d.table(["Kolona", "Tip", "Napomena"], rows, [5.5, 5.0, 6.0], size=9, code_cols=(0,))
d.p(("v_stanje", "code"), " (view): za svaku lager_stavka – staklo, polica, skladište, pozicija, napomena i ",
    ("kolicina = SUM(kretanje.kolicina)", "code"), ". Stanje se nikad ne upisuje direktno – samo kroz kretanja.")

d.h2("3.3 Korisni upiti")
d.code("""
-- stanje po skladištima
SELECT sk.naziv, COUNT(*) mesta, SUM(v.kolicina) kom
FROM v_stanje v JOIN skladiste sk ON sk.id = v.skladiste_id
WHERE v.kolicina > 0 GROUP BY sk.id ORDER BY sk.redosled;

-- istorija jednog stakla
SELECT k.datum, k.vrsta, k.kolicina, k.napomena, sk.naziv, p.naziv, ls.pozicija
FROM kretanje k JOIN lager_stavka ls ON ls.id = k.lager_stavka_id
JOIN staklo s ON s.id = ls.staklo_id JOIN polica p ON p.id = ls.polica_id
JOIN skladiste sk ON sk.id = p.skladiste_id
WHERE s.naziv LIKE '%Golf 5%' ORDER BY k.id;

-- poslednje akcije korisnika
SELECT vreme, akcija, opis FROM audit_log ORDER BY id DESC LIMIT 50;
""")
d.p("Bazu je najbezbednije čitati iz kopije (backup ili dijagnostika), npr. alatom DB Browser for SQLite.")

# ================================================================ 4
d.h1("4. Poslovna pravila (lager\\repo.py)")
d.p("Sve funkcije koje menjaju podatke rade u jednoj transakciji zajedno sa upisom u audit_log; greška vraća sve. "
    "Greške namenjene korisniku su ", ("LagerError", "code"), " – UI ih prikazuje kao poruku, bez gašenja programa.")
d.h2("4.1 Skladišta i police")
d.bullets([
    "Naziv obavezan; jedinstven (bez obzira na velika slova); polica jedinstvena u okviru skladišta.",
    "Novo skladište automatski dobija „Polica 1“.",
    "Brisanje: ima stakala → zabranjeno; prazno ali ima istoriju → aktivno = 0 (i njegove police); bez istorije → DELETE.",
    "Redosled: pomeranje gore/dole uz prenumerisanje 1..n.",
])
d.h2("4.2 Pozicije")
d.bullets([
    "Pozicija je redni broj kroz CELO skladište, preko svih polica (po redosledu polica).",
    ["Ulaz/premeštanje: ", ("svaki komad dobija svoju stavku i svoj broj", "b"),
     "; sve stavke skladišta sa pozicijom ≥ P pomeraju se za broj komada."],
    "Dozvoljen opseg za policu: od prvog broja na polici do (poslednji + 1); prazna polica → posle poslednjeg broja na policama iznad. Van opsega se ograničava.",
    "Kad stavka ostane na 0 (izlaz, ispravka na 0, premeštanje svega): pozicija = NULL, a sve ispod se penju za 1 – osim ako isti broj deli još neka stavka (redovi sa papira tipa „2 bez + 1 senzor“).",
    "Ispravka sa 0 na više: stavka dobija broj na kraju svoje police.",
    "Izmena mesta (isto skladište): oslobađanje stare pozicije pa ubacivanje na novu; za drugo skladište → Premesti.",
    "Početno stanje sa papira: stavke mogu imati više komada na jednom broju (npr. „3x“).",
])
d.h2("4.3 Kretanja")
d.table(["Radnja", "Funkcija", "Pravilo"], [
    ["Ulaz", "ulaz()", "količina > 0; nove stavke po komadu; vrsta ULAZ"],
    ["Izlaz", "izlaz()", "ne više od stanja; IZLAZ sa −količina"],
    ["Ispravka", "korekcija()", "nova količina ≥ 0, različita od trenutne; KOREKCIJA sa razlikom"],
    ["Premeštanje", "premesti()", "−n sa izvora, +1 po komadu na odredištu; oba PREMESTANJE, povezana veza_id"],
    ["Pozicija/napomena", "izmeni_mesto()", "samo isto skladište; audit IZMENA staro/novo"],
], [3.2, 3.3, 10.0], code_cols=(1,))
d.h2("4.4 Pretraga (lager\\search.py)")
d.bullets([
    "Normalizacija: mala slova, bez kvačica (š→s, đ→dj…), podela na reči po svemu što nije slovo/broj.",
    "Sinonimi (ALIASES): peugeot→pezo, renault→reno, volkswagen→vw, touaran→touran, senzorom→senzor…",
    "Svaka reč upita mora biti POČETAK neke reči teksta (golf 5 ≠ „Golf 4 … 05-“).",
    "Tekst stavke: naziv, napomene, opisi senzora/kamere, pločica, vozila, skladište, polica + reči senzor/kamera/polovno.",
    "Filteri (skladište, polica, tip, senzor, kamera, polovno, samo na stanju) idu u SQL; tekst se filtrira u Python-u.",
])
d.h2("4.5 Štampa (lager\\stampa.py)")
d.p("HTML → QTextDocument → QPdfWriter (A4, 300 dpi, margine 15/12 mm). Spisak po skladištima: naslov skladišta, "
    "police odvojene linijom, „Nx“ podebljano, opciono svako skladište na novoj strani. PDF se snima u ",
    ("C:\\AutoStakla\\stampa", "code"), " i otvara preko os.startfile (podrazumevani PDF program / pregledač).")
d.h2("4.6 Tema")
d.p("Meni Prikaz → Svetla/Tamna. Primenjuje se odmah (QStyleHints.setColorScheme) i pamti u podesavanja.tema. "
    "Bez sačuvane vrednosti program prati Windows.")

# ================================================================ 5
d.h1("5. Logovanje i podrška")
d.h2("5.1 audit_log – šta je korisnik radio")
d.table(["Akcija", "Kada"], [
    ["START / KRAJ", "pokretanje i zatvaranje programa"],
    ["MIGRACIJA", "primenjene migracije (automatski ili iz Provere baze)"],
    ["DODATO / IZMENA / BRISANJE", "skladište, polica, staklo, lager_stavka (staro/novo u JSON-u)"],
    ["ULAZ / IZLAZ / KOREKCIJA / PREMESTANJE", "svako kretanje: količina, staklo, mesto, napomena"],
    ["BACKUP, STAMPA, DIJAGNOSTIKA, PROVERA_BAZE", "ručne radnje iz menija"],
    ["UPDATE", "pokrenut i završen update (uspeh ili neuspeh)"],
    ["PODESAVANJE", "promena teme"],
], [6.5, 10.0], code_cols=(0,))
d.p("Greška pri upisu u audit se loguje, ali ne ruši radnju korisnika.")
d.h2("5.2 Log fajlovi")
d.bullets([
    [("logs\\app.log", "code"), " – start (verzija, Python, Windows), migracije, backup, update, upozorenja i svaka "
                                "neuhvaćena greška sa traceback-om. Rotacija 5 × 1 MB."],
    [("logs\\updater.log", "code"), " – svaki korak zamene verzije."],
])
d.h2("5.3 Dijagnostika")
d.p("Alati → Napravi dijagnostiku… pravi na desktopu ", ("AutoStakla_dijagnostika_<datum>.zip", "code"), ":")
d.bullets(["info.txt – verzije, Windows, folder, status baze, integritet, poslednji backup, poslednjih 200 akcija;",
           "logs\\*.log*;", "opciono data\\stakla.db (kopija preko SQLite backup API-ja)."])
d.h2("5.4 Backup")
d.p("SQLite backup API (ispravna kopija i dok je baza otvorena). Kada: pri zatvaranju, pre migracija, pre update-a, "
    "ručno. Ime ", ("stakla_<yyyy-mm-dd_hhmmss>_<razlog>.db", "code"), ", čuva se poslednjih 30.")
d.box("Vraćanje iz backup-a (ručno):", ["zatvoriti program → preimenovati data\\stakla.db (npr. stakla_lose.db) → "
                                        "kopirati izabrani backup u data\\stakla.db → pokrenuti program."])

# ================================================================ 6
d.h1("6. Instalacija")
d.p(("installer\\AutoStakla.iss", "code"), " (Inno Setup 6), pravi ga build.ps1:")
d.bullets([
    "PrivilegesRequired=lowest – bez admin prava; DefaultDirName=C:\\AutoStakla, izbor foldera isključen.",
    "Kopira build\\dist\\AutoStakla → {app}\\app; pravi data, backup, logs (uninsneveruninstall).",
    "Pre kopiranja briše stari app\\, app_old\\, update\\ (ponovna instalacija – podaci ostaju).",
    "Prečica na desktopu i u Start meniju; na kraju opcija „Pokreni AutoStakla“.",
    "AppMutex=AutoStaklaMutex – ne instalira dok program radi.",
    "Poruke čarobnjaka prevedene u [Messages] (Inno nema zvaničan srpski).",
    "PDF čitač se NE instalira – PDF otvara Windows (Edge/Chrome).",
    "Deinstalacija briše program i prečice; data\\ i backup\\ ostaju.",
])
d.p("Tiha instalacija (za testiranje): ", ("AutoStakla_Setup_x.y.z.exe /VERYSILENT /SUPPRESSMSGBOXES /DIR=\"C:\\Test\"", "code"),
    ". Nepotpisan exe: Windows SmartScreen pri prvom pokretanju traži More info → Run anyway.")

# ================================================================ 7
d.h1("7. Ažuriranje (update)")
d.h2("7.1 Paket")
d.code("""
AutoStakla_update_x.y.z.zip
  OBAVEZNO_PROCITAJ.txt                 za korisnika (program ga ignoriše)
  AutoStakla_Korisnicko_uputstvo.pdf    za korisnika (program ga ignoriše)
  manifest.json      {"app_id": "AutoStakla", "edition": "osnovna", "version": "x.y.z", "napravljeno": "..."}
  app/AutoStakla.exe
  app/Updater.exe
  app/_internal/...   (uključujući docs/ = uputstvo + OBAVEZNO_PROCITAJ za meni Pomoć)
""")
d.p("Isti zip je i isporuka i paket za ažuriranje: korisnik ga otvori da pročita txt/PDF, pa ga izabere u programu. "
    "Iz zip-a se raspakuje sve, ali se premešta samo app/.")
d.h2("7.2 Tok")
d.steps([
    "Alati → Ažuriraj iz fajla… → validate_package: zip ispravan, nema „..“/apsolutnih putanja, manifest, app_id, "
    "oba exe-a, testzip. Starija verzija se odbija; ista – ponovna instalacija; drugo izdanje – upozorenje.",
    "Backup „pre_update_x.y.z“; raspakivanje u update\\staging; Updater.exe se kopira u update\\ (van app\\).",
    "U podesavanja se upisuje update_u_toku = nova verzija; audit UPDATE; pokreće se Updater sa --root --staging --pid --exe; program se zatvara.",
    "Updater čeka da se proces završi (do 60 s), preimenuje app → app_old, premešta staging → app (ponavlja do 15 puta zbog zaključanih fajlova).",
    "Uspeh: briše app_old, pokreće novi exe. Neuspeh: vraća app_old → app, poruka korisniku, pokreće staru verziju sa --update-failed.",
    "Novi program pri startu: čisti update\\ i app_old\\, primenjuje migracije, upisuje audit UPDATE i javlja uspeh.",
])

# ================================================================ 8
d.h1("8. Razvoj")
d.h2("8.1 Okruženje")
d.bullets([
    "Python 3.13; virtuelno okruženje D:\\Milos\\AutoStakla\\.venv (PySide6, pyinstaller, pytest, pillow, openpyxl, "
    "pymupdf, python-docx, python-pptx, pywin32).",
    "Inno Setup 6 (winget install JRSoftware.InnoSetup) – ISCC.exe u %LOCALAPPDATA%\\Programs\\Inno Setup 6.",
    "Word i PowerPoint – samo za PDF verzije dokumentacije.",
])
d.h2("8.2 Komande")
d.code(r"""
# pokretanje iz koda (podaci u dev_root\)
.\.venv\Scripts\python.exe src\autostakla\main.py

# testovi
.\.venv\Scripts\python.exe -m pytest -q

# build (testovi -> exe -> update zip -> Setup)
powershell -ExecutionPolicy Bypass -File build.ps1
#   rezultat: release\AutoStakla_Setup_<ver>.exe, release\AutoStakla_update_<ver>.zip

# početno stanje (posle izmene pocetno_stanje\spisak_sirovo.txt)
.\.venv\Scripts\python.exe tools\pocetno_stanje.py

# dokumentacija (snimci ekrana, uputstva, prezentacija)
.\.venv\Scripts\python.exe tools\docs\snimci.py
.\.venv\Scripts\python.exe tools\docs\korisnicko.py
.\.venv\Scripts\python.exe tools\docs\tehnicko.py
.\.venv\Scripts\python.exe tools\docs\prezentacija.py
""")
d.h2("8.3 Nova verzija – postupak")
d.steps([
    "Izmene u kodu + testovi (pytest mora da prođe).",
    "Ako se menja baza: nova migracija NNN_naziv.sql po pravilu IF NOT EXISTS.",
    "Podići VERSION u version.py (MAJOR.MINOR.PATCH).",
    ["Upisati izmene u ", ("IZMENE.md", "code"), " (odeljak „## x.y.z (datum)“ sa Dodato / Izmenjeno / "
     "Ispravljeno / Uklonjeno) – bez toga build i test test_izmene_postoje_za_trenutnu_verziju padaju."],
    "Ako se menja izgled ili rad programa: dopuniti tools\\docs\\korisnicko.py (i prezentacija.py).",
    "build.ps1 – sam pravi snimke, dokumentaciju, OBAVEZNO_PROCITAJ.txt i pakete.",
    "Probati Setup tiho u test folder i update zip nad postojećom instalacijom.",
    "Korisniku poslati update zip (Viber/link) – u njemu su i novo uputstvo i OBAVEZNO_PROCITAJ.txt.",
])
d.h2("8.4 Isporuka – šta pravi build.ps1")
d.table(["Fajl (release\\<ver>\\)", "Za šta"], [
    ["AutoStakla_<ver>_PRVA_INSTALACIJA.zip", "nova instalacija: Setup, uputstvo (PDF), prezentacija (pptx+pdf), "
                                              "OBAVEZNO_PROCITAJ.txt (kako instalirati + šta je novo)"],
    ["AutoStakla_update_<ver>.zip", "ažuriranje: program + uputstvo + OBAVEZNO_PROCITAJ.txt (kako primeniti + šta je novo)"],
    ["AutoStakla_Setup_<ver>.exe", "sam Setup, za probu"],
], [6.5, 10.0], code_cols=(0,))
d.p("Lokalno postoji JEDNA dokumentacija (dokumentacija\\) koja se pri svakom build-u prepiše. Paketi po verzijama "
    "ostaju u release\\<ver>\\ – tako se uvek zna šta je korisnik dobio. Program nosi svoje uputstvo i "
    "OBAVEZNO_PROCITAJ u _internal\\docs (meni Pomoć; „Šta je novo“ se prikaže sam posle ažuriranja).")
d.h2("8.5 Testovi")
d.table(["Fajl", "Pokriva"], [
    ["test_core.py", "migracije (sveže, dvaput, rollback, novija baza), audit, backup i rotacija, status, "
                     "dijagnostika, update paketi (ispravni/neispravni, zip-slip), početno stanje"],
    ["test_lager.py", "CRUD skladišta/polica, pozicije (ubacivanje, pomeranje, opseg, oslobađanje, deljen broj), "
                      "izmena mesta, premeštanje, kretanja, transakcije, pretraga, validacija"],
    ["test_updater.py", "zamena app\\, vraćanje stare verzije pri grešci, podaci netaknuti"],
    ["test_ui_smoke.py", "svi prozori offscreen, PDF, tema se pamti"],
    ["test_isporuka.py", "IZMENE.md za trenutnu verziju, OBAVEZNO_PROCITAJ (BOM, CRLF), update zip sa dokumentima, "
                         "„Šta je novo“"],
], [3.8, 12.7], code_cols=(0,))
d.p("Fixture ", ("conn", "code"), " daje bazu bez početnog stanja, ", ("conn_full", "code"),
    " sa svim migracijama. Svaki test radi u svom privremenom korenu (AUTOSTAKLA_ROOT).")
d.h2("8.6 Početno stanje")
d.p(("pocetno_stanje\\spisak_sirovo.txt", "code"), " je prekucan papir: ", ("= Skladište | opis", "code"), ", ",
    ("- Polica | opis", "code"), ", ", ("12. tekst 2x // napomena ## komentar", "code"), "; ", ("2a.", "code"),
    " = ubačeno posle 2. Alat izvlači senzor/kameru/pločicu/polovno/tip iz teksta, prenumeriše brojeve neprekidno "
    "po skladištu i pravi 003_pocetno_stanje.sql i Excel za proveru (žuto = tumačenje rukom pisanog). "
    "Kad je 003 jednom isporučen korisniku, više se ne menja.")

# ================================================================ 9
d.h1("9. Rešavanje problema")
d.table(["Simptom", "Uzrok", "Rešenje"], [
    ["„Program je već pokrenut“", "otvorena instanca ili ostao lock", "zatvoriti program; QLockFile sam čisti zastareo lock"],
    ["„Baza je otvarana novijom verzijom“", "vraćena starija verzija programa", "instalirati najnoviju verziju"],
    ["Provera baze: integritet ≠ ok", "oštećen fajl (nestanak struje, disk)", "dijagnostika sa bazom; vratiti poslednji ispravan backup"],
    ["Update nije uspeo", "zaključani fajlovi, antivirus", "logs\\updater.log; stara verzija je vraćena; ponoviti"],
    ["PDF se ne otvara", "nema programa za PDF", "otvoriti iz C:\\AutoStakla\\stampa u pregledaču"],
    ["SmartScreen upozorenje", "nepotpisan exe", "More info → Run anyway (jednom)"],
    ["Antivirus blokira exe", "lažna detekcija PyInstaller-a", "izuzetak za C:\\AutoStakla ili ponovni build"],
    ["Greška u radu", "bag", "Napravi dijagnostiku → app.log (traceback) + audit_log"],
], [4.5, 5.0, 7.0], size=9)

# ================================================================ 10
d.h1("10. Istorija verzija")
d.table(["Verzija", "Izmene"], [
    ["0.1.0", "Jezgro: baza i migracije, log, audit, backup, dijagnostika, update + Updater, Setup."],
    ["0.2.0", "Lager: skladišta/police CRUD, stakla, ulaz/izlaz/ispravka/premeštanje, pretraga i filteri, "
              "PDF štampa, početno stanje sa papira."],
    ["0.3.0", "Pozicije: ubacivanje sa pomeranjem (svaki komad svoj broj), izmena pozicije i napomene, šire kolone; "
              "Adobe Reader izbačen iz instalacije."],
    ["0.4.0", "Svetla/tamna tema koja se pamti; dokumentacija."],
    ["1.0.0", "Prva isporuka: meni Pomoć (uputstvo, Šta je novo), OBAVEZNO_PROCITAJ.txt iz IZMENE.md, "
              "paketi za prvu instalaciju i ažuriranje sa dokumentacijom."],
], [2.5, 14.0])
d.h2("10.1 Odloženo / plan")
d.bullets(["Razlog izlaza (prodato, razbijeno, vraćeno) – dogovoreno za kasnije.",
           "Popunjavanje staklo_vozilo za postojeća stakla (za analitiku u Better-u).",
           "AutoStaklaBetter: cene, zarada, kupci, analitika, naručivanje."])

path = d.save("AutoStakla_Tehnicko_uputstvo")
print(path)
print(to_pdf(path))
mark_update_fields(path)
