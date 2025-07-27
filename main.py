#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
股票分析系统主程序
参考同花顺iFinD、Wind等专业财经软件设计
"""

import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QFont

# 添加项目根目录到系统路径
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from ui.main_window import MainWindow
from ui.styles.themes import DarkTheme


def setup_application():
    """
    设置应用程序基本配置
    """
    # 启用高DPI支持 (PyQt6中已默认启用)
    try:
        # PyQt5兼容性
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
    except AttributeError:
        # PyQt6中这些属性已被移除，默认启用高DPI支持
        pass
    
    # 创建应用程序实例
    app = QApplication(sys.argv)
    
    # 设置应用程序信息
    app.setApplicationName("股票分析系统")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Stock Analysis")
    app.setOrganizationDomain("stockanalysis.com")
    
    # 设置应用程序图标
    # app.setWindowIcon(QIcon("resources/icons/app_icon.png"))
    
    # 设置默认字体
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)
    
    # 应用暗色主题
    app.setStyleSheet(DarkTheme.get_stylesheet())
    
    return app


def main():
    """
    主函数
    """
    app = None
    try:
        print("正在启动股票分析系统...")
        
        # 设置应用程序
        print("设置应用程序配置...")
        app = setup_application()
        print("应用程序配置完成")
        
        # 创建主窗口
        print("创建主窗口...")
        main_window = MainWindow()
        print("主窗口创建完成")
        
        # 显示主窗口
        print("显示主窗口...")
        main_window.show()
        print("主窗口显示完成")
        
        print("启动应用程序事件循环...")
        # 运行应用程序
        sys.exit(app.exec())
        
    except Exception as e:
        print(f"应用程序启动失败: {e}")
        import traceback
        traceback.print_exc()
        if app:
            app.quit()
        sys.exit(1)


if __name__ == "__main__":
    main()