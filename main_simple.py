#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简化版主程序
用于测试完整UI启动
"""

import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

# 添加项目根目录到系统路径
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from ui.styles.themes import DarkTheme

class SimpleMainWindow(QMainWindow):
    """
    简化的主窗口
    """
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        """
        初始化用户界面
        """
        self.setWindowTitle("股票分析系统")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中央组件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建布局
        layout = QVBoxLayout(central_widget)
        
        # 添加标签
        label = QLabel("股票分析系统启动成功！")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #FFFFFF;
                padding: 20px;
            }
        """)
        layout.addWidget(label)
        
        # 状态栏
        self.statusBar().showMessage("就绪")

def setup_application():
    """
    设置应用程序基本配置
    """
    # 创建应用程序实例
    app = QApplication(sys.argv)
    
    # 设置应用程序信息
    app.setApplicationName("股票分析系统")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Stock Analysis")
    app.setOrganizationDomain("stockanalysis.com")
    
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
    try:
        print("正在启动股票分析系统...")
        
        # 设置应用程序
        app = setup_application()
        print("应用程序配置完成")
        
        # 创建主窗口
        main_window = SimpleMainWindow()
        print("主窗口创建完成")
        
        # 显示主窗口
        main_window.show()
        print("主窗口显示完成")
        
        print("启动应用程序事件循环...")
        # 运行应用程序
        sys.exit(app.exec())
        
    except Exception as e:
        print(f"应用程序启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()