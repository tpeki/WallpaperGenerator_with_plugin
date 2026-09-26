# -*- mode: python ; coding: utf-8 -*-

"""
PyInstaller spec for WallpaperGenerator

This is a one-file build.

The source tree is expected to contain:

```
wallpaper.pyw
wallpaper.ico
wall_common.py
filedialog.py
winwall.py
plugins/
    __init__.py
    mod_*.py
    efx_*.py
    sub_sprites.py
    ...
samples/
    ...
```

plugins and samples are NOT included in the executable.
They are expected to exist next to the executable:

```
WallpaperGenerator.exe
plugins/
samples/
```

The application should use sys.executable as the base directory
when running as a frozen application.
"""

from pathlib import Path

PROJECT_DIR = Path(SPECPATH).resolve()
MAIN_SCRIPT = PROJECT_DIR / "wallpaper.pyw"

# plugins and samples are intentionally NOT included.

#

# They are external directories next to WallpaperGenerator.exe.

#

datas = []

# efx_impose.py is loaded dynamically and imports fontTools itself.

# Therefore PyInstaller cannot necessarily discover fontTools through

# normal static analysis of wallpaper.pyw.

hiddenimports = [
"fontTools",
"fontTools.ttLib",
]

a = Analysis(
[str(MAIN_SCRIPT)],
pathex=[str(PROJECT_DIR)],
binaries=[],
datas=datas,
hiddenimports=hiddenimports,
hookspath=[],
hooksconfig={},
runtime_hooks=[],
excludes=[],
noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
pyz,
a.scripts,
a.binaries,
a.datas,
[],
name="WallpaperGenerator",
debug=False,
bootloader_ignore_signals=False,
strip=False,
upx=False,
console=False,
icon=str(PROJECT_DIR / "wallpaper.ico"),
)
