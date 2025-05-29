#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
主窗口模块
整合各个视图组件，提供应用程序的主界面框架
"""

import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QVBoxLayout, 
                             QWidget, QStatusBar, QToolBar, QMenuBar, QMenu, 
                             QMessageBox, QFileDialog, QDockWidget)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction, QIcon
from pathlib import Path

# 添加项目根目录到系统路径
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

# 导入视图组件
from data_view import DataView
from chart_view import ChartView
from strategy_view import StrategyView
from association_rule_view import AssociationRuleView

# 导入工具模块
import utils.logger as logger
import utils.config_loader as config

class MainWindow(QMainWindow):
    """A股量化分析系统主窗口"""
    
    def __init__(self):
        super().__init__()
        
        # 设置窗口基本属性
        self.setWindowTitle("A股量化分析系统")
        self.setMinimumSize(1200, 800)
        
        # 初始化UI组件
        self.init_ui()
        
        # 连接信号和槽
        self.connect_signals_slots()
        
        # 加载配置
        self.load_config()
        
        # 显示状态栏消息
        self.statusBar().showMessage("系统就绪")
    
    def init_ui(self):
        """初始化UI组件"""
        # 创建中央部件和布局
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # 创建标签页控件
        self.tab_widget = QTabWidget()
        self.main_layout.addWidget(self.tab_widget)
        
        # 创建各个视图
        self.data_view = DataView()
        self.chart_view = ChartView()
        self.strategy_view = StrategyView()
        self.association_rule_view = AssociationRuleView()
        
        # 添加视图到标签页
        self.tab_widget.addTab(self.data_view, "数据浏览")
        self.tab_widget.addTab(self.chart_view, "图表分析")
        self.tab_widget.addTab(self.strategy_view, "策略回测")
        self.tab_widget.addTab(self.association_rule_view, "关联规则挖掘")
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 创建菜单栏
        self.create_menus()
        
        # 创建工具栏
        self.create_toolbars()
    
    def create_menus(self):
        """创建菜单栏"""
        # 文件菜单
        file_menu = self.menuBar().addMenu("文件")
        
        # 退出动作
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 数据菜单
        data_menu = self.menuBar().addMenu("数据")
        
        # 刷新数据动作
        refresh_action = QAction("刷新数据", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.refresh_data)
        data_menu.addAction(refresh_action)
        
        # 导入数据动作
        import_action = QAction("导入数据", self)
        import_action.triggered.connect(self.import_data)
        data_menu.addAction(import_action)
        
        # 导出数据动作
        export_action = QAction("导出数据", self)
        export_action.triggered.connect(self.export_data)
        data_menu.addAction(export_action)
        
        # 分析菜单
        analysis_menu = self.menuBar().addMenu("分析")
        
        # 技术分析动作
        tech_analysis_action = QAction("技术分析", self)
        tech_analysis_action.triggered.connect(self.show_tech_analysis)
        analysis_menu.addAction(tech_analysis_action)
        
        # 基本面分析动作
        fund_analysis_action = QAction("基本面分析", self)
        fund_analysis_action.triggered.connect(self.show_fund_analysis)
        analysis_menu.addAction(fund_analysis_action)
        
        # 市场分析动作
        market_analysis_action = QAction("市场分析", self)
        market_analysis_action.triggered.connect(self.show_market_analysis)
        analysis_menu.addAction(market_analysis_action)
        
        # 策略菜单
        strategy_menu = self.menuBar().addMenu("策略")
        
        # 新建策略动作
        new_strategy_action = QAction("新建策略", self)
        new_strategy_action.triggered.connect(self.create_new_strategy)
        strategy_menu.addAction(new_strategy_action)
        
        # 运行回测动作
        run_backtest_action = QAction("运行回测", self)
        run_backtest_action.triggered.connect(self.run_backtest)
        strategy_menu.addAction(run_backtest_action)
        
        # 帮助菜单
        help_menu = self.menuBar().addMenu("帮助")
        
        # 关于动作
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)
    
    def create_toolbars(self):
        """创建工具栏"""
        # 主工具栏
        main_toolbar = QToolBar("主工具栏")
        main_toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(main_toolbar)
        
        # 添加刷新数据按钮
        refresh_action = QAction("刷新", self)
        refresh_action.setStatusTip("刷新数据")
        refresh_action.triggered.connect(self.refresh_data)
        main_toolbar.addAction(refresh_action)
        
        # 添加分隔符
        main_toolbar.addSeparator()
        
        # 添加技术分析按钮
        tech_analysis_action = QAction("技术分析", self)
        tech_analysis_action.setStatusTip("打开技术分析视图")
        tech_analysis_action.triggered.connect(self.show_tech_analysis)
        main_toolbar.addAction(tech_analysis_action)
        
        # 添加基本面分析按钮
        fund_analysis_action = QAction("基本面", self)
        fund_analysis_action.setStatusTip("打开基本面分析视图")
        fund_analysis_action.triggered.connect(self.show_fund_analysis)
        main_toolbar.addAction(fund_analysis_action)
        
        # 添加分隔符
        main_toolbar.addSeparator()
        
        # 添加运行回测按钮
        run_backtest_action = QAction("回测", self)
        run_backtest_action.setStatusTip("运行策略回测")
        run_backtest_action.triggered.connect(self.run_backtest)
        main_toolbar.addAction(run_backtest_action)
    
    def connect_signals_slots(self):
        """连接信号和槽"""
        # 标签页切换信号
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
    
    def load_config(self):
        """加载配置"""
        # 这里可以添加加载配置的代码
        pass
    
    def on_tab_changed(self, index):
        """标签页切换事件处理"""
        tab_name = self.tab_widget.tabText(index)
        self.statusBar().showMessage(f"当前视图: {tab_name}")
    
    def refresh_data(self):
        """刷新数据"""
        self.statusBar().showMessage("正在刷新数据...")
        # 这里添加刷新数据的代码
        # 根据当前标签页调用相应视图的刷新方法
        current_index = self.tab_widget.currentIndex()
        if current_index == 0:
            self.data_view.refresh_data()
        elif current_index == 1:
            self.chart_view.refresh_data()
        elif current_index == 2:
            self.strategy_view.refresh_data()
        
        self.statusBar().showMessage("数据刷新完成")
    
    def import_data(self):
        """导入数据"""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self, "选择数据文件", "", "CSV文件 (*.csv);;Excel文件 (*.xlsx *.xls);;所有文件 (*)"
        )
        
        if file_path:
            self.statusBar().showMessage(f"正在导入数据: {file_path}")
            # 这里添加导入数据的代码
            self.statusBar().showMessage(f"数据导入完成: {file_path}")
    
    def export_data(self):
        """导出数据"""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getSaveFileName(
            self, "保存数据文件", "", "CSV文件 (*.csv);;Excel文件 (*.xlsx);;所有文件 (*)"
        )
        
        if file_path:
            self.statusBar().showMessage(f"正在导出数据: {file_path}")
            # 这里添加导出数据的代码
            self.statusBar().showMessage(f"数据导出完成: {file_path}")
    
    def show_tech_analysis(self):
        """显示技术分析视图"""
        self.tab_widget.setCurrentIndex(1)  # 切换到图表分析标签页
        self.chart_view.show_tech_analysis()
    
    def show_fund_analysis(self):
        """显示基本面分析视图"""
        self.tab_widget.setCurrentIndex(1)  # 切换到图表分析标签页
        self.chart_view.show_fund_analysis()
    
    def show_market_analysis(self):
        """显示市场分析视图"""
        self.tab_widget.setCurrentIndex(1)  # 切换到图表分析标签页
        self.chart_view.show_market_analysis()
    
    def create_new_strategy(self):
        """创建新策略"""
        self.tab_widget.setCurrentIndex(2)  # 切换到策略回测标签页
        self.strategy_view.create_new_strategy()
    
    def run_backtest(self):
        """运行回测"""
        self.tab_widget.setCurrentIndex(2)  # 切换到策略回测标签页
        self.strategy_view.run_backtest()
    
    def show_about_dialog(self):
        """显示关于对话框"""
        QMessageBox.about(
            self,
            "关于 A股量化分析系统",
            "A股量化分析系统 v1.0\n\n"
            "一个针对中国A股市场的量化分析系统，提供基本数据获取、指标计算、策略选股等功能。\n\n"
            "使用技术：Python, PyQt6, AKShare, PostgreSQL, Redis"
        )


def main():
    """主函数"""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()