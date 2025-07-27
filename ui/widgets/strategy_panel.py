#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
策略面板组件
用于策略管理、回测分析和实时监控
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QTreeWidget, QTreeWidgetItem, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QComboBox, QSpinBox,
    QDateEdit, QTextEdit, QProgressBar, QFrame, QSplitter,
    QGroupBox, QFormLayout, QLineEdit, QCheckBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QDate
from PyQt6.QtGui import QFont, QIcon
import random
from datetime import datetime, timedelta


class StrategyPanel(QWidget):
    """
    策略面板组件
    包含策略管理、回测分析、实时监控等功能
    """
    
    # 信号定义
    strategy_selected = pyqtSignal(str)  # 策略选择信号
    backtest_started = pyqtSignal(dict)  # 回测开始信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_strategy = None
        self.backtest_running = False
        self.init_ui()
        self.setup_timer()
        self.load_sample_strategies()
        
    def init_ui(self):
        """初始化用户界面"""
        # 创建标签页
        self.tab_widget = QTabWidget()
        
        # 策略管理标签页
        self.setup_strategy_management_tab()
        
        # 回测分析标签页
        self.setup_backtest_tab()
        
        # 实时监控标签页
        self.setup_monitor_tab()
        
        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(self.tab_widget)
        
    def setup_strategy_management_tab(self):
        """设置策略管理标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 工具栏
        toolbar_layout = QHBoxLayout()
        
        self.new_strategy_btn = QPushButton("新建策略")
        self.new_strategy_btn.clicked.connect(self.on_new_strategy)
        toolbar_layout.addWidget(self.new_strategy_btn)
        
        self.edit_strategy_btn = QPushButton("编辑策略")
        self.edit_strategy_btn.clicked.connect(self.on_edit_strategy)
        toolbar_layout.addWidget(self.edit_strategy_btn)
        
        self.delete_strategy_btn = QPushButton("删除策略")
        self.delete_strategy_btn.clicked.connect(self.on_delete_strategy)
        toolbar_layout.addWidget(self.delete_strategy_btn)
        
        toolbar_layout.addStretch()
        
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.refresh_strategies)
        toolbar_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(toolbar_layout)
        
        # 策略列表
        self.strategy_tree = QTreeWidget()
        self.strategy_tree.setHeaderLabels(["策略名称", "类型", "状态", "收益率", "最大回撤", "创建时间"])
        self.strategy_tree.itemClicked.connect(self.on_strategy_selected)
        layout.addWidget(self.strategy_tree)
        
        # 策略详情
        self.setup_strategy_details(layout)
        
        self.tab_widget.addTab(tab, "策略管理")
        
    def setup_strategy_details(self, layout):
        """设置策略详情区域"""
        details_group = QGroupBox("策略详情")
        details_layout = QFormLayout(details_group)
        
        self.strategy_name_label = QLabel("--")
        details_layout.addRow("策略名称:", self.strategy_name_label)
        
        self.strategy_type_label = QLabel("--")
        details_layout.addRow("策略类型:", self.strategy_type_label)
        
        self.strategy_description = QTextEdit()
        self.strategy_description.setMaximumHeight(80)
        self.strategy_description.setReadOnly(True)
        details_layout.addRow("策略描述:", self.strategy_description)
        
        self.strategy_params_label = QLabel("--")
        details_layout.addRow("主要参数:", self.strategy_params_label)
        
        layout.addWidget(details_group)
        
    def setup_backtest_tab(self):
        """设置回测分析标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 回测参数设置
        params_group = QGroupBox("回测参数")
        params_layout = QFormLayout(params_group)
        
        # 策略选择
        self.backtest_strategy_combo = QComboBox()
        params_layout.addRow("选择策略:", self.backtest_strategy_combo)
        
        # 股票池
        self.stock_pool_combo = QComboBox()
        self.stock_pool_combo.addItems(["全市场", "沪深300", "中证500", "创业板", "科创板", "自定义"])
        params_layout.addRow("股票池:", self.stock_pool_combo)
        
        # 时间范围
        date_layout = QHBoxLayout()
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addYears(-1))
        self.start_date.setCalendarPopup(True)
        date_layout.addWidget(self.start_date)
        
        date_layout.addWidget(QLabel("至"))
        
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        date_layout.addWidget(self.end_date)
        
        params_layout.addRow("回测期间:", date_layout)
        
        # 初始资金
        self.initial_capital = QSpinBox()
        self.initial_capital.setRange(10000, 10000000)
        self.initial_capital.setValue(1000000)
        self.initial_capital.setSuffix(" 元")
        params_layout.addRow("初始资金:", self.initial_capital)
        
        # 手续费率
        self.commission_rate = QLineEdit("0.0003")
        params_layout.addRow("手续费率:", self.commission_rate)
        
        layout.addWidget(params_group)
        
        # 回测控制
        control_layout = QHBoxLayout()
        
        self.start_backtest_btn = QPushButton("开始回测")
        self.start_backtest_btn.clicked.connect(self.on_start_backtest)
        control_layout.addWidget(self.start_backtest_btn)
        
        self.stop_backtest_btn = QPushButton("停止回测")
        self.stop_backtest_btn.clicked.connect(self.on_stop_backtest)
        self.stop_backtest_btn.setEnabled(False)
        control_layout.addWidget(self.stop_backtest_btn)
        
        control_layout.addStretch()
        
        # 进度条
        self.backtest_progress = QProgressBar()
        control_layout.addWidget(self.backtest_progress)
        
        layout.addLayout(control_layout)
        
        # 回测结果
        self.setup_backtest_results(layout)
        
        self.tab_widget.addTab(tab, "回测分析")
        
    def setup_backtest_results(self, layout):
        """设置回测结果区域"""
        results_group = QGroupBox("回测结果")
        results_layout = QVBoxLayout(results_group)
        
        # 关键指标
        metrics_layout = QHBoxLayout()
        
        # 收益指标
        returns_frame = QFrame()
        returns_frame.setFrameStyle(QFrame.Shape.Box)
        returns_layout = QFormLayout(returns_frame)
        
        self.total_return_label = QLabel("--")
        returns_layout.addRow("总收益率:", self.total_return_label)
        
        self.annual_return_label = QLabel("--")
        returns_layout.addRow("年化收益率:", self.annual_return_label)
        
        self.benchmark_return_label = QLabel("--")
        returns_layout.addRow("基准收益率:", self.benchmark_return_label)
        
        self.alpha_label = QLabel("--")
        returns_layout.addRow("Alpha:", self.alpha_label)
        
        metrics_layout.addWidget(returns_frame)
        
        # 风险指标
        risk_frame = QFrame()
        risk_frame.setFrameStyle(QFrame.Shape.Box)
        risk_layout = QFormLayout(risk_frame)
        
        self.max_drawdown_label = QLabel("--")
        risk_layout.addRow("最大回撤:", self.max_drawdown_label)
        
        self.volatility_label = QLabel("--")
        risk_layout.addRow("波动率:", self.volatility_label)
        
        self.sharpe_ratio_label = QLabel("--")
        risk_layout.addRow("夏普比率:", self.sharpe_ratio_label)
        
        self.win_rate_label = QLabel("--")
        risk_layout.addRow("胜率:", self.win_rate_label)
        
        metrics_layout.addWidget(risk_frame)
        
        results_layout.addLayout(metrics_layout)
        
        # 交易记录表
        self.trades_table = QTableWidget()
        self.trades_table.setColumnCount(8)
        self.trades_table.setHorizontalHeaderLabels([
            "日期", "股票代码", "股票名称", "操作", "价格", "数量", "金额", "收益率"
        ])
        self.trades_table.setMaximumHeight(200)
        results_layout.addWidget(self.trades_table)
        
        layout.addWidget(results_group)
        
    def setup_monitor_tab(self):
        """设置实时监控标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 监控控制
        control_layout = QHBoxLayout()
        
        self.start_monitor_btn = QPushButton("开始监控")
        self.start_monitor_btn.clicked.connect(self.on_start_monitor)
        control_layout.addWidget(self.start_monitor_btn)
        
        self.stop_monitor_btn = QPushButton("停止监控")
        self.stop_monitor_btn.clicked.connect(self.on_stop_monitor)
        self.stop_monitor_btn.setEnabled(False)
        control_layout.addWidget(self.stop_monitor_btn)
        
        control_layout.addStretch()
        
        # 状态指示
        self.monitor_status_label = QLabel("监控状态: 未启动")
        control_layout.addWidget(self.monitor_status_label)
        
        layout.addLayout(control_layout)
        
        # 持仓监控
        positions_group = QGroupBox("当前持仓")
        positions_layout = QVBoxLayout(positions_group)
        
        self.positions_table = QTableWidget()
        self.positions_table.setColumnCount(7)
        self.positions_table.setHorizontalHeaderLabels([
            "股票代码", "股票名称", "持仓数量", "成本价", "当前价", "盈亏", "盈亏比例"
        ])
        positions_layout.addWidget(self.positions_table)
        
        layout.addWidget(positions_group)
        
        # 信号监控
        signals_group = QGroupBox("交易信号")
        signals_layout = QVBoxLayout(signals_group)
        
        self.signals_table = QTableWidget()
        self.signals_table.setColumnCount(6)
        self.signals_table.setHorizontalHeaderLabels([
            "时间", "股票代码", "股票名称", "信号类型", "价格", "强度"
        ])
        signals_layout.addWidget(self.signals_table)
        
        layout.addWidget(signals_group)
        
        self.tab_widget.addTab(tab, "实时监控")
        
    def setup_timer(self):
        """设置定时器"""
        # 回测进度更新定时器
        self.backtest_timer = QTimer()
        self.backtest_timer.timeout.connect(self.update_backtest_progress)
        
        # 实时监控定时器
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self.update_monitor_data)
        
    def load_sample_strategies(self):
        """加载示例策略"""
        strategies = [
            {
                "name": "双均线策略",
                "type": "趋势跟踪",
                "status": "运行中",
                "return": "15.6%",
                "drawdown": "-8.2%",
                "create_time": "2024-01-01",
                "description": "基于5日和20日移动平均线的交叉信号进行买卖操作",
                "params": "短期MA: 5, 长期MA: 20"
            },
            {
                "name": "RSI反转策略",
                "type": "均值回归",
                "status": "已停止",
                "return": "8.3%",
                "drawdown": "-5.1%",
                "create_time": "2024-01-15",
                "description": "利用RSI指标的超买超卖信号进行反向操作",
                "params": "RSI周期: 14, 超买线: 70, 超卖线: 30"
            },
            {
                "name": "MACD金叉策略",
                "type": "趋势跟踪",
                "status": "回测中",
                "return": "12.1%",
                "drawdown": "-6.8%",
                "create_time": "2024-02-01",
                "description": "基于MACD指标的金叉死叉信号进行交易",
                "params": "快线: 12, 慢线: 26, 信号线: 9"
            }
        ]
        
        self.strategy_tree.clear()
        self.backtest_strategy_combo.clear()
        
        for strategy in strategies:
            item = QTreeWidgetItem([
                strategy["name"],
                strategy["type"],
                strategy["status"],
                strategy["return"],
                strategy["drawdown"],
                strategy["create_time"]
            ])
            
            # 保存策略详情
            item.setData(0, Qt.ItemDataRole.UserRole, strategy)
            
            self.strategy_tree.addTopLevelItem(item)
            self.backtest_strategy_combo.addItem(strategy["name"])
            
        # 调整列宽
        for i in range(self.strategy_tree.columnCount()):
            self.strategy_tree.resizeColumnToContents(i)
            
    def on_strategy_selected(self, item, column):
        """策略选择事件"""
        strategy_data = item.data(0, Qt.ItemDataRole.UserRole)
        if strategy_data:
            self.current_strategy = strategy_data
            self.update_strategy_details(strategy_data)
            self.strategy_selected.emit(strategy_data["name"])
            
    def update_strategy_details(self, strategy_data):
        """更新策略详情"""
        self.strategy_name_label.setText(strategy_data["name"])
        self.strategy_type_label.setText(strategy_data["type"])
        self.strategy_description.setText(strategy_data["description"])
        self.strategy_params_label.setText(strategy_data["params"])
        
    def on_new_strategy(self):
        """新建策略"""
        # TODO: 打开策略编辑对话框
        print("新建策略")
        
    def on_edit_strategy(self):
        """编辑策略"""
        if self.current_strategy:
            # TODO: 打开策略编辑对话框
            print(f"编辑策略: {self.current_strategy['name']}")
            
    def on_delete_strategy(self):
        """删除策略"""
        if self.current_strategy:
            # TODO: 确认删除对话框
            print(f"删除策略: {self.current_strategy['name']}")
            
    def refresh_strategies(self):
        """刷新策略列表"""
        self.load_sample_strategies()
        
    def on_start_backtest(self):
        """开始回测"""
        if not self.backtest_running:
            self.backtest_running = True
            self.start_backtest_btn.setEnabled(False)
            self.stop_backtest_btn.setEnabled(True)
            
            # 获取回测参数
            backtest_params = {
                "strategy": self.backtest_strategy_combo.currentText(),
                "stock_pool": self.stock_pool_combo.currentText(),
                "start_date": self.start_date.date().toString("yyyy-MM-dd"),
                "end_date": self.end_date.date().toString("yyyy-MM-dd"),
                "initial_capital": self.initial_capital.value(),
                "commission_rate": float(self.commission_rate.text())
            }
            
            # 发送回测开始信号
            self.backtest_started.emit(backtest_params)
            
            # 开始进度更新
            self.backtest_progress.setValue(0)
            self.backtest_timer.start(100)  # 100ms更新一次
            
    def on_stop_backtest(self):
        """停止回测"""
        if self.backtest_running:
            self.backtest_running = False
            self.start_backtest_btn.setEnabled(True)
            self.stop_backtest_btn.setEnabled(False)
            self.backtest_timer.stop()
            
    def update_backtest_progress(self):
        """更新回测进度"""
        current_value = self.backtest_progress.value()
        if current_value < 100:
            # 模拟进度更新
            new_value = current_value + random.randint(1, 5)
            if new_value > 100:
                new_value = 100
            self.backtest_progress.setValue(new_value)
            
            if new_value == 100:
                # 回测完成
                self.on_backtest_completed()
                
    def on_backtest_completed(self):
        """回测完成"""
        self.backtest_running = False
        self.start_backtest_btn.setEnabled(True)
        self.stop_backtest_btn.setEnabled(False)
        self.backtest_timer.stop()
        
        # 显示回测结果
        self.show_sample_backtest_results()
        
    def show_sample_backtest_results(self):
        """显示示例回测结果"""
        # 更新关键指标
        self.total_return_label.setText("25.6%")
        self.total_return_label.setStyleSheet("color: red; font-weight: bold;")
        
        self.annual_return_label.setText("18.3%")
        self.benchmark_return_label.setText("12.1%")
        self.alpha_label.setText("6.2%")
        
        self.max_drawdown_label.setText("-8.5%")
        self.volatility_label.setText("15.2%")
        self.sharpe_ratio_label.setText("1.35")
        self.win_rate_label.setText("62.5%")
        
        # 添加交易记录
        sample_trades = [
            ["2024-01-15", "600519.SH", "贵州茅台", "买入", "1650.00", "100", "165000", "--"],
            ["2024-01-20", "600519.SH", "贵州茅台", "卖出", "1680.00", "100", "168000", "+1.82%"],
            ["2024-02-01", "000858.SZ", "五粮液", "买入", "180.50", "500", "90250", "--"],
            ["2024-02-10", "000858.SZ", "五粮液", "卖出", "185.20", "500", "92600", "+2.60%"]
        ]
        
        self.trades_table.setRowCount(len(sample_trades))
        for row, trade in enumerate(sample_trades):
            for col, value in enumerate(trade):
                item = QTableWidgetItem(str(value))
                if col == 7 and value.startswith("+"):  # 收益率列
                    item.setForeground(Qt.GlobalColor.red)
                self.trades_table.setItem(row, col, item)
                
    def on_start_monitor(self):
        """开始实时监控"""
        self.start_monitor_btn.setEnabled(False)
        self.stop_monitor_btn.setEnabled(True)
        self.monitor_status_label.setText("监控状态: 运行中")
        self.monitor_status_label.setStyleSheet("color: green;")
        
        # 开始监控定时器
        self.monitor_timer.start(5000)  # 5秒更新一次
        
        # 加载示例持仓数据
        self.load_sample_positions()
        
    def on_stop_monitor(self):
        """停止实时监控"""
        self.start_monitor_btn.setEnabled(True)
        self.stop_monitor_btn.setEnabled(False)
        self.monitor_status_label.setText("监控状态: 已停止")
        self.monitor_status_label.setStyleSheet("color: red;")
        
        # 停止监控定时器
        self.monitor_timer.stop()
        
    def load_sample_positions(self):
        """加载示例持仓数据"""
        positions = [
            ["600519.SH", "贵州茅台", "100", "1650.00", "1680.00", "+3000", "+1.82%"],
            ["000858.SZ", "五粮液", "500", "180.50", "185.20", "+2350", "+2.60%"],
            ["600036.SH", "招商银行", "1000", "42.50", "41.80", "-700", "-1.65%"]
        ]
        
        self.positions_table.setRowCount(len(positions))
        for row, position in enumerate(positions):
            for col, value in enumerate(position):
                item = QTableWidgetItem(str(value))
                if col in [5, 6]:  # 盈亏列
                    if value.startswith("+"):
                        item.setForeground(Qt.GlobalColor.red)
                    elif value.startswith("-"):
                        item.setForeground(Qt.GlobalColor.green)
                self.positions_table.setItem(row, col, item)
                
    def update_monitor_data(self):
        """更新监控数据"""
        # TODO: 更新实时持仓和信号数据
        # 这里可以添加随机信号生成逻辑
        pass