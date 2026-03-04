import subprocess
import sys
import shutil
import re
from pathlib import Path


def build_element_tester():
    """
    Builds the Element Tester application using PyInstaller with predefined arguments.
    """
    project_root = Path(__file__).resolve().parent
    script_path = project_root / "src" / "element_tester" / "system" / "core" / "test_runner.py"
    if not script_path.exists():
        print(f"Error: {script_path} does not exist.")
        sys.exit(1)

    # backup previous build output if present; the backup directory must live
    # outside the top-level `build` tree, otherwise the next clean operation would
    # delete the copy we just made.
    backup_root = project_root / "build_backups"
    backup_root.mkdir(parents=True, exist_ok=True)
    existing_versions = []
    for p in backup_root.iterdir():
        if p.is_dir():
            m = re.match(r"Version(\d+)$", p.name)
            if m:
                existing_versions.append(int(m.group(1)))
    next_num = max(existing_versions) + 1 if existing_versions else 1
    new_version_name = f"Version{next_num:03d}"
    new_version_folder = backup_root / new_version_name
    old_build_folder = project_root / "build" / "ElementTesterV2"
    if old_build_folder.exists():
        print(f"Backing up previous build to {new_version_folder}")
        shutil.copytree(old_build_folder, new_version_folder)
    else:
        print(f"No previous build found; creating empty backup folder {new_version_folder}")
        new_version_folder.mkdir()

    # cleanup any leftover build/dist directories so pyinstaller starts fresh
    build_folder = project_root / "build"
    if build_folder.exists():
        print(f"Removing old build folder: {build_folder}")
        shutil.rmtree(build_folder)
    # older versions used a separate dist directory; remove it as well
    dist_folder = project_root / "dist"
    if dist_folder.exists():
        print(f"Removing old dist folder: {dist_folder}")
        shutil.rmtree(dist_folder)

    # Hidden imports for dynamically discovered test modules
    # PyInstaller can't detect these since they're loaded via pkgutil at runtime
    hidden_imports = [
        # Hipot test modules
        "element_tester.programs.hipot_test",
        "element_tester.programs.hipot_test.test_1_hypot",
        # Measurement test modules
        "element_tester.programs.measurement_test",
        "element_tester.programs.measurement_test.test_1_pin1to6",
        "element_tester.programs.measurement_test.test_2_pin2to5",
        "element_tester.programs.measurement_test.test_3_pin3to4",
        # Simulate test modules (if any)
        "element_tester.programs.simulate_test",
        # Printing support (pywin32)
        "win32print",
        "win32ui",
    ]

    build_folder = project_root / "build"
    
    pyinstaller_args = [
        "pyinstaller",
        "--clean",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name", "ElementTesterV2",
        "--distpath", str(build_folder),
        # PyInstaller uses "--workpath" (or "-w") for the build directory (formerly called
        # "buildpath"). "--buildpath" is not a recognized option and leads to errors.
        "--workpath", str(build_folder / "build_artifacts"),
        "--specpath", str(build_folder),
    ]
    
    # Add hidden imports
    for hidden in hidden_imports:
        pyinstaller_args.extend(["--hidden-import", hidden])
    
    pyinstaller_args.append(str(script_path))

    print("Running PyInstaller with arguments:")
    print(" ".join(pyinstaller_args))

    try:
        subprocess.run(pyinstaller_args, check=True)
        print("Build completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Build failed with error: {e}")
        sys.exit(e.returncode)


if __name__ == "__main__":
    build_element_tester()
