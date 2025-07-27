#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
图表组件
提供专业的K线图表、技术指标显示功能
"""

# import pyqtgraph as pg  # 暂时注释掉
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, 
    QPushButton, QLabel, QSplitter, QCheckBox, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
# import numpy as np  # 暂时注释掉
from datetime import datetime, timedelta


# class CandlestickItem(pg.GraphicsObject):
#     """
#     K线图形项
#     """
#     
#     def __init__(self, data):
#         pg.GraphicsObject.__init__(self)
#         self.data = data
#         self.generatePicture()
#         
#     def generatePicture(self):
#         """生成K线图形"""
#         self.picture = pg.QtGui.QPicture()
#         p = pg.QtGui.QPainter(self.picture)
#         
#         # 设置画笔
#         p.setPen(pg.mkPen('w', width=1))
#         
#         w = 0.8  # K线宽度
#         
#         for i, (time, open_price, high, low, close, volume) in enumerate(self.data):
#             # 确定颜色（红涨绿跌）
#             if close > open_price:
#                 p.setBrush(pg.mkBrush('r'))  # 红色
#                 p.setPen(pg.mkPen('r', width=1))
#             else:
#                 p.setBrush(pg.mkBrush('g'))  # 绿色
#                 p.setPen(pg.mkPen('g', width=1))
#                 
#             # 绘制影线
#             p.drawLine(pg.QtCore.QPointF(i, low), pg.QtCore.QPointF(i, high))
#             
#             # 绘制实体
#             if close != open_price:
#                 p.drawRect(pg.QtCore.QRectF(i-w/2, min(open_price, close), 
#                                           w, abs(close - open_price)))
#             else:
#                 # 十字星
#                 p.drawLine(pg.QtCore.QPointF(i-w/2, close), 
#                           pg.QtCore.QPointF(i+w/2, close))
#                 
#         p.end()
#         
#     def paint(self, p, *args):
#         p.drawPicture(0, 0, self.picture)
#         
#     def boundingRect(self):
#         return pg.QtCore.QRectF(self.picture.boundingRect())


class ChartWidget(QWidget):
    """
    图表组件
    支持K线图、技术指标、成交量等显示
    """
    
    # 信号定义
    period_changed = pyqtSignal(str)  # 周期切换信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_stock = None
        self.init_ui()
        self.setup_sample_data()
        
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 工具栏
        self.setup_toolbar(layout)
        
        # 图表区域
        self.setup_chart_area(layout)
        
    def setup_toolbar(self, layout):
        """设置工具栏"""
        toolbar_layout = QHBoxLayout()
        
        # 股票信息
        self.stock_label = QLabel("请选择股票")
        self.stock_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        toolbar_layout.addWidget(self.stock_label)
        
        toolbar_layout.addStretch()
        
        # 周期选择
        toolbar_layout.addWidget(QLabel("周期:"))
        self.period_combo = QComboBox()
        self.period_combo.addItems(["1分钟", "5分钟", "15分钟", "30分钟", 
                                   "1小时", "日线", "周线", "月线"])
        self.period_combo.setCurrentText("日线")
        toolbar_layout.addWidget(self.period_combo)
        
        # 复权选择
        toolbar_layout.addWidget(QLabel("复权:"))
        self.adjust_combo = QComboBox()
        self.adjust_combo.addItems(["不复权", "前复权", "后复权"])
        self.adjust_combo.setCurrentText("前复权")
        toolbar_layout.addWidget(self.adjust_combo)
        
        # 技术指标选择
        self.ma_checkbox = QCheckBox("均线")
        self.ma_checkbox.setChecked(True)
        toolbar_layout.addWidget(self.ma_checkbox)
        
        self.macd_checkbox = QCheckBox("MACD")
        toolbar_layout.addWidget(self.macd_checkbox)
        
        self.rsi_checkbox = QCheckBox("RSI")
        toolbar_layout.addWidget(self.rsi_checkbox)
        
        # 全屏按钮
        self.fullscreen_btn = QPushButton("全屏")
        toolbar_layout.addWidget(self.fullscreen_btn)
        
        layout.addLayout(toolbar_layout)
        
    def setup_chart_area(self, layout):
        """设置图表区域"""
        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # 主图表（K线图）- 暂时使用QTextEdit
        self.main_chart = QTextEdit()
        self.main_chart.setPlainText("主图表区域\n(K线图将在此显示)")
        self.main_chart.setReadOnly(True)
        
        splitter.addWidget(self.main_chart)
        
        # 成交量图表 - 暂时使用QTextEdit
        self.volume_chart = QTextEdit()
        self.volume_chart.setPlainText("成交量图表区域")
        self.volume_chart.setReadOnly(True)
        self.volume_chart.setMaximumHeight(150)
        
        splitter.addWidget(self.volume_chart)
        
        # 技术指标图表 - 暂时使用QTextEdit
        self.indicator_chart = QTextEdit()
        self.indicator_chart.setPlainText("技术指标图表区域")
        self.indicator_chart.setReadOnly(True)
        self.indicator_chart.setMaximumHeight(120)
        
        splitter.addWidget(self.indicator_chart)
        
        # 设置分割器比例
        splitter.setSizes([400, 150, 120])
        
        layout.addWidget(splitter)
        
        # 连接信号
        self.setup_connections()
        
    def setup_connections(self):
        """设置信号连接"""
        self.period_combo.currentTextChanged.connect(self.on_period_changed)
        self.adjust_combo.currentTextChanged.connect(self.on_adjust_changed)
        
        self.ma_checkbox.toggled.connect(self.update_indicators)
        self.macd_checkbox.toggled.connect(self.update_indicators)
        self.rsi_checkbox.toggled.connect(self.update_indicators)
        
        self.fullscreen_btn.clicked.connect(self.toggle_fullscreen)
        
    def setup_sample_data(self):
        """设置示例数据"""
        # 生成示例K线数据
        import random
        random.seed(42)
        n_days = 100
        
        # 生成时间序列
        dates = [datetime.now() - timedelta(days=i) for i in range(n_days, 0, -1)]
        
        # 生成价格数据
        base_price = 100
        prices = []
        volumes = []
        
        current_price = base_price
        for i in range(n_days):
            # 开盘价
            open_price = current_price + random.gauss(0, 1)
            
            # 最高价和最低价
            high = open_price + abs(random.gauss(2, 1))
            low = open_price - abs(random.gauss(2, 1))
            
            # 收盘价
            close = open_price + random.gauss(0, 2)
            close = max(low, min(high, close))  # 确保在合理范围内
            
            # 成交量
            volume = abs(random.gauss(10000, 3000))
            
            prices.append((i, open_price, high, low, close, volume))
            volumes.append(volume)
            
            current_price = close
            
        self.sample_data = prices
        self.sample_volumes = volumes
        self.sample_dates = dates
        
        # 显示示例数据
        self.display_sample_chart()
        
    def display_sample_chart(self):
        """显示示例图表"""
        # 暂时使用文本显示数据
        if hasattr(self, 'sample_data') and self.sample_data:
            # 显示最近几天的数据
            recent_data = self.sample_data[-5:]
            chart_text = "最近5天K线数据:\n"
            chart_text += "日期\t开盘\t最高\t最低\t收盘\t成交量\n"
            for i, (idx, open_p, high, low, close, volume) in enumerate(recent_data):
                chart_text += f"{i+1}\t{open_p:.2f}\t{high:.2f}\t{low:.2f}\t{close:.2f}\t{volume:.0f}\n"
            
            self.main_chart.setPlainText(chart_text)
            self.volume_chart.setPlainText(f"成交量图表\n平均成交量: {sum(d[5] for d in recent_data)/len(recent_data):.0f}")
            self.indicator_chart.setPlainText("技术指标图表\n(MACD, RSI等)")
            
    def draw_moving_averages(self):
        """绘制移动平均线"""
        # 暂时注释掉pyqtgraph相关代码
        pass
        # closes = [data[4] for data in self.sample_data]  # 收盘价
        # x = list(range(len(closes)))
        # 
        # # MA5
        # ma5 = self.calculate_ma(closes, 5)
        # self.main_chart.plot(x[4:], ma5, pen=pg.mkPen('yellow', width=1), name='MA5')
        # 
        # # MA10
        # ma10 = self.calculate_ma(closes, 10)
        # self.main_chart.plot(x[9:], ma10, pen=pg.mkPen('blue', width=1), name='MA10')
        # 
        # # MA20
        # ma20 = self.calculate_ma(closes, 20)
        # self.main_chart.plot(x[19:], ma20, pen=pg.mkPen('magenta', width=1), name='MA20')
        
    def calculate_ma(self, data, period):
        """计算移动平均线"""
        ma = []
        for i in range(period - 1, len(data)):
            ma.append(sum(data[i-period+1:i+1]) / period)
        return ma
        
    def draw_volume(self):
        """绘制成交量"""
        # 暂时注释掉pyqtgraph相关代码
        pass
        # x = list(range(len(self.sample_volumes)))
        # 
        # # 创建成交量柱状图
        # bargraph = pg.BarGraphItem(x=x, height=self.sample_volumes, 
        #                           width=0.8, brush='cyan', pen='cyan')
        # self.volume_chart.addItem(bargraph)
        
    def draw_macd(self):
        """绘制MACD指标"""
        # 暂时注释掉pyqtgraph相关代码
        pass
        # closes = [data[4] for data in self.sample_data]
        # 
        # # 简化的MACD计算
        # ema12 = self.calculate_ema(closes, 12)
        # ema26 = self.calculate_ema(closes, 26)
        # 
        # if len(ema12) > 0 and len(ema26) > 0:
        #     min_len = min(len(ema12), len(ema26))
        #     dif = [ema12[i] - ema26[i] for i in range(min_len)]
        #     dea = self.calculate_ema(dif, 9)
        #     
        #     x = list(range(len(dif)))
        #     self.indicator_chart.plot(x, dif, pen=pg.mkPen('white', width=1), name='DIF')
        #     
        #     if len(dea) > 0:
        #         x_dea = list(range(len(dea)))
        #         self.indicator_chart.plot(x_dea, dea, pen=pg.mkPen('yellow', width=1), name='DEA')
                
    def calculate_ema(self, data, period):
        """计算指数移动平均线"""
        if len(data) < period:
            return []
            
        ema = []
        multiplier = 2 / (period + 1)
        
        # 第一个EMA值使用SMA
        sma = sum(data[:period]) / period
        ema.append(sma)
        
        # 计算后续EMA值
        for i in range(period, len(data)):
            ema_value = (data[i] * multiplier) + (ema[-1] * (1 - multiplier))
            ema.append(ema_value)
            
        return ema
        
    def draw_rsi(self):
        """绘制RSI指标"""
        # 暂时注释掉pyqtgraph相关代码
        pass
        # closes = [data[4] for data in self.sample_data]
        # rsi = self.calculate_rsi(closes, 14)
        # 
        # if len(rsi) > 0:
        #     x = list(range(len(rsi)))
        #     self.indicator_chart.plot(x, rsi, pen=pg.mkPen('orange', width=1), name='RSI')
        #     
        #     # 添加超买超卖线
        #     self.indicator_chart.addLine(y=70, pen=pg.mkPen('red', style=Qt.PenStyle.DashLine))
        #     self.indicator_chart.addLine(y=30, pen=pg.mkPen('green', style=Qt.PenStyle.DashLine))
            
    def calculate_rsi(self, data, period):
        """计算RSI指标"""
        if len(data) < period + 1:
            return []
            
        gains = []
        losses = []
        
        # 计算涨跌幅
        for i in range(1, len(data)):
            change = data[i] - data[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
                
        rsi = []
        for i in range(period - 1, len(gains)):
            avg_gain = sum(gains[i-period+1:i+1]) / period
            avg_loss = sum(losses[i-period+1:i+1]) / period
            
            if avg_loss == 0:
                rsi.append(100)
            else:
                rs = avg_gain / avg_loss
                rsi_value = 100 - (100 / (1 + rs))
                rsi.append(rsi_value)
                
        return rsi
        
    def load_stock_data(self, stock_code):
        """加载股票数据"""
        self.current_stock = stock_code
        
        # 更新股票标签
        self.stock_label.setText(f"股票代码: {stock_code}")
        
        # TODO: 从数据库或API加载真实股票数据
        # 目前显示示例数据
        self.display_sample_chart()
        
    def on_period_changed(self, period):
        """处理周期切换"""
        self.period_changed.emit(period)
        # TODO: 根据新周期重新加载数据
        print(f"切换到{period}")
        
    def on_adjust_changed(self, adjust_type):
        """处理复权类型切换"""
        # TODO: 根据复权类型重新加载数据
        print(f"切换到{adjust_type}")
        
    def update_indicators(self):
        """更新技术指标显示"""
        self.display_sample_chart()
        
    def toggle_fullscreen(self):
        """切换全屏模式"""
        if self.isFullScreen():
            self.showNormal()
            self.fullscreen_btn.setText("全屏")
        else:
            self.showFullScreen()
            self.fullscreen_btn.setText("退出全屏")