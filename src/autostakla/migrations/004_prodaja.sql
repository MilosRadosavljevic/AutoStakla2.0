-- 004: Better – razlog kretanja, kupci i prodaja
-- PRAVILO: sve mora moći da se pusti više puta (IF NOT EXISTS / INSERT OR IGNORE / WHERE NOT EXISTS)
-- Tabela kretanje se ne menja: ovo su dodaci vezani 1:1 za kretanje.

-- Zašto je staklo izašlo ili ušlo (stara kretanja nemaju red = „nepoznato“)
CREATE TABLE IF NOT EXISTS kretanje_razlog (
    kretanje_id  INTEGER PRIMARY KEY REFERENCES kretanje (id),
    razlog       TEXT    NOT NULL
                 CHECK (razlog IN ('PRODATO', 'RAZBIJENO', 'POVRAT_DOBAVLJACU', 'ZAMENA_REKLAMACIJA',
                                   'NABAVKA', 'POVRAT_KUPCA', 'OSTALO'))
);

CREATE TABLE IF NOT EXISTS kupac (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ime        TEXT    NOT NULL,
    telefon    TEXT,
    napomena   TEXT,
    kreirano   TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    izmenjeno  TEXT
);
CREATE INDEX IF NOT EXISTS ix_kupac_ime ON kupac (ime);

-- Prodaja = izlaz sa razlogom PRODATO. Cena je po komadu, u celim dinarima, SA PDV-om (ono što kupac plaća).
CREATE TABLE IF NOT EXISTS prodaja (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    kretanje_id   INTEGER NOT NULL UNIQUE REFERENCES kretanje (id),
    kupac_id      INTEGER REFERENCES kupac (id),
    vozilo        TEXT,
    tablice       TEXT,
    cena          INTEGER NOT NULL CHECK (cena >= 0),
    sa_ugradnjom  INTEGER NOT NULL DEFAULT 0 CHECK (sa_ugradnjom IN (0, 1)),
    napomena      TEXT
);
CREATE INDEX IF NOT EXISTS ix_prodaja_kupac   ON prodaja (kupac_id);
CREATE INDEX IF NOT EXISTS ix_prodaja_tablice ON prodaja (tablice);
