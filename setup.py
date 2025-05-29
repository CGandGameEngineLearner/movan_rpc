#!/usr/bin/env python3
# 此文件用于兼容旧版本工具，现代工具将优先使用pyproject.toml

from setuptools import setup

if __name__ == "__main__":
    try:
        setup()
    except Exception:
        import sys
        import traceback
        traceback.print_exc()
        sys.exit(1)