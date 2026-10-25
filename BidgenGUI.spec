# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置（macOS 唯一来源，由 scripts/build_macos.sh 调用）。

入库受控文件——新增依赖的 collect / 资源 / plist 声明都在此维护：
- info_plist.CFBundleDocumentTypes：声明可打开 PDF，支撑拖文件到 Dock/图标与「打开方式」
- CFBundleShortVersionString：与 version.json 同步（version.json 为发布版本源）
"""

import json

from PyInstaller.utils.hooks import collect_all

with open('version.json', encoding='utf-8') as _f:
    _version = json.load(_f)['version']

datas = [('assets', 'assets')]
binaries = []
hiddenimports = ['PySide6']
for _pkg in ('fitz', 'pdf2docx', 'cv2', 'docx', 'yaml', 'bidgen'):
    _ret = collect_all(_pkg)
    datas += _ret[0]; binaries += _ret[1]; hiddenimports += _ret[2]


a = Analysis(
    ['app_gui.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BidgenGUI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets/logo.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='BidgenGUI',
)
app = BUNDLE(
    coll,
    name='投标助手.app',
    icon='assets/logo.icns',
    bundle_identifier='BidgenGUI',
    info_plist={
        'CFBundleShortVersionString': _version,
        # 显示名「投标助手」：Finder/Dock/启动台以此显示（.app 文件名保持 BidgenGUI 不动）
        'CFBundleDisplayName': '投标助手',
        'CFBundleName': '投标助手',
        # 声明可打开 PDF：拖放到 Dock/.app 图标与 Finder「打开方式」均依赖此声明；
        # Alternate + Viewer 表示不抢占系统默认 PDF 阅读器
        'CFBundleDocumentTypes': [
            {
                'CFBundleTypeName': 'PDF 招标文件',
                'CFBundleTypeRole': 'Viewer',
                'LSItemContentTypes': ['com.adobe.pdf'],
                'LSHandlerRank': 'Alternate',
            },
        ],
    },
)
