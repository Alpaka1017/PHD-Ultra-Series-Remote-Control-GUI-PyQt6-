# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_submodules


block_cipher = None


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

datas = collect_data_files('.')
datas += collect_submodules('resources_rc')

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='main',
    debug=False,
	datas=datas,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               [('C:\\Users\\Xueyong Lu\\Desktop\\Archive\\DA\\SHK_HZDR\\Projects\\PHD Ultra_remote control_QT Designer\\font', 'C:\\Users\\Xueyong Lu\\Desktop\\Archive\\DA\\SHK_HZDR\\Projects\\Release')],
			   [('C:\\Users\\Xueyong Lu\\Desktop\\Archive\\DA\\SHK_HZDR\\Projects\\PHD Ultra_remote control_QT Designer\\image', 'C:\\Users\\Xueyong Lu\\Desktop\\Archive\\DA\\SHK_HZDR\\Projects\\Release')],
			   [('C:\\Users\\Xueyong Lu\\Desktop\\Archive\\DA\\SHK_HZDR\\Projects\\PHD Ultra_remote control_QT Designer\\settings', 'C:\\Users\\Xueyong Lu\\Desktop\\Archive\\DA\\SHK_HZDR\\Projects\\Release')],
			   [('C:\\Users\\Xueyong Lu\\Desktop\\Archive\\DA\\SHK_HZDR\\Projects\\PHD Ultra_remote control_QT Designer\\logs', 'C:\\Users\\Xueyong Lu\\Desktop\\Archive\\DA\\SHK_HZDR\\Projects\\Release')],
			   [('C:\\Users\\Xueyong Lu\\Desktop\\Archive\\DA\\SHK_HZDR\\Projects\\PHD Ultra_remote control_QT Designer\\.msc', 'C:\\Users\\Xueyong Lu\\Desktop\\Archive\\DA\\SHK_HZDR\\Projects\\Release')],
			   [('C:\\Users\\Xueyong Lu\\Desktop\\Archive\\DA\\SHK_HZDR\\Projects\\PHD Ultra_remote control_QT Designer\\.idea', 'C:\\Users\\Xueyong Lu\\Desktop\\Archive\\DA\\SHK_HZDR\\Projects\\Release')],
			   [('C:\\Users\\Xueyong Lu\\Desktop\\Archive\\DA\\SHK_HZDR\\Projects\\PHD Ultra_remote control_QT Designer\\qss', 'C:\\Users\\Xueyong Lu\\Desktop\\Archive\\DA\\SHK_HZDR\\Projects\\Release')],
			   [('C:\\Users\\Xueyong Lu\\Desktop\\Archive\\DA\\SHK_HZDR\\Projects\\PHD Ultra_remote control_QT Designer\\json', 'C:\\Users\\Xueyong Lu\\Desktop\\Archive\\DA\\SHK_HZDR\\Projects\\Release')]
               )
