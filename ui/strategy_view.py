#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
策略视图模块
提供策略配置、回测和结果展示功能
参考同花顺iFinder和Winder数据库的专业设计风格
实现高级图表组件、多维度指标分析和专业化交易记录展示
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox, 
                             QPushButton, QLabel, QLineEdit, QGroupBox, 
                             QFormLayout, QSplitter, QTabWidget, QCheckBox,
                             QDateEdit, QSpinBox, QDoubleSpinBox, QToolBar,
                             QFrame, QSizePolicy, QTextEdit, QTableView,
                             QHeaderView, QProgressBar, QRadioButton, QScrollArea,
                             QGridLayout, QTreeWidget, QTreeWidgetItem, QMenu,
                             QStatusBar, QDialog, QFileDialog, QListWidget, QListWidgetItem,
                             QStyledItemDelegate, QCalendarWidget, QStackedWidget, QSlider)
from PyQt6.QtCore import Qt, QDate, pyqtSignal, QSortFilterProxyModel, QDateTime, QTimer, QMargins, QRectF, QPointF
from PyQt6.QtGui import (QStandardItemModel, QStandardItem, QColor, QIcon, QFont, QAction, QCursor,
                      QBrush, QPen, QLinearGradient, QGradient, QPainter, QPainterPath, QPixmap)

# 导入绘图库
import pyqtgraph as pg
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('QtAgg')  # 使用QtAgg后端，它会自动检测Qt版本
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
from matplotlib.gridspec import GridSpec

class MatplotlibCanvas(FigureCanvas):
    """Matplotlib画布类，用于在PyQt6中嵌入Matplotlib图表"""
    
    def __init__(self, parent=None, width=8, height=6, dpi=100):
        """初始化Matplotlib画布
        
        Args:
            parent: 父窗口
            width: 宽度（英寸）
            height: 高度（英寸）
            dpi: 分辨率
        """
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        
        # 先初始化FigureCanvas
        FigureCanvas.__init__(self, self.fig)
        
        # 设置画布属性
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.updateGeometry()
        
        # 最后设置父窗口
        if parent is not None:
            self.setParent(parent)
    
    def clear_plot(self):
        """清除图表"""
        self.axes.clear()
        self.draw()

# 导入技术分析库
import talib as ta
from scipy import stats

# 设置pyqtgraph样式
pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')
pg.setConfigOption('antialias', True)

# 设置matplotlib样式
plt.style.use('ggplot')
plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

# 导入数据处理模块
import datetime
import json
import os
import sys
import math
import pickle
from collections import defaultdict
from typing import Dict, List, Tuple, Union, Optional
from pathlib import Path

# 导入策略工厂
from core.strategy.strategy_factory import strategy_factory

# 添加项目根目录到系统路径
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

class StrategyView(QWidget):
    """策略配置和回测结果展示界面"""
    
    def __init__(self):
        super().__init__()
        
        # 初始化UI组件
        self.init_ui()
        
        # 连接信号和槽
        self.connect_signals_slots()
        
        # 加载初始数据
        self.load_initial_data()
    
    def init_ui(self):
        """初始化UI组件"""
        # 主布局
        main_layout = QVBoxLayout(self)
        
        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # 左侧策略配置面板
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # 策略选择组
        strategy_group = QGroupBox("策略选择")
        strategy_layout = QVBoxLayout()
        
        # 策略类型选择
        strategy_type_layout = QFormLayout()
        self.strategy_type_combo = QComboBox()
        self.strategy_type_combo.addItems(["均线策略", "MACD策略", "KDJ策略", "RSI策略", "布林带策略", "MACD轮动策略", "自定义策略"])
        strategy_type_layout.addRow("策略类型:", self.strategy_type_combo)
        strategy_layout.addLayout(strategy_type_layout)
        
        # 策略参数设置
        params_group = QGroupBox("策略参数")
        self.params_layout = QFormLayout(params_group)
        
        # 添加一些通用参数
        self.stock_code_edit = QLineEdit()
        self.params_layout.addRow("股票代码:", self.stock_code_edit)
        
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QDate.currentDate().addYears(-1))
        self.params_layout.addRow("开始日期:", self.start_date_edit)
        
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QDate.currentDate())
        self.params_layout.addRow("结束日期:", self.end_date_edit)
        
        self.initial_capital_spin = QDoubleSpinBox()
        self.initial_capital_spin.setRange(1000, 10000000)
        self.initial_capital_spin.setValue(100000)
        self.initial_capital_spin.setSingleStep(10000)
        self.params_layout.addRow("初始资金:", self.initial_capital_spin)
        
        # 策略特定参数区域
        self.strategy_params_group = QGroupBox("策略特定参数")
        self.strategy_params_layout = QFormLayout(self.strategy_params_group)
        
        # 默认显示均线策略参数
        self.ma_short_spin = QSpinBox()
        self.ma_short_spin.setRange(1, 120)
        self.ma_short_spin.setValue(5)
        self.strategy_params_layout.addRow("短期均线:", self.ma_short_spin)
        
        self.ma_long_spin = QSpinBox()
        self.ma_long_spin.setRange(5, 250)
        self.ma_long_spin.setValue(20)
        self.strategy_params_layout.addRow("长期均线:", self.ma_long_spin)
        
        # 添加策略参数组到布局
        strategy_layout.addWidget(params_group)
        strategy_layout.addWidget(self.strategy_params_group)
        
        # 操作按钮
        buttons_layout = QHBoxLayout()
        self.run_button = QPushButton("运行回测")
        self.save_button = QPushButton("保存策略")
        self.load_button = QPushButton("加载策略")
        buttons_layout.addWidget(self.run_button)
        buttons_layout.addWidget(self.save_button)
        buttons_layout.addWidget(self.load_button)
        strategy_layout.addLayout(buttons_layout)
        
        # 设置策略组布局
        strategy_group.setLayout(strategy_layout)
        left_layout.addWidget(strategy_group)
        
        # 右侧结果展示面板
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # 创建结果标签页
        result_tab = QTabWidget()
        
        # 回测结果概览标签页
        overview_tab = QWidget()
        overview_layout = QVBoxLayout(overview_tab)
        
        # 回测进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        overview_layout.addWidget(self.progress_bar)
        
        # 回测结果概览表格
        self.overview_table = QTableView()
        self.overview_table.setAlternatingRowColors(True)
        self.overview_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        overview_layout.addWidget(self.overview_table)
        
        # 回测结果图表标签页
        chart_tab = QWidget()
        chart_layout = QVBoxLayout(chart_tab)
        
        # 创建回测结果图表
        self.result_plot = pg.PlotWidget()
        self.result_plot.setLabel('left', '价值')
        self.result_plot.setLabel('bottom', '日期')
        self.result_plot.showGrid(x=True, y=True)
        chart_layout.addWidget(self.result_plot)
        
        # 创建收益率图表
        self.return_plot = pg.PlotWidget()
        self.return_plot.setLabel('left', '收益率(%)')
        self.return_plot.setLabel('bottom', '日期')
        self.return_plot.showGrid(x=True, y=True)
        chart_layout.addWidget(self.return_plot)
        
        # 设置图表比例
        chart_layout.setStretchFactor(self.result_plot, 7)
        chart_layout.setStretchFactor(self.return_plot, 3)
        
        # 交易记录标签页
        trades_tab = QWidget()
        trades_layout = QVBoxLayout(trades_tab)
        
        # 交易记录表格
        self.trades_table = QTableView()
        self.trades_table.setAlternatingRowColors(True)
        self.trades_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        trades_layout.addWidget(self.trades_table)
        
        # 添加标签页
        result_tab.addTab(overview_tab, "回测概览")
        result_tab.addTab(chart_tab, "回测图表")
        result_tab.addTab(trades_tab, "交易记录")
        
        # 添加结果标签页到右侧布局
        right_layout.addWidget(result_tab)
        
        # 添加左右面板到分割器
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        
        # 设置分割器初始大小
        splitter.setSizes([400, 800])
    
    def connect_signals_slots(self):
        """连接信号和槽"""
        # 策略类型变化事件
        self.strategy_type_combo.currentIndexChanged.connect(self.on_strategy_type_changed)
        
        # 运行回测按钮点击事件
        self.run_button.clicked.connect(self.run_backtest)
        
        # 保存策略按钮点击事件
        self.save_button.clicked.connect(self.save_strategy)
        
        # 加载策略按钮点击事件
        self.load_button.clicked.connect(self.load_strategy)
    
    def load_initial_data(self):
        """加载初始数据"""
        # 设置默认股票代码
        self.stock_code_edit.setText("000001")
        
        # 初始化结果表格模型
        self.init_table_models()
        
        # 生成示例回测结果
        self.generate_sample_results()
    
    def init_table_models(self):
        """初始化表格模型"""
        # 初始化概览表格模型
        self.overview_model = QStandardItemModel()
        self.overview_model.setHorizontalHeaderLabels(["指标", "数值"])
        self.overview_table.setModel(self.overview_model)
        
        # 初始化交易记录表格模型
        self.trades_model = QStandardItemModel()
        self.trades_model.setHorizontalHeaderLabels(["日期", "交易类型", "价格", "数量", "交易额", "手续费", "剩余资金"])
        self.trades_table.setModel(self.trades_model)
    
    def on_strategy_type_changed(self, index):
        """策略类型变化事件处理"""
        # 清空策略特定参数布局
        while self.strategy_params_layout.rowCount() > 0:
            self.strategy_params_layout.removeRow(0)
        
        # 根据选择的策略类型添加不同的参数
        strategy_type = self.strategy_type_combo.currentText()
        
        if strategy_type == "均线策略":
            # 添加均线策略参数
            self.ma_short_spin = QSpinBox()
            self.ma_short_spin.setRange(1, 120)
            self.ma_short_spin.setValue(5)
            self.strategy_params_layout.addRow("短期均线:", self.ma_short_spin)
            
            self.ma_long_spin = QSpinBox()
            self.ma_long_spin.setRange(5, 250)
            self.ma_long_spin.setValue(20)
            self.strategy_params_layout.addRow("长期均线:", self.ma_long_spin)
        
        elif strategy_type == "MACD策略":
            # 添加MACD策略参数
            self.macd_fast_spin = QSpinBox()
            self.macd_fast_spin.setRange(1, 120)
            self.macd_fast_spin.setValue(12)
            self.strategy_params_layout.addRow("快线周期:", self.macd_fast_spin)
            
            self.macd_slow_spin = QSpinBox()
            self.macd_slow_spin.setRange(5, 250)
            self.macd_slow_spin.setValue(26)
            self.strategy_params_layout.addRow("慢线周期:", self.macd_slow_spin)
            
            self.macd_signal_spin = QSpinBox()
            self.macd_signal_spin.setRange(1, 50)
            self.macd_signal_spin.setValue(9)
            self.strategy_params_layout.addRow("信号周期:", self.macd_signal_spin)
            
        elif strategy_type == "MACD轮动策略":
            # 添加MACD轮动策略参数
            # MACD参数
            self.macd_fast_spin = QSpinBox()
            self.macd_fast_spin.setRange(1, 120)
            self.macd_fast_spin.setValue(12)
            self.strategy_params_layout.addRow("快线周期:", self.macd_fast_spin)
            
            self.macd_slow_spin = QSpinBox()
            self.macd_slow_spin.setRange(5, 250)
            self.macd_slow_spin.setValue(26)
            self.strategy_params_layout.addRow("慢线周期:", self.macd_slow_spin)
            
            self.macd_signal_spin = QSpinBox()
            self.macd_signal_spin.setRange(1, 50)
            self.macd_signal_spin.setValue(9)
            self.strategy_params_layout.addRow("信号周期:", self.macd_signal_spin)
            
            # 轮动参数
            self.stock_pool_edit = QLineEdit()
            self.stock_pool_edit.setPlaceholderText("000001,000002,000063,000333,000651")
            self.strategy_params_layout.addRow("股票池(逗号分隔):", self.stock_pool_edit)
            
            self.max_positions_spin = QSpinBox()
            self.max_positions_spin.setRange(1, 20)
            self.max_positions_spin.setValue(3)
            self.strategy_params_layout.addRow("最大持仓数:", self.max_positions_spin)
            
            self.rotation_period_spin = QSpinBox()
            self.rotation_period_spin.setRange(1, 60)
            self.rotation_period_spin.setValue(5)
            self.strategy_params_layout.addRow("轮动周期(天):", self.rotation_period_spin)
            
            self.weight_combo = QComboBox()
            self.weight_combo.addItems(["等权重", "MACD强度"])
            self.strategy_params_layout.addRow("持仓权重:", self.weight_combo)
            
            self.rotation_condition_combo = QComboBox()
            self.rotation_condition_combo.addItems(["定期轮动", "信号触发"])
            self.strategy_params_layout.addRow("轮动条件:", self.rotation_condition_combo)
            
            self.macd_threshold_spin = QDoubleSpinBox()
            self.macd_threshold_spin.setRange(0, 10)
            self.macd_threshold_spin.setSingleStep(0.1)
            self.macd_threshold_spin.setValue(0.5)
            self.strategy_params_layout.addRow("MACD阈值:", self.macd_threshold_spin)
        
        elif strategy_type == "KDJ策略":
            # 添加KDJ策略参数
            self.kdj_n_spin = QSpinBox()
            self.kdj_n_spin.setRange(1, 50)
            self.kdj_n_spin.setValue(9)
            self.strategy_params_layout.addRow("N周期:", self.kdj_n_spin)
            
            self.kdj_m1_spin = QSpinBox()
            self.kdj_m1_spin.setRange(1, 20)
            self.kdj_m1_spin.setValue(3)
            self.strategy_params_layout.addRow("M1周期:", self.kdj_m1_spin)
            
            self.kdj_m2_spin = QSpinBox()
            self.kdj_m2_spin.setRange(1, 20)
            self.kdj_m2_spin.setValue(3)
            self.strategy_params_layout.addRow("M2周期:", self.kdj_m2_spin)
        
        elif strategy_type == "RSI策略":
            # 添加RSI策略参数
            self.rsi_period_spin = QSpinBox()
            self.rsi_period_spin.setRange(1, 50)
            self.rsi_period_spin.setValue(14)
            self.strategy_params_layout.addRow("RSI周期:", self.rsi_period_spin)
            
            self.rsi_upper_spin = QSpinBox()
            self.rsi_upper_spin.setRange(50, 90)
            self.rsi_upper_spin.setValue(70)
            self.strategy_params_layout.addRow("超买阈值:", self.rsi_upper_spin)
            
            self.rsi_lower_spin = QSpinBox()
            self.rsi_lower_spin.setRange(10, 50)
            self.rsi_lower_spin.setValue(30)
            self.strategy_params_layout.addRow("超卖阈值:", self.rsi_lower_spin)
        
        elif strategy_type == "布林带策略":
            # 添加布林带策略参数
            self.boll_period_spin = QSpinBox()
            self.boll_period_spin.setRange(1, 50)
            self.boll_period_spin.setValue(20)
            self.strategy_params_layout.addRow("周期:", self.boll_period_spin)
            
            self.boll_std_spin = QDoubleSpinBox()
            self.boll_std_spin.setRange(0.5, 5.0)
            self.boll_std_spin.setValue(2.0)
            self.boll_std_spin.setSingleStep(0.1)
            self.strategy_params_layout.addRow("标准差倍数:", self.boll_std_spin)
        
        elif strategy_type == "自定义策略":
            # 添加自定义策略参数
            self.strategy_code_edit = QTextEdit()
            self.strategy_code_edit.setPlaceholderText("在这里输入自定义策略代码...")
            self.strategy_params_layout.addRow("策略代码:", self.strategy_code_edit)
    
    def generate_sample_results(self):
        """生成示例回测结果"""
        # 生成日期序列
        dates = pd.date_range(start='2023-01-01', periods=252, freq='B')
        
        # 生成资金曲线
        np.random.seed(42)
        initial_value = 100000
        daily_returns = np.random.normal(0.0005, 0.01, len(dates))
        cumulative_returns = np.cumprod(1 + daily_returns)
        portfolio_value = initial_value * cumulative_returns
        
        # 生成基准曲线
        benchmark_returns = np.random.normal(0.0003, 0.012, len(dates))
        benchmark_cumulative = np.cumprod(1 + benchmark_returns)
        benchmark_value = initial_value * benchmark_cumulative
        
        # 创建回测结果DataFrame
        self.backtest_results = pd.DataFrame({
            '日期': dates,
            '策略价值': portfolio_value,
            '基准价值': benchmark_value,
            '策略收益率': daily_returns * 100,
            '基准收益率': benchmark_returns * 100
        })
        
        # 生成交易记录
        trade_dates = np.random.choice(dates, 20, replace=False)
        trade_dates.sort()
        
        trade_types = []
        prices = []
        quantities = []
        amounts = []
        fees = []
        remaining = []
        
        cash = initial_value
        position = 0
        
        for i, date in enumerate(trade_dates):
            idx = np.where(dates == date)[0][0]
            price = portfolio_value[idx] / 100  # 假设价格
            
            if i % 2 == 0:  # 买入
                quantity = int(cash * 0.4 / price)
                amount = quantity * price
                fee = amount * 0.0003
                cash -= (amount + fee)
                position += quantity
                trade_types.append("买入")
            else:  # 卖出
                quantity = int(position * 0.5)
                amount = quantity * price
                fee = amount * 0.0003
                cash += (amount - fee)
                position -= quantity
                trade_types.append("卖出")
            
            prices.append(price)
            quantities.append(quantity)
            amounts.append(amount)
            fees.append(fee)
            remaining.append(cash)
        
        # 创建交易记录DataFrame
        self.trade_records = pd.DataFrame({
            '日期': trade_dates,
            '交易类型': trade_types,
            '价格': prices,
            '数量': quantities,
            '交易额': amounts,
            '手续费': fees,
            '剩余资金': remaining
        })
        
        # 更新概览表格
        self.update_overview_table()
        
        # 更新交易记录表格
        self.update_trades_table()
        
        # 绘制回测结果图表
        self.plot_backtest_results()
    
    def update_overview_table(self):
        """更新概览表格"""
        # 清空表格
        self.overview_model.removeRows(0, self.overview_model.rowCount())
        
        # 计算回测指标
        initial_value = self.backtest_results['策略价值'].iloc[0]
        final_value = self.backtest_results['策略价值'].iloc[-1]
        total_return = (final_value / initial_value - 1) * 100
        annual_return = total_return / (len(self.backtest_results) / 252) 
        
        # 计算最大回撤
        portfolio_value = self.backtest_results['策略价值'].values
        max_drawdown = 0
        peak = portfolio_value[0]
        
        for value in portfolio_value:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # 计算夏普比率
        daily_returns = self.backtest_results['策略收益率'].values / 100
        sharpe_ratio = np.sqrt(252) * np.mean(daily_returns) / np.std(daily_returns)
        
        # 添加指标到表格
        metrics = [
            ("初始资金", f"{initial_value:.2f}"),
            ("最终资金", f"{final_value:.2f}"),
            ("总收益率", f"{total_return:.2f}%"),
            ("年化收益率", f"{annual_return:.2f}%"),
            ("最大回撤", f"{max_drawdown:.2f}%"),
            ("夏普比率", f"{sharpe_ratio:.2f}"),
            ("交易次数", str(len(self.trade_records))),
            ("胜率", "55.00%"),  # 示例数据
            ("盈亏比", "1.5")  # 示例数据
        ]
        
        for metric, value in metrics:
            self.overview_model.appendRow([QStandardItem(metric), QStandardItem(value)])
    
    def update_trades_table(self):
        """更新交易记录表格"""
        # 清空表格
        self.trades_model.removeRows(0, self.trades_model.rowCount())
        
        # 添加交易记录到表格
        for i in range(len(self.trade_records)):
            date = QStandardItem(self.trade_records['日期'].iloc[i].strftime('%Y-%m-%d'))
            trade_type = QStandardItem(self.trade_records['交易类型'].iloc[i])
            price = QStandardItem(f"{self.trade_records['价格'].iloc[i]:.2f}")
            quantity = QStandardItem(str(self.trade_records['数量'].iloc[i]))
            amount = QStandardItem(f"{self.trade_records['交易额'].iloc[i]:.2f}")
            fee = QStandardItem(f"{self.trade_records['手续费'].iloc[i]:.2f}")
            remaining = QStandardItem(f"{self.trade_records['剩余资金'].iloc[i]:.2f}")
            
            # 设置颜色
            if self.trade_records['交易类型'].iloc[i] == "买入":
                trade_type.setForeground(QColor('red'))
            else:
                trade_type.setForeground(QColor('green'))
            
            self.trades_model.appendRow([date, trade_type, price, quantity, amount, fee, remaining])
    
    def plot_backtest_results(self):
        """绘制回测结果图表"""
        # 清空图表
        self.result_plot.clear()
        self.return_plot.clear()
        
        # 获取数据
        dates = np.arange(len(self.backtest_results))
        portfolio_value = self.backtest_results['策略价值'].values
        benchmark_value = self.backtest_results['基准价值'].values
        portfolio_returns = self.backtest_results['策略收益率'].values
        benchmark_returns = self.backtest_results['基准收益率'].values
        
        # 绘制资金曲线
        self.result_plot.plot(dates, portfolio_value, pen=pg.mkPen('r', width=2), name="策略")
        self.result_plot.plot(dates, benchmark_value, pen=pg.mkPen('b', width=2), name="基准")
        
        # 添加图例
        legend = pg.LegendItem((80, 60), offset=(70, 20))
        legend.setParentItem(self.result_plot.graphicsItem())
        legend.addItem(pg.PlotDataItem(pen=pg.mkPen('r', width=2)), "策略")
        legend.addItem(pg.PlotDataItem(pen=pg.mkPen('b', width=2)), "基准")
        
        # 绘制收益率曲线
        self.return_plot.plot(dates, portfolio_returns, pen=pg.mkPen('r', width=1), name="策略收益率")
        self.return_plot.plot(dates, benchmark_returns, pen=pg.mkPen('b', width=1), name="基准收益率")
        
        # 设置X轴刻度
        date_strings = [d.strftime('%Y-%m-%d') for d in self.backtest_results['日期']]
        ticks = []
        for i, date_str in enumerate(date_strings):
            if i % 21 == 0:  # 每月显示一个日期标签
                ticks.append((i, date_str))
        
        self.result_plot.getAxis('bottom').setTicks([ticks])
        self.return_plot.getAxis('bottom').setTicks([ticks])
    
    def run_backtest(self):
        """运行回测"""
        # 获取策略参数
        strategy_type = self.strategy_type_combo.currentText()
        stock_code = self.stock_code_edit.text()
        start_date = self.start_date_edit.date().toString("yyyy-MM-dd")
        end_date = self.end_date_edit.date().toString("yyyy-MM-dd")
        initial_capital = self.initial_capital_spin.value()
        
        # 创建策略参数字典
        strategy_params = {
            '股票代码': stock_code,
            '开始日期': start_date,
            '结束日期': end_date,
            '初始资金': initial_capital
        }
        
        # 根据策略类型添加特定参数
        if strategy_type == "均线策略":
            strategy_params.update({
                '短期均线': self.ma_short_spin.value(),
                '长期均线': self.ma_long_spin.value()
            })
        elif strategy_type == "MACD策略":
            strategy_params.update({
                'MACD快线': self.macd_fast_spin.value(),
                'MACD慢线': self.macd_slow_spin.value(),
                'MACD信号线': self.macd_signal_spin.value()
            })
        elif strategy_type == "KDJ策略":
            strategy_params.update({
                'KDJ_N': self.kdj_n_spin.value(),
                'KDJ_M1': self.kdj_m1_spin.value(),
                'KDJ_M2': self.kdj_m2_spin.value()
            })
        elif strategy_type == "RSI策略":
            strategy_params.update({
                'RSI周期': self.rsi_period_spin.value(),
                'RSI上限': self.rsi_upper_spin.value(),
                'RSI下限': self.rsi_lower_spin.value()
            })
        elif strategy_type == "布林带策略":
            strategy_params.update({
                '布林带周期': self.boll_period_spin.value(),
                '布林带标准差': self.boll_std_spin.value()
            })
        elif strategy_type == "MACD轮动策略":
            # 处理股票池字符串，转换为列表
            stock_pool_str = self.stock_pool_edit.text().strip()
            stock_pool = [code.strip() for code in stock_pool_str.split(',')] if stock_pool_str else []
            
            strategy_params.update({
                'MACD快线': self.macd_fast_spin.value(),
                'MACD慢线': self.macd_slow_spin.value(),
                'MACD信号线': self.macd_signal_spin.value(),
                '股票池': stock_pool,
                '最大持仓数': self.max_positions_spin.value(),
                '轮动周期': self.rotation_period_spin.value(),
                '持仓权重': 'equal' if self.weight_combo.currentText() == "等权重" else 'macd',
                '轮动条件': 'regular' if self.rotation_condition_combo.currentText() == "定期轮动" else 'signal',
                'MACD阈值': self.macd_threshold_spin.value()
            })
        elif strategy_type == "自定义策略":
            # 处理自定义策略代码
            strategy_params['策略代码'] = self.strategy_code_edit.toPlainText()
        
        # 使用策略工厂创建策略实例并运行回测
        try:
            # 创建策略实例
            strategy = strategy_factory.create_strategy(strategy_type, strategy_params)
            
            # 这里应该添加实际的回测逻辑
            # 实际应用中，应该使用线程或QThread来避免UI冻结
            # backtest_results = strategy.run_backtest()
            
            # 记录策略创建成功
            print(f"策略创建成功: {strategy_type}")
        except Exception as e:
            print(f"策略创建失败: {e}")
            return
        
        # 模拟回测进度
        self.progress_bar.setValue(0)
        for i in range(101):
            # 在实际应用中，这里应该是实际的回测进度
            self.progress_bar.setValue(i)
            # 实际应用中应该使用QTimer或线程来避免UI冻结
        
        # 生成新的示例回测结果
        self.generate_sample_results()
        
        # 显示回测完成消息
        self.progress_bar.setValue(100)
        print(f"运行回测: {strategy_type}, 参数: {strategy_params}")
    
    def save_strategy(self):
        """保存策略"""
        # 获取策略参数
        strategy_type = self.strategy_type_combo.currentText()
        stock_code = self.stock_code_edit.text()
        start_date = self.start_date_edit.date().toString("yyyy-MM-dd")
        end_date = self.end_date_edit.date().toString("yyyy-MM-dd")
        initial_capital = self.initial_capital_spin.value()
        
        # 创建策略参数字典
        strategy_params = {
            '股票代码': stock_code,
            '开始日期': start_date,
            '结束日期': end_date,
            '初始资金': initial_capital
        }
        
        # 根据策略类型添加特定参数
        if strategy_type == "均线策略":
            strategy_params.update({
                '短期均线': self.ma_short_spin.value(),
                '长期均线': self.ma_long_spin.value()
            })
        elif strategy_type == "MACD策略":
            strategy_params.update({
                'MACD快线': self.macd_fast_spin.value(),
                'MACD慢线': self.macd_slow_spin.value(),
                'MACD信号线': self.macd_signal_spin.value()
            })
        elif strategy_type == "KDJ策略":
            strategy_params.update({
                'KDJ_N': self.kdj_n_spin.value(),
                'KDJ_M1': self.kdj_m1_spin.value(),
                'KDJ_M2': self.kdj_m2_spin.value()
            })
        elif strategy_type == "RSI策略":
            strategy_params.update({
                'RSI周期': self.rsi_period_spin.value(),
                'RSI上限': self.rsi_upper_spin.value(),
                'RSI下限': self.rsi_lower_spin.value()
            })
        elif strategy_type == "布林带策略":
            strategy_params.update({
                '布林带周期': self.boll_period_spin.value(),
                '布林带标准差': self.boll_std_spin.value()
            })
        elif strategy_type == "MACD轮动策略":
            # 处理股票池字符串，转换为列表
            stock_pool_str = self.stock_pool_edit.text().strip()
            stock_pool = [code.strip() for code in stock_pool_str.split(',')] if stock_pool_str else []
            
            strategy_params.update({
                'MACD快线': self.macd_fast_spin.value(),
                'MACD慢线': self.macd_slow_spin.value(),
                'MACD信号线': self.macd_signal_spin.value(),
                '股票池': stock_pool,
                '最大持仓数': self.max_positions_spin.value(),
                '轮动周期': self.rotation_period_spin.value(),
                '持仓权重': 'equal' if self.weight_combo.currentText() == "等权重" else 'macd',
                '轮动条件': 'regular' if self.rotation_condition_combo.currentText() == "定期轮动" else 'signal',
                'MACD阈值': self.macd_threshold_spin.value()
            })
        elif strategy_type == "自定义策略":
            # 处理自定义策略代码
            strategy_params['策略代码'] = self.strategy_code_edit.toPlainText()
        
        # 使用策略工厂保存策略配置
        try:
            # 创建策略实例
            strategy = strategy_factory.create_strategy(strategy_type, strategy_params)
            
            # 保存策略配置
            file_path = strategy_factory.save_strategy_config(strategy)
            
            # 显示保存成功消息
            print(f"策略已保存到: {file_path}")
        except Exception as e:
            print(f"保存策略失败: {e}")
            return
        
        # 显示保存成功消息
        print(f"策略已保存: {strategy_type}, 参数: {strategy_params}")
    
    def load_strategy(self):
        """加载策略"""
        # 打开文件对话框选择策略配置文件
        file_dialog = QFileDialog(self)
        file_dialog.setNameFilter("策略配置文件 (*.json)")
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        
        if file_dialog.exec():
            file_paths = file_dialog.selectedFiles()
            if file_paths:
                file_path = file_paths[0]
                
                # 这里应该添加加载策略的代码
                # 例如，使用策略工厂加载策略配置
                # from core.strategy.strategy_factory import strategy_factory
                # strategy = strategy_factory.load_strategy_config(file_path)
                # strategy_params = strategy.params
                
                # 模拟加载策略参数
                # 实际应用中，应该从加载的策略对象中获取参数
                import json
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        strategy_data = json.load(f)
                    
                    strategy_params = strategy_data.get('params', {})
                    strategy_type = strategy_data.get('name', '')
                    
                    # 设置策略类型
                    index = self.strategy_type_combo.findText(strategy_type)
                    if index >= 0:
                        self.strategy_type_combo.setCurrentIndex(index)
                    
                    # 设置通用参数
                    self.stock_code_edit.setText(strategy_params.get('股票代码', ''))
                    
                    # 设置日期
                    start_date = strategy_params.get('开始日期', '')
                    if start_date:
                        self.start_date_edit.setDate(QDate.fromString(start_date, "yyyy-MM-dd"))
                    
                    end_date = strategy_params.get('结束日期', '')
                    if end_date:
                        self.end_date_edit.setDate(QDate.fromString(end_date, "yyyy-MM-dd"))
                    
                    # 设置初始资金
                    self.initial_capital_spin.setValue(strategy_params.get('初始资金', 100000))
                    
                    # 根据策略类型设置特定参数
                    if strategy_type == "均线策略":
                        self.ma_short_spin.setValue(strategy_params.get('短期均线', 5))
                        self.ma_long_spin.setValue(strategy_params.get('长期均线', 20))
                    
                    elif strategy_type == "MACD策略":
                        self.macd_fast_spin.setValue(strategy_params.get('MACD快线', 12))
                        self.macd_slow_spin.setValue(strategy_params.get('MACD慢线', 26))
                        self.macd_signal_spin.setValue(strategy_params.get('MACD信号线', 9))
                    
                    elif strategy_type == "KDJ策略":
                        self.kdj_n_spin.setValue(strategy_params.get('KDJ_N', 9))
                        self.kdj_m1_spin.setValue(strategy_params.get('KDJ_M1', 3))
                        self.kdj_m2_spin.setValue(strategy_params.get('KDJ_M2', 3))
                    
                    elif strategy_type == "RSI策略":
                        self.rsi_period_spin.setValue(strategy_params.get('RSI周期', 14))
                        self.rsi_upper_spin.setValue(strategy_params.get('RSI上限', 70))
                        self.rsi_lower_spin.setValue(strategy_params.get('RSI下限', 30))
                    
                    elif strategy_type == "布林带策略":
                        self.boll_period_spin.setValue(strategy_params.get('布林带周期', 20))
                        self.boll_std_spin.setValue(strategy_params.get('布林带标准差', 2.0))
                    
                    elif strategy_type == "MACD轮动策略":
                        # 设置MACD参数
                        self.macd_fast_spin.setValue(strategy_params.get('MACD快线', 12))
                        self.macd_slow_spin.setValue(strategy_params.get('MACD慢线', 26))
                        self.macd_signal_spin.setValue(strategy_params.get('MACD信号线', 9))
                        
                        # 设置股票池
                        stock_pool = strategy_params.get('股票池', [])
                        self.stock_pool_edit.setText(','.join(stock_pool))
                        
                        # 设置轮动参数
                        self.max_positions_spin.setValue(strategy_params.get('最大持仓数', 3))
                        self.rotation_period_spin.setValue(strategy_params.get('轮动周期', 5))
                        
                        # 设置持仓权重
                        weight_index = 0 if strategy_params.get('持仓权重', 'equal') == 'equal' else 1
                        self.weight_combo.setCurrentIndex(weight_index)
                        
                        # 设置轮动条件
                        condition_index = 0 if strategy_params.get('轮动条件', 'regular') == 'regular' else 1
                        self.rotation_condition_combo.setCurrentIndex(condition_index)
                        
                        # 设置MACD阈值
                        self.macd_threshold_spin.setValue(strategy_params.get('MACD阈值', 0.5))
                    
                    elif strategy_type == "自定义策略":
                        # 设置自定义策略代码
                        self.strategy_code_edit.setPlainText(strategy_params.get('策略代码', ''))
                    
                    # 显示加载成功消息
                    print(f"策略已加载: {strategy_type}, 参数: {strategy_params}")
                
                except Exception as e:
                    print(f"加载策略失败: {e}")
        else:
            print("取消加载策略")


if __name__ == "__main__":
    # 测试代码
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = StrategyView()
    window.show()
    sys.exit(app.exec())