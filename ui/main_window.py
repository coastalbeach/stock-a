#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
主窗口 - A股量化分析系统
参考同花顺iFinder等专业财经软件设计
"""

import sys
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QSplitter, QTabWidget, QDockWidget, QMenuBar, 
    QToolBar, QStatusBar, QApplication, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QIcon, QKeySequence

from pathlib import Path
project_root = str(Path(__file__).resolve().parent.parent) 
if project_root not in sys.path:
    sys.path.append(project_root)

from ui.widgets.stock_selector import StockSelector
from ui.widgets.chart_widget import ChartWidget
from ui.widgets.data_table import DataTableWidget
from ui.widgets.info_panel import InfoPanel
from ui.widgets.strategy_panel import StrategyPanel
from ui.dialogs.settings_dialog import SettingsDialog
from ui.styles.theme_manager import ThemeManager


class MainWindow(QMainWindow):
    """
    主窗口类
    实现专业财经软件的多面板布局
    """
    
    # 信号定义
    stock_selected = pyqtSignal(str)  # 股票选择信号
    theme_changed = pyqtSignal(str)   # 主题切换信号
    
    def __init__(self):
        super().__init__()
        self.theme_manager = ThemeManager()
        self.init_ui()
        self.setup_connections()
        self.setup_timer()
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("A股量化分析系统 v0.1.0")
        self.setGeometry(100, 100, 1600, 900)
        
        # 设置中央部件
        self.setup_central_widget()
        
        # 设置停靠面板
        self.setup_dock_widgets()
        
        # 设置菜单栏
        self.setup_menu_bar()
        
        # 设置工具栏
        self.setup_tool_bar()
        
        # 设置状态栏
        self.setup_status_bar()
        
        # 应用主题
        self.theme_manager.apply_to_widget(self, "dark")
        
    def setup_central_widget(self):
        """设置中央部件 - 主要图表区域"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # 创建标签页组件
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        
        # 添加默认图表标签页
        self.main_chart = ChartWidget()
        self.tab_widget.addTab(self.main_chart, "主图表")
        
        main_layout.addWidget(self.tab_widget)
        
    def setup_dock_widgets(self):
        """设置停靠面板"""
        # 左侧股票选择器
        self.stock_dock = QDockWidget("股票选择", self)
        self.stock_selector = StockSelector()
        self.stock_dock.setWidget(self.stock_selector)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.stock_dock)
        
        # 右侧信息面板
        self.info_dock = QDockWidget("股票信息", self)
        self.info_panel = InfoPanel()
        self.info_dock.setWidget(self.info_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.info_dock)
        
        # 右侧策略面板
        self.strategy_dock = QDockWidget("策略管理", self)
        self.strategy_panel = StrategyPanel()
        self.strategy_dock.setWidget(self.strategy_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.strategy_dock)
        
        # 底部数据表格
        self.data_dock = QDockWidget("数据表格", self)
        self.data_table = DataTableWidget()
        self.data_dock.setWidget(self.data_table)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.data_dock)
        
        # 设置停靠面板的初始大小
        self.resizeDocks([self.stock_dock], [300], Qt.Orientation.Horizontal)
        self.resizeDocks([self.info_dock, self.strategy_dock], [250, 250], Qt.Orientation.Horizontal)
        self.resizeDocks([self.data_dock], [200], Qt.Orientation.Vertical)
        
    def setup_menu_bar(self):
        """设置菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件(&F)')
        
        # 新建工作区
        new_action = QAction('新建工作区(&N)', self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self.new_workspace)
        file_menu.addAction(new_action)
        
        # 打开工作区
        open_action = QAction('打开工作区(&O)', self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_workspace)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        # 退出
        exit_action = QAction('退出(&X)', self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 视图菜单
        view_menu = menubar.addMenu('视图(&V)')
        
        # 面板显示控制
        view_menu.addAction(self.stock_dock.toggleViewAction())
        view_menu.addAction(self.info_dock.toggleViewAction())
        view_menu.addAction(self.strategy_dock.toggleViewAction())
        view_menu.addAction(self.data_dock.toggleViewAction())
        
        view_menu.addSeparator()
        
        # 主题切换
        theme_menu = view_menu.addMenu('主题')
        
        dark_theme_action = QAction('深色主题', self)
        dark_theme_action.triggered.connect(lambda: self.change_theme('dark'))
        theme_menu.addAction(dark_theme_action)
        
        light_theme_action = QAction('浅色主题', self)
        light_theme_action.triggered.connect(lambda: self.change_theme('light'))
        theme_menu.addAction(light_theme_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu('工具(&T)')
        
        # 设置
        settings_action = QAction('设置(&S)', self)
        settings_action.triggered.connect(self.show_settings)
        tools_menu.addAction(settings_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助(&H)')
        
        # 关于
        about_action = QAction('关于(&A)', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def setup_tool_bar(self):
        """设置工具栏"""
        toolbar = QToolBar("主工具栏")
        self.addToolBar(toolbar)
        
        # 刷新数据
        refresh_action = QAction('刷新', self)
        refresh_action.setToolTip('刷新当前数据')
        refresh_action.triggered.connect(self.refresh_data)
        toolbar.addAction(refresh_action)
        
        toolbar.addSeparator()
        
        # 开始/停止实时数据
        self.realtime_action = QAction('开始实时', self)
        self.realtime_action.setToolTip('开始/停止实时数据更新')
        self.realtime_action.setCheckable(True)
        self.realtime_action.triggered.connect(self.toggle_realtime)
        toolbar.addAction(self.realtime_action)
        
    def setup_status_bar(self):
        """设置状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 显示就绪状态
        self.status_bar.showMessage("就绪")
        
    def setup_connections(self):
        """设置信号连接"""
        # 股票选择信号
        self.stock_selector.stock_selected.connect(self.on_stock_selected)
        
        # 标签页关闭信号
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        
    def setup_timer(self):
        """设置定时器"""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_realtime_data)
        
    def on_stock_selected(self, stock_code):
        """处理股票选择事件"""
        self.stock_selected.emit(stock_code)
        self.main_chart.load_stock_data(stock_code)
        self.info_panel.update_stock_info(stock_code)
        self.data_table.load_stock_data(stock_code)
        
        # 更新状态栏
        self.status_bar.showMessage(f"已选择股票: {stock_code}")
        
    def close_tab(self, index):
        """关闭标签页"""
        if self.tab_widget.count() > 1:  # 保留至少一个标签页
            self.tab_widget.removeTab(index)
            
    def new_workspace(self):
        """新建工作区"""
        # TODO: 实现新建工作区功能
        self.status_bar.showMessage("新建工作区")
        
    def open_workspace(self):
        """打开工作区"""
        # TODO: 实现打开工作区功能
        self.status_bar.showMessage("打开工作区")
        
    def refresh_data(self):
        """刷新数据"""
        self.status_bar.showMessage("正在刷新数据...")
        # TODO: 实现数据刷新逻辑
        
    def toggle_realtime(self, checked):
        """切换实时数据更新"""
        if checked:
            self.update_timer.start(5000)  # 5秒更新一次
            self.realtime_action.setText('停止实时')
            self.status_bar.showMessage("实时数据更新已开启")
        else:
            self.update_timer.stop()
            self.realtime_action.setText('开始实时')
            self.status_bar.showMessage("实时数据更新已停止")
            
    def update_realtime_data(self):
        """更新实时数据"""
        # TODO: 实现实时数据更新逻辑
        pass
        
    def change_theme(self, theme_name):
        """切换主题"""
        self.theme_manager._apply_theme(self, theme_name)
        self.theme_changed.emit(theme_name)
        self.status_bar.showMessage(f"已切换到{theme_name}主题")
        
    def show_settings(self):
        """显示设置对话框"""
        dialog = SettingsDialog(self)
        dialog.exec()
        
    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(self, "关于", 
                         "A股量化分析系统 v0.1.0\n\n"
                         "专业的股票分析和量化交易平台\n"
                         "参考同花顺iFinder等专业财经软件设计")
        
    def closeEvent(self, event):
        """窗口关闭事件"""
        reply = QMessageBox.question(self, '确认退出', 
                                   '确定要退出程序吗？',
                                   QMessageBox.StandardButton.Yes | 
                                   QMessageBox.StandardButton.No,
                                   QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            # 停止定时器
            if hasattr(self, 'update_timer'):
                self.update_timer.stop()
            event.accept()
        else:
            event.ignore()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())