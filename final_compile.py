#!/usr/bin/env python3
"""
Compilation script for wd14-tagger API
Handles Nuitka compilation with all necessary dependencies and data files
"""

import os
import sys
import shutil
import subprocess
import onnxruntime

def main():
    print("Starting compilation process...")
    
    # 使用指定的Python版本
    python_exe = "py"
    python_version = "-3.10"
    
    # 清理之前的构建
    if os.path.exists('dist'):
        shutil.rmtree('dist')
        print("Cleaned dist directory")
    
    # 获取onnxruntime基础路径
    onnxruntime_base = os.path.dirname(os.path.abspath(onnxruntime.__file__))
    
    # 构建Nuitka命令
    cmd = [
        python_exe, python_version, "-m", "nuitka",
        "--standalone",
        "--onefile",
        "--output-dir=dist",
        "--windows-console-mode=force",
        "--nofollow-import-to=numpy.distutils",
        "--nofollow-import-to=numpy.f2py",
        "--nofollow-import-to=numpy.testing",
        "--nofollow-import-to=PIL.ImageQt",
        "--include-module=tagger",
        "--include-module=tagger.api",
        "--include-module=tagger.interrogator",
        "--include-module=tagger.utils",
        "--include-module=tagger.api_models",
        "--include-module=tagger.settings",
        "--include-package-data=gradio",
        "--include-package-data=onnxruntime",
        "--include-module=onnxruntime.capi.onnxruntime_pybind11_state",
        f"--include-data-file={os.path.join(onnxruntime_base, '..', 'safehttpx', 'version.txt')}=safehttpx/version.txt",
        f"--include-data-file={os.path.join(onnxruntime_base, '..', 'groovy', 'version.txt')}=groovy/version.txt"
    ]
    
    # 添加主程序文件
    cmd.append('wd14_tagger_exe.py')
    
    print("\nCompilation command:")
    print(' '.join(cmd))
    
    # 执行编译
    print("\nExecuting Nuitka compilation...")
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("\n========================================")
        print("SUCCESS: Compilation completed successfully!")
        exe_path = os.path.join('dist', 'wd14_tagger_exe.exe')
        if os.path.exists(exe_path):
            print(f"Executable created at: {exe_path}")
        else:
            print("Warning: Executable file not found at expected location")
        print("========================================")
    else:
        print("\n========================================")
        print("ERROR: Compilation failed with exit code:", result.returncode)
        print("========================================")
        sys.exit(1)

if __name__ == "__main__":
    main()