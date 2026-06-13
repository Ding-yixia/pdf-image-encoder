#!/usr/bin/env python3
"""
PDF Image Encoder — 打包脚本

使用 PyInstaller 将项目打包为单文件 exe。

用法:
    python build_exe.py                  # 默认Release构建
    python build_exe.py --debug          # Debug构建(含控制台)
    python build_exe.py --clean          # 清理构建产物

输出:
    dist/PDFImageEncoder.exe             # 单文件可执行 (约30-50MB)
    build/                               # 临时构建文件(可删除)
"""
import os
import sys
import shutil
import argparse
import subprocess
from pathlib import Path


def ensure_pyinstaller():
    """检查并安装 PyInstaller"""
    try:
        import PyInstaller
        print(f'[OK] PyInstaller {PyInstaller.__version__}')
    except ImportError:
        print('安装 PyInstaller...')
        subprocess.run(
            [sys.executable, '-m', 'pip', 'install', 'pyinstaller'],
            check=True
        )


def build(args):
    """执行打包"""
    project_root = Path(__file__).parent.resolve()
    dist_dir = project_root / 'dist'
    build_dir = project_root / 'build'
    spec_file = project_root / 'PDFImageEncoder.spec'

    # 清理旧的构建产物
    if args.clean:
        for d in [dist_dir, build_dir]:
            if d.exists():
                shutil.rmtree(d)
                print(f'清理: {d}')
        if spec_file.exists():
            spec_file.unlink()
            print(f'清理: {spec_file}')
        print('[OK] 清理完成')
        if not args.build:
            return

    # 确保入口文件存在
    entry = project_root / 'run.py'
    if not entry.exists():
        print(f'[ERR] 入口文件不存在: {entry}')
        sys.exit(1)

    print(f'[BUILD] 打包: {entry}')
    print(f'    输出: {dist_dir / "PDFImageEncoder.exe"}')

    # PyInstaller 参数
    pyi_args = [
        sys.executable, '-m', 'PyInstaller',
        '--onefile',                    # 单文件 exe
        '--name', 'PDFImageEncoder',    # exe 名称
        '--distpath', str(dist_dir),
        '--workpath', str(build_dir),
        '--specpath', str(project_root),
        # 排除不需要的庞大依赖
        '--exclude-module', 'matplotlib',
        '--exclude-module', 'pandas',
        '--exclude-module', 'PySide6',
        '--exclude-module', 'PyQt5',
        '--exclude-module', 'PyQt6',
        '--exclude-module', 'notebook',
        '--exclude-module', 'scipy',
        '--exclude-module', 'sklearn',
        '--exclude-module', 'sqlalchemy',
        '--exclude-module', 'openpyxl',
        '--exclude-module', 'pydantic',
        # 显式声明需要的隐藏导入
        '--hidden-import', 'imagecodecs',
        '--hidden-import', 'imagecodecs._imagecodecs',
        '--hidden-import', 'imagecodecs._lzw',
        '--hidden-import', 'PIL',
        '--hidden-import', 'PIL._imaging',
        '--hidden-import', 'yaml',
        '--hidden-import', 'pikepdf',
        '--hidden-import', 'zlib',
    ]

    # 调试模式: 保留控制台窗口
    if args.debug:
        pyi_args.append('--debug')
        print('[WARN] Debug模式: 保留控制台')
    else:
        pyi_args.append('--noconsole')
        # Release模式: 添加版本信息(可选)
        version_info = project_root / 'version.txt'
        if version_info.exists():
            pyi_args.extend(['--version-file', str(version_info)])

    pyi_args.append(str(entry))

    # 执行打包
    print('[START] 开始打包...')
    result = subprocess.run(pyi_args, cwd=project_root)
    if result.returncode != 0:
        print(f'[ERR] 打包失败 (exit code: {result.returncode})')
        sys.exit(1)

    # 验证输出
    exe_path = dist_dir / 'PDFImageEncoder.exe'
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f'\n[OK] 打包成功!')
        print(f'   📄 {exe_path}')
        print(f'     {size_mb:.1f} MB')
        print(f'\n用法:')
        print(f'  PDFImageEncoder.exe --input D:\\wallpapers')
        print(f'  PDFImageEncoder.exe --encoders LZW,DCT --count 5')
        print(f'  PDFImageEncoder.exe --help')
    else:
        print(f'[ERR] 未找到输出文件: {exe_path}')
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='PDF Image Encoder 打包脚本')
    parser.add_argument('--debug', action='store_true',
                        help='Debug构建(保留控制台)')
    parser.add_argument('--clean', action='store_true',
                        help='清理构建产物')
    parser.add_argument('--build', action='store_true', default=True,
                        help='执行打包(默认启用)')
    args = parser.parse_args()

    print('=' * 50)
    print('PDF Image Encoder — 打包工具')
    print('=' * 50)

    ensure_pyinstaller()
    build(args)

    print('=' * 50)
    print('完成')
    print('=' * 50)


if __name__ == '__main__':
    main()
