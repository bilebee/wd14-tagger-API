#!/usr/bin/env python3
"""
Compile script for WD14 Tagger API using Nuitka
Creates a standalone executable that behaves like run_server.bat
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible with Nuitka and MinGW64"""
    major, minor = sys.version_info[:2]
    if major > 3 or (major == 3 and minor >= 13):
        print(f"Error: Python {major}.{minor} is not fully compatible with Nuitka and MinGW64")
        print("Please use Python 3.12 or earlier to compile this project")
        print("You can:")
        print("1. Download Python 3.12 from https://www.python.org/downloads/release/python-312/")
        print("2. Or use a specific Python version with: py -3.10 compile.py")
        return False
    return True

def main():
    print("Compiling WD14 Tagger API with Nuitka...")
    
    # Check Python version compatibility
    if not check_python_version():
        sys.exit(1)
    
    # Get project root directory
    project_root = Path(__file__).parent.absolute()
    print(f"Project root: {project_root}")
    
    # Entry point script
    entry_script = project_root / "wd14_tagger_exe.py"
    
    if not entry_script.exists():
        print(f"Error: {entry_script} not found")
        sys.exit(1)
    
    # Output directory
    output_dir = project_root / "dist"
    output_dir.mkdir(exist_ok=True)
    
    # Nuitka command with optimizations
    cmd = [
        sys.executable, "-m", "nuitka",
        "--standalone",
        "--onefile",
        "--mingw64",
        "--windows-console=force",
        "--output-dir=" + str(output_dir),
        "--remove-output",
        "--assume-yes-for-downloads",
        # Anti-bloat plugin configurations to exclude test modules
        "--noinclude-unittest-mode=error",
        "--noinclude-pytest-mode=error",
        "--noinclude-setuptools-mode=error",
        # Explicitly set Torch JIT parameter
        "--module-parameter=torch-disable-jit=yes",
        # Disable LTO to prevent compilation errors
        # "--lto=yes",
        # Use multiple cores for faster compilation
        "--jobs=4",
        # Include necessary packages
        "--include-package=tagger",
        "--include-package=fastapi",
        "--include-package=uvicorn",
        "--include-package=PIL",
        "--include-package=jsonschema",
        "--include-module=safehttpx",
        # Include data files for safehttpx
        "--include-data-file=C:\\path\\to\\Python\\Python310\\lib\\site-packages\\safehttpx\\version.txt=safehttpx/version.txt",
        # Follow imports for key packages but exclude tests
        "--nofollow-import-to=*.tests",
        "--nofollow-import-to=*.test",
        "--nofollow-import-to=pandas.tests",
        "--nofollow-import-to=pandas.util._test*",
        "--nofollow-import-to=jsonschema.tests",
        "--nofollow-import-to=torch.utils.cpp_extension",
        "--nofollow-import-to=numpy.testing._private.utils",
        "--nofollow-import-to=numpy.ma.testutils",
        "--nofollow-import-to=numpy.conftest",
        "--nofollow-import-to=pandas.conftest",
        str(entry_script)
    ]
    
    print("Running Nuitka compilation...")
    print("Command:", " ".join(cmd))
    
    try:
        result = subprocess.run(cmd, check=True, cwd=project_root)
        print("Compilation completed successfully!")
        print(f"Executable created at: {output_dir / 'wd14_tagger_exe.exe'}")
    except subprocess.CalledProcessError as e:
        print(f"Compilation failed with error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nCompilation interrupted by user")
        sys.exit(1)

if __name__ == "__main__":
    main()