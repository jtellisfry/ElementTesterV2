import subprocess
import sys
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
    ]

    pyinstaller_args = [
        "pyinstaller",
        "--clean",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name", "ElementTesterV2",
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
