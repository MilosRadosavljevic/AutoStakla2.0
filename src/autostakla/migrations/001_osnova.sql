-- 001: osnovne tabele aplikacije (nezavisne od lagera)
-- PRAVILO: sve mora moći da se pusti više puta (IF NOT EXISTS / INSERT OR IGNORE / WHERE NOT EXISTS)

-- Šta je korisnik radio
CREATE TABLE IF NOT EXISTS audit_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    vreme        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f','now','localtime')),
    akcija       TEXT    NOT NULL,   -- npr. START, KRAJ, BACKUP, UPDATE, ULAZ, IZLAZ, IZMENA, BRISANJE
    entitet      TEXT,               -- npr. staklo, kretanje
    entitet_id   INTEGER,
    opis         TEXT,
    staro_json   TEXT,
    novo_json    TEXT,
    app_verzija  TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_audit_log_vreme   ON audit_log (vreme);
CREATE INDEX IF NOT EXISTS ix_audit_log_entitet ON audit_log (entitet, entitet_id);

-- Podešavanja programa (ključ -> vrednost)
CREATE TABLE IF NOT EXISTS podesavanja (
    kljuc     TEXT PRIMARY KEY,
    vrednost  TEXT
);
