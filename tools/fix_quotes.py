"""Zamenjuje „{x}" (ASCII zatvarajući navodnik prekida Python string) sa „{x}“ u zadatim fajlovima."""
import ast
import re
import sys
from pathlib import Path

PATTERN = re.compile("„(\\{[^}]*\\})\"")

for name in sys.argv[1:]:
    p = Path(name)
    text = p.read_text(encoding="utf-8")
    new, n = PATTERN.subn("„\\1“", text)
    p.write_text(new, encoding="utf-8")
    if p.suffix == ".py":
        ast.parse(new)
    print(f"{p.name}: {n} zamena, sintaksa ok")
