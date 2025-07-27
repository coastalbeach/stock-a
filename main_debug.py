#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试版主程序 - 逐步测试UI组件
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QHBoxLayout, QLabel, QTabWidget, QDockWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ui.styles.theme_manager import ThemeManager
from ui.widgets.stock_selector import StockSelector
from ui.widgets.chart_widget import ChartWidget
from ui.widgets.data_table import DataTableWidget
from ui.widgets.info_panel import InfoPanel
from ui.widgets.strategy_panel import StrategyPanel

class DebugMainWindow(QMainWindow):
    """调试版主窗口"""
    
    def __init__(self):
        super().__init__()
        self.theme_manager = ThemeManager()
        self.init_ui()
        
    def init_ui(self):
        """初始化用户界面"""
        print("设置窗口基本属性...")
        self.setWindowTitle("A股量化分析系统 - 调试版")
        self.setGeometry(100, 100, 1200, 800)
        
        print("创建中央部件...")
        self.setup_central_widget()
        
        print("创建停靠面板...")
        self.setup_dock_widgets()
        
        print("应用主题...")
        self.theme_manager.apply_theme(self, "dark")
        
    def setup_central_widget(self):
        """设置中央部件"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        
        # 添加主图表
        print("创建主图表...")
        self.main_chart = ChartWidget()
        self.tab_widget.addTab(self.main_chart, "主图表")
        
        layout.addWidget(self.tab_widget)
        
    def setup_dock_widgets(self):
        """设置停靠面板"""
        # 左侧股票选择器
        print("创建股票选择器停靠面板...")
        self.stock_dock = QDockWidget("股票选择", self)
        self.stock_selector = StockSelector()
        self.stock_dock.setWidget(self.stock_selector)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.stock_dock)
        
        # 右侧信息面板
        print("创建信息面板停靠面板...")
        self.info_dock = QDockWidget("股票信息", self)
        self.info_panel = InfoPanel()
        self.info_dock.setWidget(self.info_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.info_dock)
        
        # 右侧策略面板
        print("创建策略面板停靠面板...")
        self.strategy_dock = QDockWidget("策略分析", self)
        self.strategy_panel = StrategyPanel()
        self.strategy_dock.setWidget(self.strategy_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.strategy_dock)
        
        # 底部数据表格
        print("创建数据表格停靠面板...")
        self.data_dock = QDockWidget("数据表格", self)
        self.data_table = DataTableWidget()
        self.data_dock.setWidget(self.data_table)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.data_dock)

def setup_application():
    """设置应用程序"""
    app = QApplication(sys.argv)
    
    # 设置应用程序信息
    app.setApplicationName("A股量化分析系统")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("Stock Analysis")
    
    # 设置字体
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)
    
    return app

def main():
    """主函数"""
    try:
        print("正在启动调试版股票分析系统...")
        
        # 设置应用程序
        print("设置应用程序配置...")
        app = setup_application()
        print("应用程序配置完成")
        
        # 创建主窗口
        print("创建调试版主窗口...")
        main_window = DebugMainWindow()
        print("调试版主窗口创建完成")
        
        # 显示主窗口
        print("显示调试版主窗口...")
        main_window.show()
        print("调试版主窗口显示完成")
        
        print("启动应用程序事件循环...")
        # 运行应用程序
        sys.exit(app.exec())
        
    except Exception as e:
        print(f"调试版应用程序启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()