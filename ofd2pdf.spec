# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: build ``OFD转PDF工具.exe`` (standalone Windows GUI).

Why this spec exists
--------------------
The first packaged EXE was "incomplete": only the pure-Python modules made it
into the archive and every binary dependency (pymupdf's ``_mupdf.pyd`` +
``mupdfcpp64.dll``, Tk's tcl/tk runtime, PIL's ``_imaging``, …) was missing,
so ``import fitz`` and the GUI crashed at startup.

This spec fixes that by explicitly collecting pymupdf's dynamic libraries and
submodules. Build it with::

    py -3.13 -m PyInstaller ofd2pdf.spec --noconfirm

(use the 64-bit Python that has ``easyofd`` and ``pymupdf`` installed.)
"""

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
)

# pymupdf's C extension (`_mupdf.pyd`) + its `mupdfcpp64.dll` must ship with
# the binary, otherwise `import fitz` (used internally by easyofd) fails at
# runtime. `collect_dynamic_libs` grabs the DLL, and the .pyd is pulled in as
# an extension module via the submodule collection below.
hiddenimports = []
hiddenimports += collect_submodules("easyofd")
hiddenimports += collect_submodules("pymupdf")

datas = collect_data_files("pymupdf")
binaries = collect_dynamic_libs("pymupdf")

a = Analysis(
    ["ofd2pdf/gui.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "ruff", "tkinter.test"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="OFD转PDF工具",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # windowed GUI, no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
