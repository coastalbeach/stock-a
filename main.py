#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
主程序入口
启动A股量化分析系统
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到系统路径
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow

def main():
    """程序主入口"""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()