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

def get_site_packages_dirs():
    """获取所有site-packages目录路径"""
    import site
    site_packages_dirs = site.getsitepackages()
    user_site = site.getusersitepackages()
    if user_site:
        site_packages_dirs.append(user_site)
    return site_packages_dirs

def find_version_files():
    """查找所有需要包含的version.txt文件"""
    version_files = []
    site_packages_dirs = get_site_packages_dirs()
    
    for site_pkg in site_packages_dirs:
        site_path = Path(site_pkg)
        if not site_path.exists():
            continue
            
        # 查找特定包中的version.txt文件
        for pkg_name in ['safehttpx', 'groovy']:
            version_file = site_path / pkg_name / 'version.txt'
            if version_file.exists():
                version_files.append(str(version_file))
                
    return version_files

def main():
    print("Compiling WD14 Tagger API with Nuitka...")
    
    # Check Python version compatibility
    if not check_python_version():
        sys.exit(1)
    
    # Get project root directory
    project_root = Path(__file__).parent.absolute()
    print(f"Project root: {project_root}")
    
    # Entry point script
    entry_script = project_root / "simple_api.py"
    
    if not entry_script.exists():
        print(f"Error: {entry_script} not found")
        sys.exit(1)
    
    # Output directory
    output_dir = project_root / "dist"
    output_dir.mkdir(exist_ok=True)
    
    # 查找需要包含的version.txt文件
    version_files = find_version_files()
    print(f"Found {len(version_files)} version.txt files to include")
    
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
        "--include-package=yaml",
        # Include simple_api module
        "--include-module=simple_api",
    ]

    # 添加找到的version.txt文件
    for version_file in version_files:
        pkg_name = Path(version_file).parent.name
        cmd.append(f"--include-data-file={version_file}={pkg_name}/version.txt")

    # 添加其他Nuitka选项
    cmd.extend([
        # Follow imports for key packages but exclude tests
        # 显式包含需要的模块，然后排除不需要的测试模块
        "--follow-import-to=jsonschema",
        # 排除特定不需要的测试模块
        "--nofollow-import-to=*.tests",
        "--nofollow-import-to=*.test",
        "--nofollow-import-to=pandas.tests",
        "--nofollow-import-to=pandas.util._test*",
        "--nofollow-import-to=torch.utils.cpp_extension",
        "--nofollow-import-to=numpy.testing._private.utils",
        "--nofollow-import-to=numpy.ma.testutils",
        "--nofollow-import-to=numpy.conftest",
        "--nofollow-import-to=pandas.conftest",
        "--nofollow-import-to=jsonschema.tests",
        # 明确排除 gradio 及其相关模块
        "--nofollow-import-to=gradio",
        # 明确排除 jinja2 及其相关模块
        "--nofollow-import-to=jinja2",
        str(entry_script)
    ])
    
    print("Running Nuitka compilation...")
    print("Command:", " ".join(cmd))
    
    try:
        result = subprocess.run(cmd, check=True, cwd=project_root)
        print("Compilation completed successfully!")
        print(f"Executable created at: {output_dir / 'simple_api.exe'}")
        print("\nNote: The executable will create a default config.yaml file on first run.")
        print("You can modify this file to configure the server.")
    except subprocess.CalledProcessError as e:
        print(f"Compilation failed with error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nCompilation interrupted by user")
        sys.exit(1)

if __name__ == "__main__":
    main()