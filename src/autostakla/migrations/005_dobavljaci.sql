-- 005: Better – dobavljači, cenovnik i nabavka
-- PRAVILO: sve mora moći da se pusti više puta (IF NOT EXISTS / INSERT OR IGNORE / WHERE NOT EXISTS)

CREATE TABLE IF NOT EXISTS dobavljac (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    naziv      TEXT    NOT NULL COLLATE NOCASE UNIQUE,
    telefon    TEXT,
    email      TEXT,
    napomena   TEXT,
    aktivno    INTEGER NOT NULL DEFAULT 1 CHECK (aktivno IN (0, 1)),
    kreirano   TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    izmenjeno  TEXT
);

-- Nabavna cena stakla kod dobavljača, u celim dinarima BEZ PDV-a. Promena cene = novi red (istorija cena).
CREATE TABLE IF NOT EXISTS cenovnik (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    staklo_id     INTEGER NOT NULL REFERENCES staklo (id),
    dobavljac_id  INTEGER NOT NULL REFERENCES dobavljac (id),
    cena          INTEGER NOT NULL CHECK (cena >= 0),
    vazi_od       TEXT    NOT NULL DEFAULT (date('now','localtime')),
    napomena      TEXT,
    kreirano      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS ix_cenovnik_staklo ON cenovnik (staklo_id, dobavljac_id, vazi_od);

-- Nabavka = ulaz sa razlogom NABAVKA; nabavna cena po komadu, u celim dinarima BEZ PDV-a
CREATE TABLE IF NOT EXISTS nabavka (
    kretanje_id   INTEGER PRIMARY KEY REFERENCES kretanje (id),
    dobavljac_id  INTEGER REFERENCES dobavljac (id),
    nabavna_cena  INTEGER NOT NULL CHECK (nabavna_cena >= 0),
    dokument      TEXT,
    napomena      TEXT
);
CREATE INDEX IF NOT EXISTS ix_nabavka_dobavljac ON nabavka (dobavljac_id);
