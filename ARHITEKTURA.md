# AutoStakla – arhitektura

Desktop aplikacija za evidenciju lagera auto stakala. Jedan korisnik, jedan laptop, Windows.

Dva izdanja iz **istog koda i iste baze**:

| Izdanje | Za koga | Sadržaj |
|---|---|---|
| **AutoStakla** (osnovna) | drug, prva verzija | šifarnik stakala, ulaz/izlaz/korekcija **količina**, pretraga, PDF štampa |
| **AutoStaklaBetter** | nadogradnja | + cene i zarada, kupci (kome je ugrađeno), analitika, „šta naručiti", dobavljači |

Prelazak na Better = običan update: menja se `app\`, migracije dodaju tabele, podaci ostaju.

---

## 1. Tehnologije

| Deo | Izbor | Zašto |
|---|---|---|
| Jezik | Python 3.13 | brz razvoj |
| UI | PySide6 (Qt 6) | pravi Windows izgled, tabele, PDF bez dodatnih biblioteka |
| Baza | SQLite (jedan fajl) | bez instalacije i servisa, transakcije, backup = kopija fajla |
| Pakovanje | PyInstaller `--onedir` | Python i SQLite su unutra – kod korisnika se **ništa ne instalira** |
| Instalacija | Inno Setup 6 | jedan `Setup.exe`, bez admin prava, srpski jezik |
| PDF | Qt `QPdfWriter` | bez spoljnih alata; otvara se u podrazumevanom PDF čitaču |

## 2. Folder kod korisnika

```
C:\AutoStakla\
  app\                 ← program (AutoStakla.exe + _internal\). Update menja SAMO ovo.
  data\stakla.db       ← baza. Update i deinstalacija je NIKAD ne diraju.
  backup\              ← automatske kopije baze (čuva se poslednjih 30)
  logs\app.log         ← log grešaka (rotacija 5 × 1 MB)
  logs\updater.log     ← log update-a
  update\              ← privremeno, tokom update-a
```

Prečica na desktopu → `C:\AutoStakla\app\AutoStakla.exe`.

Koren se određuje ovako: ako je program spakovan → roditelj foldera u kom je exe;
u razvoju → `<projekat>\dev_root`; može se pregaziti promenljivom `AUTOSTAKLA_ROOT`.

## 3. Struktura projekta

```
D:\Milos\AutoStakla\
  src\autostakla\
    version.py          ← JEDINI izvor verzije i izdanja
    main.py             ← ulazna tačka
    core\
      paths.py          ← folderi (root, data, backup, logs)
      logging_setup.py  ← log fajl + hvatanje svih neuhvaćenih grešaka
      db.py             ← konekcija, migracije, provera baze
      audit.py          ← upis u audit_log
      backup.py         ← backup + rotacija
      diagnostics.py    ← zip za slanje Milošu
      update.py         ← provera update zipa i pokretanje Updater-a
    migrations\NNN_naziv.sql
    ui\                 ← prozori i dijalozi
  updater\updater.py    ← zaseban mali exe koji menja app\
  installer\AutoStakla.iss
  build.ps1             ← pravi exe, update zip i Setup.exe
  tests\
```

## 4. Baza i migracije

- Svaka izmena strukture je numerisan SQL fajl u `migrations\` (`001_osnova.sql`, `002_lager.sql`…).
- Tabela `schema_version` pamti šta je primenjeno.
- **Pri svakom pokretanju** program primeni sve što fali, ali tek **posle backup-a**. Sve u jednoj transakciji – ili sve, ili ništa.
- Ako je baza **novija** od programa (npr. vraćena stara verzija) – program odbija da radi, da ne pokvari podatke.
- Meni *Alati → Provera baze*: verzija programa i baze, `PRAGMA integrity_check`, poslednji backup, primena migracija koje fale.

**Lager se vodi kao kretanja** (ulaz / izlaz / korekcija sa datumom), a stanje je njihov zbir.
Tako osnovna verzija od prvog dana skuplja istoriju koju Better koristi za analitiku.

Model (migracija 002):

```
skladiste      jedna celina (1 Stalak, Dvorište, Garaža...)          CRUD + redosled
  polica       deo skladišta (horizontalna linija na papiru, I deo)   CRUD + redosled
staklo         šifarnik: naziv kako ga on piše + tip, senzor, kamera, pločica, polovno
  staklo_vozilo  za koja vozila odgovara (popunjava se postepeno – za Better)
lager_stavka   staklo + polica + pozicija (redni broj = fizički položaj)
kretanje       POCETNO / ULAZ / IZLAZ / KOREKCIJA / PREMESTANJE (+/− količina)
v_stanje       zbir kretanja po stavci
```

Brisanje skladišta/police: sa staklima – zabranjeno; prazno sa istorijom – samo se gasi (`aktivno=0`);
bez istorije – stvarno se briše.

Pretraga (`lager/search.py`): bez obzira na velika slova i kvačice, svaka reč upita mora biti početak
neke reči (`golf 5` ne nalazi `Golf 4 ... 05-`), sinonimi marki (`peugeot` = `pezo`, `renault` = `reno`).

**Početno stanje** (migracija 003) se generiše: `pocetno_stanje\spisak_sirovo.txt` (prekucan papir)
→ `tools\pocetno_stanje.py` → `003_pocetno_stanje.sql` + `Pocetno_stanje_za_proveru.xlsx`.
Dok nije isporučen, 003 se sme ponovo generisati; posle isporuke ispravke idu kroz program.

## 5. Logovanje

| Šta | Gde | Sadržaj |
|---|---|---|
| Šta je korisnik radio | tabela `audit_log` u bazi | vreme, akcija, entitet, id, opis, staro → novo (JSON), verzija programa |
| Greške | `logs\app.log` | traceback, verzija, vreme; hvata se i svaka neuhvaćena greška |
| Update | `logs\updater.log` | svaki korak zamene verzije |

Kad nešto pukne korisnik vidi kratku poruku, a detalji idu u log.
*Alati → Napravi dijagnostiku* pravi `AutoStakla_dijagnostika_<datum>.zip` na desktopu
(logovi + info o verzijama + po izboru kopija baze) – to se pošalje Milošu.

## 6. Backup

- Automatski pri zatvaranju programa, pre migracija i pre update-a.
- SQLite backup API (ispravna kopija i dok je baza otvorena).
- Čuva se poslednjih 30; ručno: *Alati → Napravi backup sada*.

## 7. Isporuka

**Prva instalacija** – `AutoStakla_Setup_<ver>.exe`:
1. pravi `C:\AutoStakla` i potfoldere, kopira program u `app\`;
2. prečica na desktopu i u Start meniju;
3. na kraju pokreće program, koji sam pravi bazu.

PDF čitač se **ne instalira** – PDF otvara podrazumevani program u Windows-u (Edge/Chrome).

Ne traži admin prava. Deinstalacija briše program, **ne briše** `data\` i `backup\`.

**Nove verzije** – `AutoStakla_update_<ver>.zip` (pošalje se Viberom/mejlom):
1. *Alati → Ažuriraj iz fajla* → izabere zip;
2. program proveri `manifest.json` (ime, izdanje, verzija), napravi backup, raspakuje u `update\`;
3. pokrene `Updater.exe` (iz novog paketa, kopiran van `app\`) i zatvori se;
4. Updater sačeka da se program zatvori, preimenuje `app\` → `app_old\`, ubaci novi `app\`, pokrene program, obriše `app_old\`.
   Ako bilo šta pukne – vraća `app_old\` nazad i javlja grešku.
5. Novi program pri pokretanju primeni migracije.

Program može da radi u samo jednoj instanci (zaključavanje u `C:\AutoStakla`).

## 8. Verzije

`MAJOR.MINOR.PATCH` u `src\autostakla\version.py`. Build skript odatle čita verziju
za exe, update zip i Setup.

## 8a. Isporuka korisniku

Pre build-a: podići `VERSION` i upisati izmene u **IZMENE.md** (bez toga build staje).
`build.ps1` pravi u `release\<ver>\`:

- `AutoStakla_<ver>_PRVA_INSTALACIJA.zip` – Setup + uputstvo (PDF) + prezentacija + `OBAVEZNO_PROCITAJ.txt`
- `AutoStakla_update_<ver>.zip` – za *Alati → Ažuriraj iz fajla* + uputstvo + `OBAVEZNO_PROCITAJ.txt`

Lokalno postoji samo jedna dokumentacija (`dokumentacija\`), prepisuje se pri svakom build-u.
Program nosi uputstvo i „Šta je novo“ (meni Pomoć; prikaže se samo posle ažuriranja).

## 9. Razvoj – kako se pravi nova verzija

```powershell
# pokretanje iz koda (podaci idu u dev_root\)
.\.venv\Scripts\python.exe src\autostakla\main.py

# testovi
.\.venv\Scripts\python.exe -m pytest -q

# nova verzija: 1) podigni VERSION u version.py  2) build
powershell -ExecutionPolicy Bypass -File build.ps1
```

Rezultat u `release\`:
- `AutoStakla_Setup_<ver>.exe` – prva instalacija (ili ponovna, podaci ostaju)
- `AutoStakla_update_<ver>.zip` – šalje se za *Alati → Ažuriraj iz fajla*

Izmena baze = novi fajl `src\autostakla\migrations\NNN_naziv.sql` (bez BEGIN/COMMIT – to radi program).
Postojeće migracije se **nikad ne menjaju** posle isporuke.

**Pravilo: svaki SQL mora moći da se pusti više puta bez greške i bez duplikata.**
- `CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`, `CREATE VIEW IF NOT EXISTS`, `CREATE TRIGGER IF NOT EXISTS`
- početni podaci: `INSERT OR IGNORE …` (kad postoji jedinstveni ključ) ili `INSERT … SELECT … WHERE NOT EXISTS (…)`
- `DROP … IF EXISTS`
- SQLite nema `ADD COLUMN IF NOT EXISTS` – nova kolona ide kroz novu tabelu (`CREATE TABLE IF NOT EXISTS x_new` → prepis → zamena) ili kroz Python korak u migraciji, uz proveru `PRAGMA table_info`.

Test `test_every_migration_can_run_twice` pušta svaku migraciju dvaput i pada ako pravilo nije ispoštovano.
