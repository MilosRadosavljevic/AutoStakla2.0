# Third-party notices – AutoStakla 2.0

The AutoStakla source code is © 2026 Miloš Radosavljević, all rights reserved (see `LICENSE`).
The components below are **not** covered by that license; they remain under their own licenses.
This file and the `LICENSES` folder must be shipped together with the compiled program.

| Component | Version | License | In the compiled program |
|---|---|---|---|
| PySide6, shiboken6 (Qt for Python) | 6.12 | LGPL-3.0 | yes |
| openpyxl | 3.1 | MIT | yes |
| et_xmlfile | 2.0 | MIT | yes |
| Python | 3.13 | PSF License | yes (runtime) |
| PyInstaller bootloader | 6.22 | GPL-2.0+ with bootloader exception | yes |
| PyMuPDF, python-docx, python-pptx, Pillow | – | AGPL-3.0 (PyMuPDF), MIT, MIT, MIT-CMU | **no** – documentation tools only |
| pytest | – | MIT | **no** – tests only |

### Qt for Python (PySide6, shiboken6) 6.12 – LGPL-3.0
Copyright (C) The Qt Company Ltd. Used under the GNU Lesser General Public License v3.0
(`LICENSES/LGPL-3.0.txt`, which incorporates `LICENSES/GPL-3.0.txt`). Qt libraries are distributed as separate,
unmodified dynamic libraries (PyInstaller `--onedir`), so the user can replace them with a compatible version.
Source code: https://download.qt.io/official_releases/QtForPython/ and https://code.qt.io/cgit/pyside/pyside-setup.git/

### Python 3.13 – PSF License
Copyright (c) 2001 Python Software Foundation. All rights reserved. Full text: `LICENSES/Python-PSF.txt`.
Bundled as the runtime of the compiled program (PyInstaller).

### PyInstaller bootloader 6.22 – GPL-2.0-or-later with bootloader exception
The exception allows distributing programs built with PyInstaller under any license. https://pyinstaller.org

**Note:** PyMuPDF is AGPL-3.0. It must never be imported by the program itself (`src/`), only by the
documentation tools, otherwise the AGPL would apply to the whole program.
