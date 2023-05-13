# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

# 添加自定义函数 collect_dependencies()
def collect_dependencies():
    import os
    import sys
    import subprocess

    # 创建一个文件夹用于存放依赖文件
    dependencies_folder = 'dependencies'
    os.makedirs(dependencies_folder, exist_ok=True)

    # 使用 pip freeze 命令获取项目的依赖列表
    output = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze']).decode('utf-8')
    dependencies = output.strip().split('\n')

    # 将依赖库文件复制到 dependencies 文件夹中
    for dependency in dependencies:
        package_name = dependency.split('==')[0]
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-d', dependencies_folder, package_name])

    # 返回数据文件配置
    return [(os.path.join(dependencies_folder, '*'), 'dependencies')]

block_cipher = None


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['qdarktheme','numpy'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PHD MA1 70-3xxx Series Syringe Pump v1.0.0',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
	icon='./image/Logo_TU_Dresden_small.ico'
)
