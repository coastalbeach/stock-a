#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
股票选择器组件
提供股票搜索、分类浏览和筛选功能
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
    QTreeWidget, QTreeWidgetItem, QTabWidget,
    QComboBox, QPushButton, QLabel, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon


class StockSelector(QWidget):
    """
    股票选择器组件
    支持搜索、分类浏览、自选股管理
    """
    
    # 信号定义
    stock_selected = pyqtSignal(str)  # 股票选择信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.setup_data()
        self.setup_connections()
        
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 搜索框
        self.setup_search_box(layout)
        
        # 标签页组件
        self.tab_widget = QTabWidget()
        
        # 市场分类标签页
        self.setup_market_tab()
        
        # 行业分类标签页
        self.setup_industry_tab()
        
        # 自选股标签页
        self.setup_favorites_tab()
        
        # 筛选器标签页
        self.setup_filter_tab()
        
        layout.addWidget(self.tab_widget)
        
    def setup_search_box(self, layout):
        """设置搜索框"""
        search_layout = QHBoxLayout()
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入股票代码或名称")
        
        self.search_btn = QPushButton("搜索")
        self.search_btn.setMaximumWidth(60)
        
        search_layout.addWidget(self.search_edit)
        search_layout.addWidget(self.search_btn)
        
        layout.addLayout(search_layout)
        
    def setup_market_tab(self):
        """设置市场分类标签页"""
        market_widget = QWidget()
        layout = QVBoxLayout(market_widget)
        
        self.market_tree = QTreeWidget()
        self.market_tree.setHeaderLabel("市场分类")
        
        # 添加市场分类
        self.add_market_categories()
        
        layout.addWidget(self.market_tree)
        self.tab_widget.addTab(market_widget, "市场")
        
    def setup_industry_tab(self):
        """设置行业分类标签页"""
        industry_widget = QWidget()
        layout = QVBoxLayout(industry_widget)
        
        self.industry_tree = QTreeWidget()
        self.industry_tree.setHeaderLabel("行业分类")
        
        # 添加行业分类
        self.add_industry_categories()
        
        layout.addWidget(self.industry_tree)
        self.tab_widget.addTab(industry_widget, "行业")
        
    def setup_favorites_tab(self):
        """设置自选股标签页"""
        favorites_widget = QWidget()
        layout = QVBoxLayout(favorites_widget)
        
        # 自选股分组
        group_layout = QHBoxLayout()
        group_layout.addWidget(QLabel("分组:"))
        
        self.group_combo = QComboBox()
        self.group_combo.addItems(["默认分组", "重点关注", "短线操作", "长线投资"])
        group_layout.addWidget(self.group_combo)
        
        self.add_group_btn = QPushButton("+")
        self.add_group_btn.setMaximumWidth(30)
        group_layout.addWidget(self.add_group_btn)
        
        layout.addLayout(group_layout)
        
        # 自选股列表
        self.favorites_tree = QTreeWidget()
        self.favorites_tree.setHeaderLabels(["代码", "名称", "价格", "涨跌幅"])
        
        layout.addWidget(self.favorites_tree)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        self.add_stock_btn = QPushButton("添加")
        self.remove_stock_btn = QPushButton("删除")
        
        btn_layout.addWidget(self.add_stock_btn)
        btn_layout.addWidget(self.remove_stock_btn)
        layout.addLayout(btn_layout)
        
        self.tab_widget.addTab(favorites_widget, "自选")
        
    def setup_filter_tab(self):
        """设置筛选器标签页"""
        filter_widget = QWidget()
        layout = QVBoxLayout(filter_widget)
        
        # 筛选条件
        conditions_layout = QVBoxLayout()
        
        # 市值筛选
        market_cap_layout = QHBoxLayout()
        market_cap_layout.addWidget(QLabel("市值:"))
        self.market_cap_combo = QComboBox()
        self.market_cap_combo.addItems(["不限", "大盘股", "中盘股", "小盘股"])
        market_cap_layout.addWidget(self.market_cap_combo)
        conditions_layout.addLayout(market_cap_layout)
        
        # PE筛选
        pe_layout = QHBoxLayout()
        pe_layout.addWidget(QLabel("PE:"))
        self.pe_combo = QComboBox()
        self.pe_combo.addItems(["不限", "<15", "15-25", "25-35", ">35"])
        pe_layout.addWidget(self.pe_combo)
        conditions_layout.addLayout(pe_layout)
        
        # 涨跌幅筛选
        change_layout = QHBoxLayout()
        change_layout.addWidget(QLabel("涨跌幅:"))
        self.change_combo = QComboBox()
        self.change_combo.addItems(["不限", "涨停", ">5%", "0-5%", "-5%-0%", "<-5%", "跌停"])
        change_layout.addWidget(self.change_combo)
        conditions_layout.addLayout(change_layout)
        
        layout.addLayout(conditions_layout)
        
        # 筛选按钮
        self.filter_btn = QPushButton("开始筛选")
        layout.addWidget(self.filter_btn)
        
        # 筛选结果
        self.filter_result_tree = QTreeWidget()
        self.filter_result_tree.setHeaderLabels(["代码", "名称", "价格", "涨跌幅", "市值", "PE"])
        layout.addWidget(self.filter_result_tree)
        
        self.tab_widget.addTab(filter_widget, "筛选")
        
    def add_market_categories(self):
        """添加市场分类"""
        # 沪深主板
        main_board = QTreeWidgetItem(self.market_tree, ["沪深主板"])
        
        # 沪市主板
        sh_main = QTreeWidgetItem(main_board, ["沪市主板"])
        # 添加示例股票
        QTreeWidgetItem(sh_main, ["600000.SH", "浦发银行"])
        QTreeWidgetItem(sh_main, ["600036.SH", "招商银行"])
        QTreeWidgetItem(sh_main, ["600519.SH", "贵州茅台"])
        
        # 深市主板
        sz_main = QTreeWidgetItem(main_board, ["深市主板"])
        QTreeWidgetItem(sz_main, ["000001.SZ", "平安银行"])
        QTreeWidgetItem(sz_main, ["000002.SZ", "万科A"])
        
        # 创业板
        gem_board = QTreeWidgetItem(self.market_tree, ["创业板"])
        QTreeWidgetItem(gem_board, ["300001.SZ", "特锐德"])
        QTreeWidgetItem(gem_board, ["300015.SZ", "爱尔眼科"])
        
        # 科创板
        star_board = QTreeWidgetItem(self.market_tree, ["科创板"])
        QTreeWidgetItem(star_board, ["688001.SH", "华兴源创"])
        QTreeWidgetItem(star_board, ["688009.SH", "中国通号"])
        
        # 北交所
        bse_board = QTreeWidgetItem(self.market_tree, ["北交所"])
        QTreeWidgetItem(bse_board, ["430047.BJ", "诺思兰德"])
        
        self.market_tree.expandAll()
        
    def add_industry_categories(self):
        """添加行业分类"""
        # 金融
        finance = QTreeWidgetItem(self.industry_tree, ["金融"])
        banking = QTreeWidgetItem(finance, ["银行"])
        QTreeWidgetItem(banking, ["600000.SH", "浦发银行"])
        QTreeWidgetItem(banking, ["600036.SH", "招商银行"])
        
        insurance = QTreeWidgetItem(finance, ["保险"])
        QTreeWidgetItem(insurance, ["601318.SH", "中国平安"])
        QTreeWidgetItem(insurance, ["601601.SH", "中国太保"])
        
        # 科技
        technology = QTreeWidgetItem(self.industry_tree, ["科技"])
        software = QTreeWidgetItem(technology, ["软件服务"])
        QTreeWidgetItem(software, ["600570.SH", "恒生电子"])
        QTreeWidgetItem(software, ["002415.SZ", "海康威视"])
        
        # 消费
        consumer = QTreeWidgetItem(self.industry_tree, ["消费"])
        liquor = QTreeWidgetItem(consumer, ["白酒"])
        QTreeWidgetItem(liquor, ["600519.SH", "贵州茅台"])
        QTreeWidgetItem(liquor, ["000858.SZ", "五粮液"])
        
        self.industry_tree.expandAll()
        
    def setup_data(self):
        """设置数据"""
        # 初始化自选股数据
        self.favorites_data = {
            "默认分组": [
                {"code": "600519.SH", "name": "贵州茅台", "price": 1680.00, "change": 2.5},
                {"code": "000858.SZ", "name": "五粮液", "price": 158.50, "change": -1.2},
            ],
            "重点关注": [
                {"code": "600036.SH", "name": "招商银行", "price": 42.50, "change": 1.8},
            ]
        }
        
        self.update_favorites_display()
        
    def update_favorites_display(self):
        """更新自选股显示"""
        self.favorites_tree.clear()
        
        current_group = self.group_combo.currentText()
        if current_group in self.favorites_data:
            for stock in self.favorites_data[current_group]:
                item = QTreeWidgetItem(self.favorites_tree)
                item.setText(0, stock["code"])
                item.setText(1, stock["name"])
                item.setText(2, f"{stock['price']:.2f}")
                
                change_text = f"{stock['change']:+.2f}%"
                item.setText(3, change_text)
                
                # 设置涨跌颜色
                if stock["change"] > 0:
                    item.setForeground(3, Qt.GlobalColor.red)
                elif stock["change"] < 0:
                    item.setForeground(3, Qt.GlobalColor.green)
                    
    def setup_connections(self):
        """设置信号连接"""
        # 搜索功能
        self.search_btn.clicked.connect(self.search_stock)
        self.search_edit.returnPressed.connect(self.search_stock)
        
        # 树形控件双击事件
        self.market_tree.itemDoubleClicked.connect(self.on_tree_item_double_clicked)
        self.industry_tree.itemDoubleClicked.connect(self.on_tree_item_double_clicked)
        self.favorites_tree.itemDoubleClicked.connect(self.on_tree_item_double_clicked)
        self.filter_result_tree.itemDoubleClicked.connect(self.on_tree_item_double_clicked)
        
        # 自选股操作
        self.group_combo.currentTextChanged.connect(self.update_favorites_display)
        self.add_stock_btn.clicked.connect(self.add_to_favorites)
        self.remove_stock_btn.clicked.connect(self.remove_from_favorites)
        
        # 筛选功能
        self.filter_btn.clicked.connect(self.start_filter)
        
    def search_stock(self):
        """搜索股票"""
        keyword = self.search_edit.text().strip()
        if not keyword:
            return
            
        # TODO: 实现股票搜索逻辑
        print(f"搜索股票: {keyword}")
        
    def on_tree_item_double_clicked(self, item, column):
        """处理树形控件双击事件"""
        # 获取股票代码
        stock_code = None
        
        if item.childCount() == 0:  # 叶子节点
            if item.text(0).count('.') > 0:  # 包含股票代码格式
                stock_code = item.text(0)
            elif item.parent() and item.parent().text(0).count('.') > 0:
                stock_code = item.parent().text(0)
                
        if stock_code:
            self.stock_selected.emit(stock_code)
            print(f"选择股票: {stock_code}")
            
    def add_to_favorites(self):
        """添加到自选股"""
        # TODO: 实现添加到自选股功能
        print("添加到自选股")
        
    def remove_from_favorites(self):
        """从自选股删除"""
        current_item = self.favorites_tree.currentItem()
        if current_item:
            stock_code = current_item.text(0)
            # TODO: 实现从自选股删除功能
            print(f"从自选股删除: {stock_code}")
            
    def start_filter(self):
        """开始筛选"""
        # 获取筛选条件
        market_cap = self.market_cap_combo.currentText()
        pe_range = self.pe_combo.currentText()
        change_range = self.change_combo.currentText()
        
        # TODO: 实现股票筛选逻辑
        print(f"筛选条件 - 市值: {market_cap}, PE: {pe_range}, 涨跌幅: {change_range}")
        
        # 模拟筛选结果
        self.filter_result_tree.clear()
        sample_results = [
            ["600519.SH", "贵州茅台", "1680.00", "+2.5%", "2.1万亿", "35.2"],
            ["000858.SZ", "五粮液", "158.50", "-1.2%", "6156亿", "28.5"],
        ]
        
        for result in sample_results:
            item = QTreeWidgetItem(self.filter_result_tree, result)
            # 设置涨跌颜色
            if result[3].startswith('+'):
                item.setForeground(3, Qt.GlobalColor.red)
            elif result[3].startswith('-'):
                item.setForeground(3, Qt.GlobalColor.green)