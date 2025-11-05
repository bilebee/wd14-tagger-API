#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess
import sys
import os

def get_python_path():
    # 检查是否存在python3.10
    possible_paths = [
        "python3.10",
        "py -3.10",
        sys.executable  # 当前使用的python路径
    ]
    
    for path in possible_paths:
        try:
            result = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and "3.10" in result.stdout:
                return path
        except Exception:
            continue
    
    # 如果没有找到python3.10，则使用当前python
    return sys.executable

def get_package_version_files():
    """
    获取需要包含在可执行文件中的包版本文件列表
    返回格式: [(源文件路径, 目标相对路径), ...]
    """
    version_files = []
    
    # 需要包含version.txt文件的包列表
    packages_with_versions = ['safehttpx', 'groovy']
    
    for package_name in packages_with_versions:
        try:
            # 动态导入包以获取其路径
            package = __import__(package_name)
            if hasattr(package, '__file__') and package.__file__:
                # 构建version.txt的完整路径
                package_dir = os.path.dirname(package.__file__)
                version_file_src = os.path.join(package_dir, 'version.txt')
                
                # 检查文件是否存在
                if os.path.exists(version_file_src):
                    # 目标路径保持包名结构
                    version_file_dst = f"{package_name}/version.txt"
                    version_files.append((version_file_src, version_file_dst))
                else:
                    print(f"Warning: version.txt not found for package {package_name}")
            else:
                print(f"Warning: Could not determine path for package {package_name}")
        except ImportError as e:
            print(f"Warning: Could not import package {package_name}: {e}")
        except Exception as e:
            print(f"Warning: Error processing package {package_name}: {e}")
    
    return version_files

def main():
    python_cmd = get_python_path()
    print(f"Using Python command: {python_cmd}")
    print("Running Nuitka compilation...")
    
    # 获取当前脚本所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(current_dir, "dist")
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 构建基础命令
    cmd = [
        python_cmd,
        "-m", "nuitka",
        "--standalone",
        "--onefile",
        "--mingw64",
        "--windows-console=force",
        f"--output-dir={output_dir}",
        "--remove-output",
        "--assume-yes-for-downloads",
        "--noinclude-unittest-mode=error",
        "--noinclude-pytest-mode=error",
        "--noinclude-setuptools-mode=error",
        "--module-parameter=torch-disable-jit=yes",
        "--lto=no",  # 禁用LTO避免之前的编译错误
        "--jobs=4",
        "--include-package=tagger",
        "--include-package=fastapi",
        "--include-package=uvicorn",
        "--include-package=PIL",
        "--include-package=jsonschema",
        "--include-module=safehttpx",
        "--include-module=groovy",
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
        os.path.join(current_dir, "wd14_tagger_exe.py")
    ]
    
    # 添加需要的数据文件
    version_files = get_package_version_files()
    for src, dst in version_files:
        cmd.append(f"--include-data-file={src}={dst}")
        print(f"Including data file: {src} -> {dst}")
    
    print("Command:", " ".join(cmd))
    
    try:
        result = subprocess.run(cmd, check=True)
        print("\nCompilation completed successfully!")
        print(f"Executable has been created in {os.path.join(output_dir, 'wd14_tagger_exe.exe')}")
    except subprocess.CalledProcessError as e:
        print(f"\nCompilation failed with error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nCompilation cancelled by user.")
        sys.exit(1)

if __name__ == "__main__":
    main()