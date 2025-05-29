#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
图表视图模块
提供各种图表展示功能，包括K线图、技术指标图、基本面分析图等
参考同花顺iFinder和Winder的专业设计风格
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox, 
                             QPushButton, QLabel, QLineEdit, QGroupBox, 
                             QFormLayout, QSplitter, QTabWidget, QCheckBox,
                             QDateEdit, QSpinBox, QDoubleSpinBox, QToolBar,
                             QFrame, QSizePolicy, QProgressBar, QMessageBox,
                             QStatusBar)
from PyQt6.QtCore import Qt, QDate, pyqtSignal, QThread
from PyQt6.QtGui import QColor

# 导入绘图库
import pyqtgraph as pg
import numpy as np
import pandas as pd
import datetime
import traceback
import sys
from pathlib import Path

# 添加项目根目录到系统路径
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

# 导入数据库管理器
from data.storage.postgresql_manager import PostgreSQLManager
from data.storage.redis_manager import RedisManager

# 导入akshare数据获取模块
import akshare as ak

# 设置pyqtgraph样式
pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')
pg.setConfigOption('antialias', True)  # 抗锯齿

class ChartDataLoaderThread(QThread):
    """图表数据加载线程，用于异步加载数据，避免界面卡顿"""
    
    # 定义信号
    data_loaded = pyqtSignal(pd.DataFrame)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(int)
    
    def __init__(self, data_type, stock_code, start_date, end_date):
        super().__init__()
        self.data_type = data_type  # K线图、技术指标、基本面等
        self.stock_code = stock_code
        self.start_date = start_date
        self.end_date = end_date
        self.pg_manager = None
        self.redis_manager = None
    
    def run(self):
        """线程运行函数"""
        try:
            # 连接数据库
            self.pg_manager = PostgreSQLManager()
            self.redis_manager = RedisManager()
            
            # 发送进度信号
            self.progress_updated.emit(10)
            
            # 根据数据类型获取数据
            if self.data_type == "K线图" or self.data_type == "技术指标":
                df = self.get_kline_data()
            elif self.data_type == "基本面":
                df = self.get_fundamental_data()
            elif self.data_type == "市场热度":
                df = self.get_market_data()
            else:
                df = pd.DataFrame()
            
            # 发送进度信号
            self.progress_updated.emit(90)
            
            # 发送数据加载完成信号
            self.data_loaded.emit(df)
            
            # 发送进度信号
            self.progress_updated.emit(100)
            
        except Exception as e:
            # 发送错误信号
            error_msg = f"数据加载错误: {str(e)}\n{traceback.format_exc()}"
            self.error_occurred.emit(error_msg)
        finally:
            # 关闭数据库连接
            if self.pg_manager:
                self.pg_manager.close()
            if self.redis_manager:
                self.redis_manager.close()
    
    def get_kline_data(self):
        """获取K线数据"""
        # 检查Redis缓存
        cache_key = f"kline:{self.stock_code}:{self.start_date}:{self.end_date}"
        cached_data = self.redis_manager.get_value(cache_key)
        if cached_data is not None:
            return cached_data
        
        # 从PostgreSQL获取数据
        sql = f"""SELECT * FROM \"股票日线行情\" 
               WHERE \"股票代码\" = '{self.stock_code}' """
        
        if self.start_date and self.end_date:
            sql += f"AND \"交易日期\" BETWEEN '{self.start_date}' AND '{self.end_date}' "
        
        sql += "ORDER BY \"交易日期\" ASC"
        
        df = self.pg_manager.query_df(sql)
        
        # 如果数据库中没有数据，则从akshare获取
        if df.empty:
            try:
                # 发送进度信号
                self.progress_updated.emit(30)
                
                # 使用akshare获取股票日线数据
                df = ak.stock_zh_a_hist(symbol=self.stock_code, start_date=self.start_date, end_date=self.end_date)
                
                # 发送进度信号
                self.progress_updated.emit(60)
                
                # 重命名列以符合中文命名规范
                df.columns = ["交易日期", "开盘价", "最高价", "最低价", "收盘价", "涨跌幅", "成交量", "成交额", "振幅", "换手率"]
                # 添加股票代码列
                df["股票代码"] = self.stock_code
                
                # 保存到数据库
                self.pg_manager.create_table("股票日线行情", {
                    "股票代码": "VARCHAR(10) NOT NULL",
                    "交易日期": "DATE NOT NULL",
                    "开盘价": "NUMERIC(10,2)",
                    "最高价": "NUMERIC(10,2)",
                    "最低价": "NUMERIC(10,2)",
                    "收盘价": "NUMERIC(10,2)",
                    "涨跌幅": "NUMERIC(10,2)",
                    "成交量": "NUMERIC(20,0)",
                    "成交额": "NUMERIC(20,2)",
                    "振幅": "NUMERIC(10,2)",
                    "换手率": "NUMERIC(10,2)",
                    "PRIMARY KEY": "(股票代码, 交易日期)"
                })
                self.pg_manager.insert_df("股票日线行情", df)
                
                # 发送进度信号
                self.progress_updated.emit(80)
            except Exception as e:
                print(f"获取股票日线行情失败: {e}")
                return pd.DataFrame()
        
        # 缓存数据到Redis
        if not df.empty:
            self.redis_manager.set_value(cache_key, df, expire=3600)  # 缓存1小时
        
        return df
    
    def get_fundamental_data(self):
        """获取基本面数据"""
        # 检查Redis缓存
        cache_key = f"fundamental:{self.stock_code}"
        cached_data = self.redis_manager.get_value(cache_key)
        if cached_data is not None:
            return cached_data
        
        # 从PostgreSQL获取数据
        sql = f"""SELECT * FROM \"股票财务数据\" 
               WHERE \"股票代码\" = '{self.stock_code}' 
               ORDER BY \"报告期\" ASC"""
        
        df = self.pg_manager.query_df(sql)
        
        # 如果数据库中没有数据，则从akshare获取
        if df.empty:
            try:
                # 发送进度信号
                self.progress_updated.emit(30)
                
                # 使用akshare获取财务数据
                income_df = ak.stock_financial_report_sina(stock=self.stock_code, symbol="利润表")
                
                # 发送进度信号
                self.progress_updated.emit(50)
                
                balance_df = ak.stock_financial_report_sina(stock=self.stock_code, symbol="资产负债表")
                
                # 发送进度信号
                self.progress_updated.emit(70)
                
                # 处理数据，合并报表
                # 这里简化处理，实际应用中需要更复杂的数据处理
                df = income_df[["报表日期", "营业收入", "净利润"]]
                df.columns = ["报告期", "营业收入", "净利润"]
                df["股票代码"] = self.stock_code
                
                # 保存到数据库
                self.pg_manager.create_table("股票财务数据", {
                    "股票代码": "VARCHAR(10) NOT NULL",
                    "报告期": "DATE NOT NULL",
                    "营业收入": "NUMERIC(20,2)",
                    "净利润": "NUMERIC(20,2)",
                    "PRIMARY KEY": "(股票代码, 报告期)"
                })
                self.pg_manager.insert_df("股票财务数据", df)
                
                # 发送进度信号
                self.progress_updated.emit(80)
            except Exception as e:
                print(f"获取股票财务数据失败: {e}")
                return pd.DataFrame()
        
        # 缓存数据到Redis
        if not df.empty:
            self.redis_manager.set_value(cache_key, df, expire=7200)  # 缓存2小时
        
        return df
    
    def get_market_data(self):
        """获取市场热度数据"""
        # 检查Redis缓存
        cache_key = f"market_heat:{self.stock_code}"
        cached_data = self.redis_manager.get_value(cache_key)
        if cached_data is not None:
            return cached_data
        
        # 从akshare获取数据
        try:
            # 发送进度信号
            self.progress_updated.emit(30)
            
            # 获取股票资金流向数据
            df = ak.stock_individual_fund_flow(stock=self.stock_code, market="sh" if self.stock_code.startswith("6") else "sz")
            
            # 发送进度信号
            self.progress_updated.emit(70)
            
            # 缓存数据到Redis
            if not df.empty:
                self.redis_manager.set_value(cache_key, df, expire=1800)  # 缓存30分钟
            
            return df
        except Exception as e:
            print(f"获取市场热度数据失败: {e}")
            return pd.DataFrame()


class ChartView(QWidget):
    """图表展示界面"""
    
    def __init__(self):
        super().__init__()
        
        # 初始化数据
        self.kline_data = pd.DataFrame()
        self.stock_info = {}
        
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
        
        # 创建控制面板
        control_panel = QGroupBox("图表控制")
        control_layout = QHBoxLayout()
        
        # 股票选择
        stock_layout = QFormLayout()
        self.stock_code_edit = QLineEdit()
        self.stock_code_edit.setPlaceholderText("请输入股票代码，如：000001")
        stock_layout.addRow("股票代码:", self.stock_code_edit)
        self.stock_name_label = QLabel("--")
        stock_layout.addRow("股票名称:", self.stock_name_label)
        control_layout.addLayout(stock_layout)
        
        # 日期范围
        date_layout = QFormLayout()
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QDate.currentDate().addMonths(-3))
        date_layout.addRow("开始日期:", self.start_date_edit)
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QDate.currentDate())
        date_layout.addRow("结束日期:", self.end_date_edit)
        control_layout.addLayout(date_layout)
        
        # 图表类型
        chart_type_layout = QFormLayout()
        self.chart_type_combo = QComboBox()
        self.chart_type_combo.addItems(["K线图", "技术指标", "基本面", "市场热度"])
        chart_type_layout.addRow("图表类型:", self.chart_type_combo)
        self.indicator_combo = QComboBox()
        self.indicator_combo.addItems(["MA", "MACD", "KDJ", "RSI", "BOLL"])
        chart_type_layout.addRow("技术指标:", self.indicator_combo)
        control_layout.addLayout(chart_type_layout)
        
        # 按钮区域
        button_layout = QVBoxLayout()
        self.query_button = QPushButton("查询")
        self.query_button.setStyleSheet("background-color: #1E90FF; color: white; font-weight: bold;")
        button_layout.addWidget(self.query_button)
        self.refresh_button = QPushButton("刷新")
        button_layout.addWidget(self.refresh_button)
        control_layout.addLayout(button_layout)
        
        # 设置控制面板布局
        control_panel.setLayout(control_layout)
        main_layout.addWidget(control_panel)
        
        # 添加进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)  # 初始隐藏
        main_layout.addWidget(self.progress_bar)
        
        # 创建图表区域
        self.chart_tab = QTabWidget()
        
        # K线图标签页
        self.kline_tab = QWidget()
        kline_layout = QVBoxLayout(self.kline_tab)
        
        # 创建K线图
        self.kline_plot = pg.PlotWidget()
        self.kline_plot.setLabel('left', '价格')
        self.kline_plot.setLabel('bottom', '日期')
        self.kline_plot.showGrid(x=True, y=True)
        self.kline_plot.setBackground('w')
        # 添加十字光标
        self.kline_crosshair = pg.CrosshairROI((0, 0), size=(1, 1), pen=pg.mkPen('r', width=1))
        self.kline_plot.addItem(self.kline_crosshair)
        kline_layout.addWidget(self.kline_plot)
        
        # 创建成交量图
        self.volume_plot = pg.PlotWidget()
        self.volume_plot.setLabel('left', '成交量')
        self.volume_plot.setLabel('bottom', '日期')
        self.volume_plot.showGrid(x=True, y=True)
        self.volume_plot.setBackground('w')
        kline_layout.addWidget(self.volume_plot)
        
        # 设置K线图和成交量图的比例
        kline_layout.setStretchFactor(self.kline_plot, 7)
        kline_layout.setStretchFactor(self.volume_plot, 3)
        
        # 技术指标标签页
        self.indicator_tab = QWidget()
        indicator_layout = QVBoxLayout(self.indicator_tab)
        
        # 创建技术指标图
        self.indicator_plot = pg.PlotWidget()
        self.indicator_plot.setLabel('left', '指标值')
        self.indicator_plot.setLabel('bottom', '日期')
        self.indicator_plot.showGrid(x=True, y=True)
        self.indicator_plot.setBackground('w')
        indicator_layout.addWidget(self.indicator_plot)
        
        # 基本面标签页
        self.fundamental_tab = QWidget()
        fundamental_layout = QVBoxLayout(self.fundamental_tab)
        
        # 创建基本面图表
        self.fundamental_plot = pg.PlotWidget()
        self.fundamental_plot.setLabel('left', '指标值')
        self.fundamental_plot.setLabel('bottom', '报告期')
        self.fundamental_plot.showGrid(x=True, y=True)
        self.fundamental_plot.setBackground('w')
        fundamental_layout.addWidget(self.fundamental_plot)
        
        # 市场热度标签页
        self.market_tab = QWidget()
        market_layout = QVBoxLayout(self.market_tab)
        
        # 创建市场热度图表
        self.market_plot = pg.PlotWidget()
        self.market_plot.setLabel('left', '资金流向')
        self.market_plot.setLabel('bottom', '日期')
        self.market_plot.showGrid(x=True, y=True)
        self.market_plot.setBackground('w')
        market_layout.addWidget(self.market_plot)
        
        # 添加标签页
        self.chart_tab.addTab(self.kline_tab, "K线图")
        self.chart_tab.addTab(self.indicator_tab, "技术指标")
        self.chart_tab.addTab(self.fundamental_tab, "基本面")
        self.chart_tab.addTab(self.market_tab, "市场热度")
        
        # 添加图表区域到主布局
        main_layout.addWidget(self.chart_tab)
        
        # 添加状态栏
        self.status_bar = QStatusBar()
        self.status_bar.showMessage("就绪")
        main_layout.addWidget(self.status_bar)
        
        # 设置布局比例
        main_layout.setStretchFactor(control_panel, 1)
        main_layout.setStretchFactor(self.chart_tab, 9)
    
    def connect_signals_slots(self):
        """连接信号和槽"""
        # 查询按钮点击事件
        self.query_button.clicked.connect(self.query_data)
        
        # 刷新按钮点击事件
        self.refresh_button.clicked.connect(self.refresh_data)
        
        # 图表类型变化事件
        self.chart_type_combo.currentIndexChanged.connect(self.on_chart_type_changed)
        
        # 技术指标变化事件
        self.indicator_combo.currentIndexChanged.connect(self.on_indicator_changed)
    
    def load_initial_data(self):
        """加载初始数据"""
        # 设置默认股票代码
        self.stock_code_edit.setText("000001")
        self.stock_name_label.setText("平安银行")
        
        # 生成示例数据
        self.generate_sample_data()
        
        # 绘制初始图表
        self.plot_kline_chart()
        self.plot_volume_chart()
        self.plot_indicator_chart()
    
    def generate_sample_data(self):
        """生成示例数据"""
        # 生成日期序列
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        
        # 生成K线数据
        np.random.seed(42)
        close = np.random.normal(100, 5, len(dates))
        close = np.cumsum(np.random.normal(0, 1, len(dates))) + 100
        open_price = close + np.random.normal(0, 1, len(dates))
        high = np.maximum(close, open_price) + np.random.normal(0.5, 0.5, len(dates))
        low = np.minimum(close, open_price) - np.random.normal(0.5, 0.5, len(dates))
        volume = np.random.normal(1000000, 200000, len(dates))
        volume = np.abs(volume)
        
        # 创建DataFrame
        self.kline_data = pd.DataFrame({
            '日期': dates,
            '开盘价': open_price,
            '最高价': high,
            '最低价': low,
            '收盘价': close,
            '成交量': volume
        })
        
        # 计算技术指标
        self.calculate_indicators()
    
    def calculate_indicators(self):
        """计算技术指标"""
        # 计算MA
        self.kline_data['MA5'] = self.kline_data['收盘价'].rolling(window=5).mean()
        self.kline_data['MA10'] = self.kline_data['收盘价'].rolling(window=10).mean()
        self.kline_data['MA20'] = self.kline_data['收盘价'].rolling(window=20).mean()
        
        # 计算MACD
        ema12 = self.kline_data['收盘价'].ewm(span=12, adjust=False).mean()
        ema26 = self.kline_data['收盘价'].ewm(span=26, adjust=False).mean()
        self.kline_data['DIFF'] = ema12 - ema26
        self.kline_data['DEA'] = self.kline_data['DIFF'].ewm(span=9, adjust=False).mean()
        self.kline_data['MACD'] = 2 * (self.kline_data['DIFF'] - self.kline_data['DEA'])
        
        # 计算KDJ
        low_9 = self.kline_data['最低价'].rolling(window=9).min()
        high_9 = self.kline_data['最高价'].rolling(window=9).max()
        rsv = 100 * ((self.kline_data['收盘价'] - low_9) / (high_9 - low_9))
        self.kline_data['K'] = rsv.ewm(com=2, adjust=False).mean()
        self.kline_data['D'] = self.kline_data['K'].ewm(com=2, adjust=False).mean()
        self.kline_data['J'] = 3 * self.kline_data['K'] - 2 * self.kline_data['D']
    
    def plot_kline_chart(self):
        """绘制K线图"""
        # 清空图表
        self.kline_plot.clear()
        
        # 创建K线图项
        kline_item = pg.GraphItem()
        self.kline_plot.addItem(kline_item)
        
        # 获取数据
        dates = np.arange(len(self.kline_data))
        open_price = self.kline_data['开盘价'].values
        close = self.kline_data['收盘价'].values
        high = self.kline_data['最高价'].values
        low = self.kline_data['最低价'].values
        
        # 绘制K线
        for i in range(len(dates)):
            # 判断涨跌
            if close[i] >= open_price[i]:
                color = 'r'  # 上涨为红色
            else:
                color = 'g'  # 下跌为绿色
            
            # 绘制实体
            self.kline_plot.plot([dates[i], dates[i]], [open_price[i], close[i]], 
                                pen=pg.mkPen(color, width=8))
            
            # 绘制上下影线
            self.kline_plot.plot([dates[i], dates[i]], [low[i], high[i]], 
                                pen=pg.mkPen(color, width=1))
        
        # 绘制均线
        if not self.kline_data['MA5'].isna().all():
            self.kline_plot.plot(dates, self.kline_data['MA5'].values, pen=pg.mkPen('b', width=1))
        if not self.kline_data['MA10'].isna().all():
            self.kline_plot.plot(dates, self.kline_data['MA10'].values, pen=pg.mkPen('y', width=1))
        if not self.kline_data['MA20'].isna().all():
            self.kline_plot.plot(dates, self.kline_data['MA20'].values, pen=pg.mkPen('m', width=1))
        
        # 设置X轴刻度
        date_strings = [d.strftime('%Y-%m-%d') for d in self.kline_data['日期']]
        ticks = []
        for i, date_str in enumerate(date_strings):
            if i % 10 == 0:  # 每10天显示一个日期标签
                ticks.append((i, date_str))
        self.kline_plot.getAxis('bottom').setTicks([ticks])
    
    def plot_volume_chart(self):
        """绘制成交量图"""
        # 清空图表
        self.volume_plot.clear()
        
        # 获取数据
        dates = np.arange(len(self.kline_data))
        volume = self.kline_data['成交量'].values
        open_price = self.kline_data['开盘价'].values
        close = self.kline_data['收盘价'].values
        
        # 绘制成交量柱状图
        for i in range(len(dates)):
            # 判断涨跌
            if close[i] >= open_price[i]:
                color = 'r'  # 上涨为红色
            else:
                color = 'g'  # 下跌为绿色
            
            # 绘制成交量柱
            self.volume_plot.plot([dates[i], dates[i]], [0, volume[i]], 
                                 pen=pg.mkPen(color, width=8))
        
        # 设置X轴刻度
        date_strings = [d.strftime('%Y-%m-%d') for d in self.kline_data['日期']]
        ticks = []
        for i, date_str in enumerate(date_strings):
            if i % 10 == 0:  # 每10天显示一个日期标签
                ticks.append((i, date_str))
        self.volume_plot.getAxis('bottom').setTicks([ticks])
    
    def plot_indicator_chart(self):
        """绘制技术指标图"""
        # 清空图表
        self.indicator_plot.clear()
        
        # 获取当前选择的指标
        indicator = self.indicator_combo.currentText()
        
        # 获取数据
        dates = np.arange(len(self.kline_data))
        
        # 根据选择的指标绘制不同的图表
        if indicator == "MA":
            if not self.kline_data['MA5'].isna().all():
                self.indicator_plot.plot(dates, self.kline_data['MA5'].values, 
                                        pen=pg.mkPen('b', width=1), name="MA5")
            if not self.kline_data['MA10'].isna().all():
                self.indicator_plot.plot(dates, self.kline_data['MA10'].values, 
                                        pen=pg.mkPen('y', width=1), name="MA10")
            if not self.kline_data['MA20'].isna().all():
                self.indicator_plot.plot(dates, self.kline_data['MA20'].values, 
                                        pen=pg.mkPen('m', width=1), name="MA20")
        
        elif indicator == "MACD":
            if not self.kline_data['DIFF'].isna().all():
                self.indicator_plot.plot(dates, self.kline_data['DIFF'].values, 
                                        pen=pg.mkPen('b', width=1), name="DIFF")
            if not self.kline_data['DEA'].isna().all():
                self.indicator_plot.plot(dates, self.kline_data['DEA'].values, 
                                        pen=pg.mkPen('y', width=1), name="DEA")
            
            # 绘制MACD柱状图
            for i in range(len(dates)):
                if not np.isnan(self.kline_data['MACD'].values[i]):
                    if self.kline_data['MACD'].values[i] >= 0:
                        color = 'r'  # 正值为红色
                    else:
                        color = 'g'  # 负值为绿色
                    
                    self.indicator_plot.plot([dates[i], dates[i]], 
                                           [0, self.kline_data['MACD'].values[i]], 
                                           pen=pg.mkPen(color, width=3))
        
        elif indicator == "KDJ":
            if not self.kline_data['K'].isna().all():
                self.indicator_plot.plot(dates, self.kline_data['K'].values, 
                                        pen=pg.mkPen('b', width=1), name="K")
            if not self.kline_data['D'].isna().all():
                self.indicator_plot.plot(dates, self.kline_data['D'].values, 
                                        pen=pg.mkPen('y', width=1), name="D")
            if not self.kline_data['J'].isna().all():
                self.indicator_plot.plot(dates, self.kline_data['J'].values, 
                                        pen=pg.mkPen('m', width=1), name="J")
        
        # 设置X轴刻度
        date_strings = [d.strftime('%Y-%m-%d') for d in self.kline_data['日期']]
        ticks = []
        for i, date_str in enumerate(date_strings):
            if i % 10 == 0:  # 每10天显示一个日期标签
                ticks.append((i, date_str))
        self.indicator_plot.getAxis('bottom').setTicks([ticks])
    
    def on_chart_type_changed(self, index):
        """图表类型变化事件处理"""
        chart_type = self.chart_type_combo.currentText()
        
        # 根据选择的图表类型切换标签页
        if chart_type == "K线图":
            self.chart_tab.setCurrentIndex(0)
        elif chart_type == "技术指标":
            self.chart_tab.setCurrentIndex(1)
            self.plot_indicator_chart()
        elif chart_type == "基本面":
            self.chart_tab.setCurrentIndex(2)
    
    def on_indicator_changed(self, index):
        """技术指标变化事件处理"""
        # 重新绘制技术指标图
        self.plot_indicator_chart()
    
    def query_data(self):
        """查询数据"""
        # 获取查询条件
        stock_code = self.stock_code_edit.text()
        start_date = self.start_date_edit.date().toString("yyyy-MM-dd")
        end_date = self.end_date_edit.date().toString("yyyy-MM-dd")
        
        # 这里应该添加从数据库或API获取数据的代码
        # 例如，根据股票代码和日期范围获取K线数据
        
        # 示例：更新股票名称
        self.stock_name_label.setText(f"示例股票 {stock_code}")
        
        # 生成新的示例数据
        self.generate_sample_data()
        
        # 重新绘制图表
        self.refresh_data()
    
    def refresh_data(self):
        """刷新数据"""
        # 重新绘制图表
        self.plot_kline_chart()
        self.plot_volume_chart()
        self.plot_indicator_chart()
    
    def show_tech_analysis(self):
        """显示技术分析视图"""
        self.chart_type_combo.setCurrentText("技术指标")
        self.chart_tab.setCurrentIndex(1)
        self.plot_indicator_chart()
    
    def show_fund_analysis(self):
        """显示基本面分析视图"""
        self.chart_type_combo.setCurrentText("基本面")
        self.chart_tab.setCurrentIndex(2)
    
    def show_market_analysis(self):
        """显示市场分析视图"""
        self.chart_type_combo.setCurrentText("市场热度")


if __name__ == "__main__":
    # 测试代码
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = ChartView()
    window.show()
    sys.exit(app.exec())