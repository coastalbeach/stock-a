#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据表格组件
提供股票数据的表格显示功能
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
    QTableWidgetItem, QTabWidget, QComboBox, QLabel,
    QPushButton, QHeaderView, QAbstractItemView, QSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from datetime import datetime, timedelta
import random
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from db.enhanced_postgresql_manager import EnhancedPostgreSQLManager


class DataTableWidget(QWidget):
    """
    数据表格组件
    支持历史数据、实时数据、财务数据等多种数据显示
    """
    
    # 信号定义
    data_updated = pyqtSignal()  # 数据更新信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_stock = None
        self.db_manager = EnhancedPostgreSQLManager()
        self.current_page = 0
        self.page_size = 100  # 每页显示100条记录
        self.total_records = 0
        self.init_ui()
        self.load_real_data()
        
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 工具栏
        self.setup_toolbar(layout)
        
        # 标签页组件
        self.tab_widget = QTabWidget()
        
        # 历史数据标签页
        self.setup_history_tab()
        
        # 实时数据标签页
        self.setup_realtime_tab()
        
        # 财务数据标签页
        self.setup_financial_tab()
        
        # 技术指标标签页
        self.setup_technical_tab()
        
        layout.addWidget(self.tab_widget)
        
    def setup_toolbar(self, layout):
        """设置工具栏"""
        toolbar_layout = QHBoxLayout()
        
        # 数据源选择
        self.data_source_combo = QComboBox()
        self.data_source_combo.addItems(["股票基本信息", "股票历史行情", "技术指标", "资产负债表", "利润表", "现金流量表", "行业板块", "概念板块"])
        self.data_source_combo.currentTextChanged.connect(self.on_data_source_changed)
        
        # 每页记录数选择
        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["50", "100", "200", "500"])
        self.page_size_combo.setCurrentText("100")
        self.page_size_combo.currentTextChanged.connect(self.on_page_size_changed)
        
        # 分页控件
        self.prev_btn = QPushButton("上一页")
        self.prev_btn.clicked.connect(self.prev_page)
        
        self.page_label = QLabel("第 1 页 / 共 1 页")
        
        self.next_btn = QPushButton("下一页")
        self.next_btn.clicked.connect(self.next_page)
        
        # 跳转页面
        self.goto_page_spin = QSpinBox()
        self.goto_page_spin.setMinimum(1)
        self.goto_page_spin.setValue(1)
        self.goto_page_spin.valueChanged.connect(self.goto_page)
        
        # 导出按钮
        self.export_btn = QPushButton("导出数据")
        self.export_btn.clicked.connect(self.export_data)
        
        # 刷新按钮
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.refresh_data)
        
        toolbar_layout.addWidget(QLabel("数据源:"))
        toolbar_layout.addWidget(self.data_source_combo)
        toolbar_layout.addWidget(QLabel("每页:"))
        toolbar_layout.addWidget(self.page_size_combo)
        toolbar_layout.addWidget(QLabel("条"))
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.prev_btn)
        toolbar_layout.addWidget(self.page_label)
        toolbar_layout.addWidget(self.next_btn)
        toolbar_layout.addWidget(QLabel("跳转:"))
        toolbar_layout.addWidget(self.goto_page_spin)
        toolbar_layout.addWidget(self.export_btn)
        toolbar_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(toolbar_layout)
        
    def setup_history_tab(self):
        """设置历史数据标签页"""
        history_widget = QWidget()
        layout = QVBoxLayout(history_widget)
        
        # 创建表格
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(8)
        self.history_table.setHorizontalHeaderLabels([
            "日期", "开盘", "最高", "最低", "收盘", "涨跌幅", "成交量", "成交额"
        ])
        
        # 设置表格属性
        self.setup_table_properties(self.history_table)
        
        layout.addWidget(self.history_table)
        self.tab_widget.addTab(history_widget, "历史数据")
        
    def setup_realtime_tab(self):
        """设置实时数据标签页"""
        realtime_widget = QWidget()
        layout = QVBoxLayout(realtime_widget)
        
        # 创建表格
        self.realtime_table = QTableWidget()
        self.realtime_table.setColumnCount(6)
        self.realtime_table.setHorizontalHeaderLabels([
            "时间", "价格", "涨跌", "涨跌幅", "成交量", "成交额"
        ])
        
        # 设置表格属性
        self.setup_table_properties(self.realtime_table)
        
        layout.addWidget(self.realtime_table)
        self.tab_widget.addTab(realtime_widget, "实时数据")
        
    def setup_financial_tab(self):
        """设置财务数据标签页"""
        financial_widget = QWidget()
        layout = QVBoxLayout(financial_widget)
        
        # 创建表格
        self.financial_table = QTableWidget()
        self.financial_table.setColumnCount(6)
        self.financial_table.setHorizontalHeaderLabels([
            "报告期", "营业收入", "净利润", "每股收益", "净资产收益率", "市盈率"
        ])
        
        # 设置表格属性
        self.setup_table_properties(self.financial_table)
        
        layout.addWidget(self.financial_table)
        self.tab_widget.addTab(financial_widget, "财务数据")
        
    def setup_technical_tab(self):
        """设置技术指标标签页"""
        technical_widget = QWidget()
        layout = QVBoxLayout(technical_widget)
        
        # 创建表格
        self.technical_table = QTableWidget()
        self.technical_table.setColumnCount(7)
        self.technical_table.setHorizontalHeaderLabels([
            "日期", "MA5", "MA10", "MA20", "MACD", "RSI", "KDJ"
        ])
        
        # 设置表格属性
        self.setup_table_properties(self.technical_table)
        
        layout.addWidget(self.technical_table)
        self.tab_widget.addTab(technical_widget, "技术指标")
        
    def setup_table_properties(self, table):
        """设置表格通用属性"""
        # 设置选择模式
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        
        # 设置表头
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        
        # 设置垂直表头
        table.verticalHeader().setVisible(False)
        
        # 设置交替行颜色
        table.setAlternatingRowColors(True)
        
        # 设置字体
        table.setFont(QFont("Arial", 9))
        
    def load_real_data(self):
        """加载真实数据库数据"""
        try:
            current_table = self.data_source_combo.currentText()
            table_mapping = {
                "股票基本信息": "股票基本信息",
                "股票历史行情": "股票历史行情", 
                "技术指标": "技术指标",
                "资产负债表": "资产负债表",
                "利润表": "利润表",
                "现金流量表": "现金流量表",
                "行业板块": "行业板块",
                "概念板块": "概念板块"
            }
            
            table_name = table_mapping.get(current_table, "股票基本信息")
            
            # 计算偏移量
            offset = self.current_page * self.page_size
            
            # 查询数据
            df = self.db_manager.read_table(
                table_name=table_name,
                limit=self.page_size,
                offset=offset,
                order_by=["股票代码"] if "股票代码" in self.get_table_columns(table_name) else None
            )
            
            # 获取总记录数（用于分页）
            total_df = self.db_manager.read_table(table_name=table_name)
            self.total_records = len(total_df) if not total_df.empty else 0
            
            # 更新表格
            self.update_table_with_data(df)
            
            # 更新分页信息
            self.update_pagination_info()
            
        except Exception as e:
            print(f"加载数据失败: {e}")
            # 如果数据库连接失败，显示示例数据
            self.load_sample_data()
    
    def get_table_columns(self, table_name):
        """获取表的列名"""
        try:
            # 查询一条记录来获取列名
            df = self.db_manager.read_table(table_name=table_name, limit=1)
            return df.columns.tolist() if not df.empty else []
        except:
            return []
    
    def update_table_with_data(self, df):
        """用数据更新表格"""
        if df.empty:
            # 清空表格
            self.history_table.setRowCount(0)
            self.history_table.setColumnCount(0)
            return
        
        # 设置表格行列数
        self.history_table.setRowCount(len(df))
        self.history_table.setColumnCount(len(df.columns))
        
        # 设置表头
        self.history_table.setHorizontalHeaderLabels(df.columns.tolist())
        
        # 填充数据
        for row in range(len(df)):
            for col in range(len(df.columns)):
                value = df.iloc[row, col]
                # 处理不同数据类型
                if value is None or str(value) == 'nan':
                    display_value = ""
                else:
                    display_value = str(value)
                
                item = QTableWidgetItem(display_value)
                self.history_table.setItem(row, col, item)
        
        # 调整列宽
        self.history_table.resizeColumnsToContents()
    
    def update_pagination_info(self):
        """更新分页信息"""
        total_pages = max(1, (self.total_records + self.page_size - 1) // self.page_size)
        current_page_display = self.current_page + 1
        
        self.page_label.setText(f"第 {current_page_display} 页 / 共 {total_pages} 页 (总计 {self.total_records} 条)")
        
        # 更新按钮状态
        self.prev_btn.setEnabled(self.current_page > 0)
        self.next_btn.setEnabled(self.current_page < total_pages - 1)
        
        # 更新跳转控件
        self.goto_page_spin.setMaximum(total_pages)
        self.goto_page_spin.setValue(current_page_display)
    
    def load_sample_data(self):
        """加载示例数据（备用）"""
        # 创建示例数据
        sample_data = []
        for i in range(10):
            sample_data.append({
                "股票代码": f"00000{i+1}",
                "股票名称": f"示例股票{i+1}",
                "当前价格": round(random.uniform(10, 100), 2),
                "涨跌幅": round(random.uniform(-10, 10), 2)
            })
        
        # 更新表格
        self.history_table.setRowCount(len(sample_data))
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels(["股票代码", "股票名称", "当前价格", "涨跌幅"])
        
        for row, data in enumerate(sample_data):
            for col, (key, value) in enumerate(data.items()):
                item = QTableWidgetItem(str(value))
                self.history_table.setItem(row, col, item)
        
        self.history_table.resizeColumnsToContents()
        
        self.load_sample_history_data()
        self.load_sample_realtime_data()
        self.load_sample_financial_data()
        self.load_sample_technical_data()
        
        # 连接信号
        self.setup_connections()
        
    def load_sample_history_data(self):
        """加载示例历史数据"""
        # 生成30天的示例数据
        data = []
        base_price = 100.0
        
        for i in range(30):
            date = datetime.now() - timedelta(days=29-i)
            
            # 生成价格数据
            open_price = base_price + random.uniform(-2, 2)
            high = open_price + random.uniform(0, 3)
            low = open_price - random.uniform(0, 3)
            close = open_price + random.uniform(-2, 2)
            
            # 计算涨跌幅
            if i > 0:
                change_pct = ((close - prev_close) / prev_close) * 100
            else:
                change_pct = 0
                
            # 生成成交量和成交额
            volume = random.randint(50000, 200000)
            amount = volume * close
            
            data.append([
                date.strftime("%Y-%m-%d"),
                f"{open_price:.2f}",
                f"{high:.2f}",
                f"{low:.2f}",
                f"{close:.2f}",
                f"{change_pct:+.2f}%",
                f"{volume:,}",
                f"{amount/10000:.2f}万"
            ])
            
            prev_close = close
            base_price = close
            
        self.populate_table(self.history_table, data)
        
    def load_sample_realtime_data(self):
        """加载示例实时数据"""
        # 生成最近1小时的分钟数据
        data = []
        base_price = 105.50
        
        for i in range(60):
            time = datetime.now() - timedelta(minutes=59-i)
            
            # 生成价格变动
            price_change = random.uniform(-0.5, 0.5)
            current_price = base_price + price_change
            
            change = current_price - base_price
            change_pct = (change / base_price) * 100
            
            volume = random.randint(1000, 5000)
            amount = volume * current_price
            
            data.append([
                time.strftime("%H:%M:%S"),
                f"{current_price:.2f}",
                f"{change:+.2f}",
                f"{change_pct:+.2f}%",
                f"{volume:,}",
                f"{amount/10000:.2f}万"
            ])
            
        self.populate_table(self.realtime_table, data)
        
    def load_sample_financial_data(self):
        """加载示例财务数据"""
        data = [
            ["2023Q4", "125.6亿", "18.9亿", "2.35", "15.2%", "22.5"],
            ["2023Q3", "118.3亿", "17.2亿", "2.14", "14.8%", "24.1"],
            ["2023Q2", "112.8亿", "16.5亿", "2.05", "14.3%", "25.8"],
            ["2023Q1", "108.2亿", "15.8亿", "1.96", "13.9%", "27.2"],
            ["2022Q4", "119.5亿", "17.8亿", "2.21", "14.6%", "23.8"],
        ]
        
        self.populate_table(self.financial_table, data)
        
    def load_sample_technical_data(self):
        """加载示例技术指标数据"""
        data = []
        
        for i in range(20):
            date = datetime.now() - timedelta(days=19-i)
            
            # 生成技术指标数据
            ma5 = 100 + random.uniform(-5, 5)
            ma10 = 100 + random.uniform(-3, 3)
            ma20 = 100 + random.uniform(-2, 2)
            macd = random.uniform(-2, 2)
            rsi = random.uniform(30, 70)
            kdj = random.uniform(20, 80)
            
            data.append([
                date.strftime("%Y-%m-%d"),
                f"{ma5:.2f}",
                f"{ma10:.2f}",
                f"{ma20:.2f}",
                f"{macd:.3f}",
                f"{rsi:.1f}",
                f"{kdj:.1f}"
            ])
            
        self.populate_table(self.technical_table, data)
        
    def populate_table(self, table, data):
        """填充表格数据"""
        table.setRowCount(len(data))
        
        for row, row_data in enumerate(data):
            for col, value in enumerate(row_data):
                item = QTableWidgetItem(str(value))
                
                # 设置数字右对齐
                if col > 0:  # 除了第一列（日期/时间）
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    
                # 设置涨跌颜色
                if "%" in str(value) and col > 0:
                    if "+" in str(value):
                        item.setForeground(QColor(255, 0, 0))  # 红色
                    elif "-" in str(value):
                        item.setForeground(QColor(0, 128, 0))  # 绿色
                        
                table.setItem(row, col, item)
                
    def setup_connections(self):
        """设置信号连接"""
        self.data_type_combo.currentTextChanged.connect(self.on_data_type_changed)
        self.time_range_combo.currentTextChanged.connect(self.on_time_range_changed)
        self.export_btn.clicked.connect(self.export_data)
        self.refresh_btn.clicked.connect(self.refresh_data)
        
    def load_stock_data(self, stock_code):
        """加载股票数据"""
        self.current_stock = stock_code
        
        # TODO: 从数据库或API加载真实股票数据
        # 目前重新生成示例数据
        self.setup_sample_data()
        
        print(f"加载股票数据: {stock_code}")
        
    def on_data_source_changed(self, data_source):
        """数据源改变时的处理"""
        self.current_page = 0  # 重置到第一页
        self.load_real_data()
    
    def on_page_size_changed(self, page_size):
        """每页记录数改变时的处理"""
        self.page_size = int(page_size)
        self.current_page = 0  # 重置到第一页
        self.load_real_data()
    
    def prev_page(self):
        """上一页"""
        if self.current_page > 0:
            self.current_page -= 1
            self.load_real_data()
    
    def next_page(self):
        """下一页"""
        total_pages = max(1, (self.total_records + self.page_size - 1) // self.page_size)
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self.load_real_data()
    
    def goto_page(self, page_num):
        """跳转到指定页面"""
        target_page = page_num - 1  # 转换为0基索引
        total_pages = max(1, (self.total_records + self.page_size - 1) // self.page_size)
        
        if 0 <= target_page < total_pages and target_page != self.current_page:
            self.current_page = target_page
            self.load_real_data()
        
    def export_data(self):
        """导出数据"""
        # TODO: 实现数据导出功能
        print("导出数据")
        
    def refresh_data(self):
        """刷新数据"""
        self.load_real_data()
        self.data_updated.emit()
        print("数据已刷新")
        
    def get_current_table(self):
        """获取当前显示的表格"""
        current_index = self.tab_widget.currentIndex()
        
        if current_index == 0:
            return self.history_table
        elif current_index == 1:
            return self.realtime_table
        elif current_index == 2:
            return self.financial_table
        elif current_index == 3:
            return self.technical_table
        else:
            return None
            
    def get_selected_data(self):
        """获取选中的数据"""
        current_table = self.get_current_table()
        if not current_table:
            return None
            
        selected_rows = current_table.selectionModel().selectedRows()
        if not selected_rows:
            return None
            
        row = selected_rows[0].row()
        data = []
        
        for col in range(current_table.columnCount()):
            item = current_table.item(row, col)
            if item:
                data.append(item.text())
            else:
                data.append("")
                
        return data