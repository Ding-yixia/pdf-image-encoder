#!/usr/bin/env python3
"""
PDF Image Encoder — 单文件可执行入口
支持: python run.py / pyinstaller 打包为 exe

用法:
    run.py --input D:\wallpapers --output ./out
    run.py --input ./images --encoders LZW,DCT,Flate --count 5 --size 300
    run.py --encoders all                     # 全部7种编码
"""
import sys
import os

# 确保能正确找到 src 包 (兼容源码运行和 PyInstaller 打包)
if getattr(sys, 'frozen', False):
    # PyInstaller 打包后的环境
    BASE_DIR = os.path.dirname(sys.executable)
    sys.path.insert(0, os.path.join(BASE_DIR, '_internal'))
else:
    # 源码开发环境
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, BASE_DIR)

# 延迟导入避免打包时递归解析
def main():
    from src.main import main as cli_main
    cli_main()

if __name__ == '__main__':
    main()
