"""Pravi update paket: manifest.json + app/... + (opciono) fajlovi za korisnika u korenu zip-a.

Upotreba: python tools/make_update_zip.py <dist_app_folder> <izlazni_zip> [dodatni_fajl ...]
Dodatni fajlovi (OBAVEZNO_PROCITAJ.txt, uputstvo) idu u koren – korisnik ih vidi kad otvori zip,
a program ih pri ažuriranju ignoriše (zamenjuje se samo app/).
"""
import json
import sys
import zipfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from autostakla import version  # noqa: E402


def main(dist_app: Path, out: Path, extra: list[Path]) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "app_id": version.APP_ID,
        "edition": version.EDITION,
        "version": version.VERSION,
        "napravljeno": datetime.now().isoformat(timespec="seconds"),
    }
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in extra:
            zf.write(f, f.name)
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        for f in sorted(dist_app.rglob("*")):
            if f.is_file():
                zf.write(f, "app/" + f.relative_to(dist_app).as_posix())
    print(out)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), [Path(p) for p in sys.argv[3:]])
