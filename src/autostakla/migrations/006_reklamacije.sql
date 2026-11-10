-- 006: Better – reklamacije (vezane za prodaju)
-- PRAVILO: sve mora moći da se pusti više puta (IF NOT EXISTS / INSERT OR IGNORE / WHERE NOT EXISTS)
-- Promene statusa se beleže u audit_log (entitet = 'reklamacija').

CREATE TABLE IF NOT EXISTS reklamacija (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    prodaja_id     INTEGER NOT NULL REFERENCES prodaja (id),
    datum_prijave  TEXT    NOT NULL DEFAULT (date('now','localtime')),
    opis           TEXT    NOT NULL,
    status         TEXT    NOT NULL DEFAULT 'PRIJAVLJENA'
                   CHECK (status IN ('PRIJAVLJENA', 'KOD_DOBAVLJACA', 'ODOBRENA', 'ODBIJENA', 'RESENA')),
    ishod          TEXT    CHECK (ishod IN ('ZAMENA', 'POVRAT_NOVCA', 'POPRAVKA')),
    dobavljac_id   INTEGER REFERENCES dobavljac (id),
    trosak         INTEGER NOT NULL DEFAULT 0 CHECK (trosak >= 0),   -- šta je reklamacija koštala (dinari)
    napomena       TEXT,
    zatvoreno      TEXT,
    kreirano       TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    izmenjeno      TEXT
);
CREATE INDEX IF NOT EXISTS ix_reklamacija_prodaja ON reklamacija (prodaja_id);
CREATE INDEX IF NOT EXISTS ix_reklamacija_status  ON reklamacija (status);
