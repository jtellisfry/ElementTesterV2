# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['\\\\fryfs001v\\eng\\DEPTS\\LAB\\Test Engineering\\Tester Information\\ElementTesterV2(Python)\\ElementTesterV2\\src\\element_tester\\system\\core\\test_runner.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['element_tester.programs.hipot_test', 'element_tester.programs.hipot_test.test_1_hypot', 'element_tester.programs.measurement_test', 'element_tester.programs.measurement_test.test_1_pin1to6', 'element_tester.programs.measurement_test.test_2_pin2to5', 'element_tester.programs.measurement_test.test_3_pin3to4', 'element_tester.programs.simulate_test'],
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
    name='ElementTesterV2',
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
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ElementTesterV2',
)
