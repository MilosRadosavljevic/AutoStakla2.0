-- 007: Better – nefiskalni dokumenti (predračun, otpremnica). Fiskalni račun ovaj program NE izdaje.
-- PRAVILO: sve mora moći da se pusti više puta (IF NOT EXISTS / INSERT OR IGNORE / WHERE NOT EXISTS)

CREATE TABLE IF NOT EXISTS dokument (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    vrsta       TEXT    NOT NULL CHECK (vrsta IN ('PREDRACUN', 'OTPREMNICA')),
    godina      INTEGER NOT NULL,
    redni_broj  INTEGER NOT NULL,
    datum       TEXT    NOT NULL DEFAULT (date('now','localtime')),
    kupac_id    INTEGER REFERENCES kupac (id),
    prodaja_id  INTEGER REFERENCES prodaja (id),
    napomena    TEXT,
    kreirano    TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    UNIQUE (vrsta, godina, redni_broj)
);

-- Cena po komadu u celim dinarima SA PDV-om
CREATE TABLE IF NOT EXISTS dokument_stavka (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    dokument_id  INTEGER NOT NULL REFERENCES dokument (id) ON DELETE CASCADE,
    staklo_id    INTEGER REFERENCES staklo (id),
    naziv        TEXT    NOT NULL,
    kolicina     INTEGER NOT NULL CHECK (kolicina > 0),
    cena         INTEGER NOT NULL CHECK (cena >= 0)
);
CREATE INDEX IF NOT EXISTS ix_dokument_stavka ON dokument_stavka (dokument_id);
