-- 002: lager – skladišta, police, stakla, pozicije i kretanja
-- PRAVILO: sve mora moći da se pusti više puta (IF NOT EXISTS / INSERT OR IGNORE / WHERE NOT EXISTS)

-- Skladište = jedna celina (stalak, „Dvorište", „Garaža"...)
CREATE TABLE IF NOT EXISTS skladiste (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    naziv      TEXT    NOT NULL COLLATE NOCASE UNIQUE,
    opis       TEXT,
    redosled   INTEGER NOT NULL DEFAULT 0,
    aktivno    INTEGER NOT NULL DEFAULT 1 CHECK (aktivno IN (0, 1)),
    kreirano   TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    izmenjeno  TEXT
);

-- Polica = deo skladišta (horizontalna linija na papiru, „I deo", „II deo"...)
CREATE TABLE IF NOT EXISTS polica (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    skladiste_id  INTEGER NOT NULL REFERENCES skladiste (id),
    naziv         TEXT    NOT NULL COLLATE NOCASE,
    opis          TEXT,
    redosled      INTEGER NOT NULL DEFAULT 0,
    aktivno       INTEGER NOT NULL DEFAULT 1 CHECK (aktivno IN (0, 1)),
    kreirano      TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    izmenjeno     TEXT,
    UNIQUE (skladiste_id, naziv)
);
CREATE INDEX IF NOT EXISTS ix_polica_skladiste ON polica (skladiste_id, redosled);

-- Staklo = vrsta stakla (šifarnik). Isto staklo može da stoji na više mesta.
CREATE TABLE IF NOT EXISTS staklo (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    naziv         TEXT    NOT NULL,                 -- kako ga on piše: „VW Golf 5 i 6 SENZOR"
    tip           TEXT    NOT NULL DEFAULT 'vetrobran'
                  CHECK (tip IN ('vetrobran', 'zadnje', 'bocno', 'ostalo')),
    senzor        INTEGER NOT NULL DEFAULT 0 CHECK (senzor IN (0, 1)),
    senzor_opis   TEXT,                             -- ROMB, KRUG, KRUŠKA, 2 SENZORA...
    kamera        INTEGER NOT NULL DEFAULT 0 CHECK (kamera IN (0, 1)),
    kamera_opis   TEXT,                             -- USKA, ŠIROKA...
    plocica       TEXT,                             -- pločica retrovizora: trougao, okrugla, niža, viša, bez...
    polovno       INTEGER NOT NULL DEFAULT 0 CHECK (polovno IN (0, 1)),
    napomena      TEXT,
    aktivno       INTEGER NOT NULL DEFAULT 1 CHECK (aktivno IN (0, 1)),
    kreirano      TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    izmenjeno     TEXT
);

-- Za koja vozila staklo odgovara (jedno staklo – više vozila: Ducato / Jumper / Boxer)
CREATE TABLE IF NOT EXISTS staklo_vozilo (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    staklo_id   INTEGER NOT NULL REFERENCES staklo (id) ON DELETE CASCADE,
    marka       TEXT    NOT NULL,
    model       TEXT,
    generacija  TEXT,
    godina_od   INTEGER,
    godina_do   INTEGER
);
CREATE INDEX IF NOT EXISTS ix_staklo_vozilo_staklo ON staklo_vozilo (staklo_id);

-- Lager stavka = određeno staklo na određenoj polici i poziciji
CREATE TABLE IF NOT EXISTS lager_stavka (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    staklo_id   INTEGER NOT NULL REFERENCES staklo (id),
    polica_id   INTEGER NOT NULL REFERENCES polica (id),
    pozicija    INTEGER,                            -- redni broj na papiru (fizički položaj)
    napomena    TEXT,
    kreirano    TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS ix_lager_stavka_staklo ON lager_stavka (staklo_id);
CREATE INDEX IF NOT EXISTS ix_lager_stavka_polica ON lager_stavka (polica_id, pozicija);

-- Kretanja – stanje je njihov zbir. Ništa se ne prepisuje, sve ostaje u istoriji.
CREATE TABLE IF NOT EXISTS kretanje (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    datum            TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now','localtime')),
    lager_stavka_id  INTEGER NOT NULL REFERENCES lager_stavka (id),
    kolicina         INTEGER NOT NULL CHECK (kolicina <> 0),     -- + ulaz, − izlaz
    vrsta            TEXT    NOT NULL
                     CHECK (vrsta IN ('POCETNO', 'ULAZ', 'IZLAZ', 'KOREKCIJA', 'PREMESTANJE')),
    napomena         TEXT,
    veza_id          INTEGER REFERENCES kretanje (id)            -- par kod premeštanja
);
CREATE INDEX IF NOT EXISTS ix_kretanje_stavka ON kretanje (lager_stavka_id);
CREATE INDEX IF NOT EXISTS ix_kretanje_datum  ON kretanje (datum);

-- Trenutno stanje po stavci
CREATE VIEW IF NOT EXISTS v_stanje AS
SELECT ls.id              AS lager_stavka_id,
       ls.staklo_id,
       ls.polica_id,
       p.skladiste_id,
       ls.pozicija,
       ls.napomena        AS stavka_napomena,
       COALESCE((SELECT SUM(k.kolicina) FROM kretanje k WHERE k.lager_stavka_id = ls.id), 0) AS kolicina
FROM lager_stavka ls
JOIN polica p ON p.id = ls.polica_id;
