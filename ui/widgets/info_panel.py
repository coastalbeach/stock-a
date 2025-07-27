#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
信息面板组件
显示股票基本信息、实时行情、资金流向等信息
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QFrame, QScrollArea, QGridLayout, QPushButton
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPalette
import random
from datetime import datetime


class InfoPanel(QWidget):
    """
    信息面板组件
    显示股票详细信息和实时数据
    """
    
    # 信号定义
    add_to_favorites = pyqtSignal(str)  # 添加到自选股信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_stock = None
        self.init_ui()
        self.setup_timer()
        
    def init_ui(self):
        """初始化用户界面"""
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # 创建内容组件
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 股票基本信息
        self.setup_basic_info(layout)
        
        # 实时行情
        self.setup_realtime_quote(layout)
        
        # 今日资金流向
        self.setup_money_flow(layout)
        
        # 技术指标概览
        self.setup_technical_overview(layout)
        
        # 重要公告
        self.setup_announcements(layout)
        
        # 操作按钮
        self.setup_action_buttons(layout)
        
        layout.addStretch()
        
        scroll_area.setWidget(content_widget)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll_area)
        
    def setup_basic_info(self, layout):
        """设置基本信息区域"""
        # 创建分组框
        group_frame = self.create_group_frame("股票信息")
        group_layout = QVBoxLayout(group_frame)
        
        # 股票名称和代码
        self.stock_name_label = QLabel("请选择股票")
        self.stock_name_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.stock_name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        group_layout.addWidget(self.stock_name_label)
        
        self.stock_code_label = QLabel("")
        self.stock_code_label.setFont(QFont("Arial", 10))
        self.stock_code_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        group_layout.addWidget(self.stock_code_label)
        
        # 基本信息网格
        info_grid = QGridLayout()
        
        # 创建信息标签
        self.create_info_row(info_grid, 0, "总市值:", "market_cap")
        self.create_info_row(info_grid, 1, "流通市值:", "float_cap")
        self.create_info_row(info_grid, 2, "市盈率:", "pe_ratio")
        self.create_info_row(info_grid, 3, "市净率:", "pb_ratio")
        self.create_info_row(info_grid, 4, "每股收益:", "eps")
        self.create_info_row(info_grid, 5, "净资产收益率:", "roe")
        
        group_layout.addLayout(info_grid)
        layout.addWidget(group_frame)
        
    def setup_realtime_quote(self, layout):
        """设置实时行情区域"""
        group_frame = self.create_group_frame("实时行情")
        group_layout = QVBoxLayout(group_frame)
        
        # 当前价格
        price_layout = QHBoxLayout()
        
        self.current_price_label = QLabel("--")
        self.current_price_label.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        price_layout.addWidget(self.current_price_label)
        
        price_layout.addStretch()
        
        # 涨跌信息
        change_layout = QVBoxLayout()
        
        self.price_change_label = QLabel("--")
        self.price_change_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        change_layout.addWidget(self.price_change_label)
        
        self.change_percent_label = QLabel("--")
        self.change_percent_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        change_layout.addWidget(self.change_percent_label)
        
        price_layout.addLayout(change_layout)
        group_layout.addLayout(price_layout)
        
        # 行情数据网格
        quote_grid = QGridLayout()
        
        self.create_info_row(quote_grid, 0, "今开:", "open_price")
        self.create_info_row(quote_grid, 1, "昨收:", "prev_close")
        self.create_info_row(quote_grid, 2, "最高:", "high_price")
        self.create_info_row(quote_grid, 3, "最低:", "low_price")
        self.create_info_row(quote_grid, 4, "成交量:", "volume")
        self.create_info_row(quote_grid, 5, "成交额:", "amount")
        self.create_info_row(quote_grid, 6, "换手率:", "turnover")
        self.create_info_row(quote_grid, 7, "振幅:", "amplitude")
        
        group_layout.addLayout(quote_grid)
        layout.addWidget(group_frame)
        
    def setup_money_flow(self, layout):
        """设置资金流向区域"""
        group_frame = self.create_group_frame("资金流向")
        group_layout = QVBoxLayout(group_frame)
        
        # 主力净流入
        main_flow_layout = QHBoxLayout()
        main_flow_layout.addWidget(QLabel("主力净流入:"))
        
        self.main_flow_label = QLabel("--")
        self.main_flow_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        main_flow_layout.addWidget(self.main_flow_label)
        main_flow_layout.addStretch()
        
        group_layout.addLayout(main_flow_layout)
        
        # 资金流向详情
        flow_grid = QGridLayout()
        
        self.create_info_row(flow_grid, 0, "超大单:", "super_large")
        self.create_info_row(flow_grid, 1, "大单:", "large_order")
        self.create_info_row(flow_grid, 2, "中单:", "medium_order")
        self.create_info_row(flow_grid, 3, "小单:", "small_order")
        
        group_layout.addLayout(flow_grid)
        layout.addWidget(group_frame)
        
    def setup_technical_overview(self, layout):
        """设置技术指标概览"""
        group_frame = self.create_group_frame("技术指标")
        group_layout = QVBoxLayout(group_frame)
        
        # 技术指标网格
        tech_grid = QGridLayout()
        
        self.create_info_row(tech_grid, 0, "MA5:", "ma5")
        self.create_info_row(tech_grid, 1, "MA10:", "ma10")
        self.create_info_row(tech_grid, 2, "MA20:", "ma20")
        self.create_info_row(tech_grid, 3, "MACD:", "macd")
        self.create_info_row(tech_grid, 4, "RSI:", "rsi")
        self.create_info_row(tech_grid, 5, "KDJ:", "kdj")
        
        group_layout.addLayout(tech_grid)
        layout.addWidget(group_frame)
        
    def setup_announcements(self, layout):
        """设置重要公告区域"""
        group_frame = self.create_group_frame("重要公告")
        group_layout = QVBoxLayout(group_frame)
        
        # 公告列表
        self.announcement_labels = []
        for i in range(3):
            label = QLabel("暂无公告")
            label.setFont(QFont("Arial", 9))
            label.setWordWrap(True)
            label.setStyleSheet("QLabel { color: #666; padding: 2px; }")
            self.announcement_labels.append(label)
            group_layout.addWidget(label)
            
        layout.addWidget(group_frame)
        
    def setup_action_buttons(self, layout):
        """设置操作按钮"""
        button_layout = QHBoxLayout()
        
        # 添加自选
        self.add_favorite_btn = QPushButton("加自选")
        self.add_favorite_btn.clicked.connect(self.on_add_to_favorites)
        button_layout.addWidget(self.add_favorite_btn)
        
        # 设置提醒
        self.set_alert_btn = QPushButton("设提醒")
        button_layout.addWidget(self.set_alert_btn)
        
        layout.addLayout(button_layout)
        
    def create_group_frame(self, title):
        """创建分组框架"""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.Box)
        frame.setStyleSheet("""
            QFrame {
                border: 1px solid #ccc;
                border-radius: 5px;
                margin: 2px;
            }
        """)
        
        # 添加标题
        layout = QVBoxLayout(frame)
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        title_label.setStyleSheet("QLabel { border: none; color: #333; margin-bottom: 5px; }")
        layout.addWidget(title_label)
        
        return frame
        
    def create_info_row(self, grid_layout, row, label_text, value_attr):
        """创建信息行"""
        label = QLabel(label_text)
        label.setFont(QFont("Arial", 9))
        
        value_label = QLabel("--")
        value_label.setFont(QFont("Arial", 9))
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        # 保存值标签的引用
        setattr(self, f"{value_attr}_label", value_label)
        
        grid_layout.addWidget(label, row, 0)
        grid_layout.addWidget(value_label, row, 1)
        
    def setup_timer(self):
        """设置定时器"""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_realtime_data)
        
    def update_stock_info(self, stock_code):
        """更新股票信息"""
        self.current_stock = stock_code
        
        # TODO: 从数据库或API获取真实股票信息
        # 目前使用示例数据
        self.load_sample_data(stock_code)
        
        # 开始实时更新
        self.update_timer.start(5000)  # 5秒更新一次
        
    def load_sample_data(self, stock_code):
        """加载示例数据"""
        # 股票基本信息
        stock_names = {
            "600519.SH": "贵州茅台",
            "000858.SZ": "五粮液",
            "600036.SH": "招商银行",
            "000001.SZ": "平安银行"
        }
        
        stock_name = stock_names.get(stock_code, "未知股票")
        self.stock_name_label.setText(stock_name)
        self.stock_code_label.setText(stock_code)
        
        # 基本信息
        self.market_cap_label.setText("2.1万亿")
        self.float_cap_label.setText("2.1万亿")
        self.pe_ratio_label.setText("35.2")
        self.pb_ratio_label.setText("8.5")
        self.eps_label.setText("47.15")
        self.roe_label.setText("25.8%")
        
        # 实时行情（示例数据）
        self.update_sample_quote_data()
        
        # 资金流向
        self.main_flow_label.setText("+1.25亿")
        self.main_flow_label.setStyleSheet("color: red;")
        
        self.super_large_label.setText("+0.85亿")
        self.super_large_label.setStyleSheet("color: red;")
        self.large_order_label.setText("+0.40亿")
        self.large_order_label.setStyleSheet("color: red;")
        self.medium_order_label.setText("-0.25亿")
        self.medium_order_label.setStyleSheet("color: green;")
        self.small_order_label.setText("-0.75亿")
        self.small_order_label.setStyleSheet("color: green;")
        
        # 技术指标
        self.ma5_label.setText("1675.50")
        self.ma10_label.setText("1682.30")
        self.ma20_label.setText("1690.80")
        self.macd_label.setText("0.025")
        self.rsi_label.setText("65.8")
        self.kdj_label.setText("72.5")
        
        # 重要公告
        announcements = [
            "2024-01-15: 发布2023年年度业绩预告",
            "2024-01-10: 董事会决议公告",
            "2024-01-05: 关于股东减持计划的公告"
        ]
        
        for i, announcement in enumerate(announcements):
            if i < len(self.announcement_labels):
                self.announcement_labels[i].setText(announcement)
                
    def update_sample_quote_data(self):
        """更新示例行情数据"""
        # 生成模拟价格变动
        base_price = 1680.0
        price_change = random.uniform(-20, 20)
        current_price = base_price + price_change
        
        prev_close = 1675.0
        change = current_price - prev_close
        change_percent = (change / prev_close) * 100
        
        # 更新价格显示
        self.current_price_label.setText(f"{current_price:.2f}")
        self.price_change_label.setText(f"{change:+.2f}")
        self.change_percent_label.setText(f"{change_percent:+.2f}%")
        
        # 设置颜色
        if change > 0:
            color = "red"
        elif change < 0:
            color = "green"
        else:
            color = "black"
            
        self.current_price_label.setStyleSheet(f"color: {color};")
        self.price_change_label.setStyleSheet(f"color: {color};")
        self.change_percent_label.setStyleSheet(f"color: {color};")
        
        # 更新其他行情数据
        self.open_price_label.setText(f"{prev_close + random.uniform(-5, 5):.2f}")
        self.prev_close_label.setText(f"{prev_close:.2f}")
        self.high_price_label.setText(f"{current_price + random.uniform(0, 10):.2f}")
        self.low_price_label.setText(f"{current_price - random.uniform(0, 10):.2f}")
        
        volume = random.randint(50000, 200000)
        amount = volume * current_price
        
        self.volume_label.setText(f"{volume:,}手")
        self.amount_label.setText(f"{amount/100000000:.2f}亿")
        self.turnover_label.setText(f"{random.uniform(0.5, 3.0):.2f}%")
        self.amplitude_label.setText(f"{random.uniform(1.0, 5.0):.2f}%")
        
    def update_realtime_data(self):
        """更新实时数据"""
        if self.current_stock:
            # TODO: 从API获取真实实时数据
            self.update_sample_quote_data()
            
    def on_add_to_favorites(self):
        """添加到自选股"""
        if self.current_stock:
            self.add_to_favorites.emit(self.current_stock)
            self.add_favorite_btn.setText("已加自选")
            self.add_favorite_btn.setEnabled(False)
            
    def stop_updates(self):
        """停止更新"""
        if hasattr(self, 'update_timer'):
            self.update_timer.stop()