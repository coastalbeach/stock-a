#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据视图模块
提供数据浏览和查询界面，展示股票、指数、板块等数据
参考同花顺iFinder和Winder的专业设计风格
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableView, 
                             QComboBox, QPushButton, QLabel, QLineEdit,
                             QDateEdit, QGroupBox, QFormLayout, QHeaderView,
                             QSplitter, QTabWidget, QMessageBox, QCheckBox,
                             QProgressBar, QStatusBar, QToolButton, QMenu,
                             QDialog, QFileDialog, QApplication)
from PyQt6.QtCore import Qt, QSortFilterProxyModel, QDate, QThread, pyqtSignal
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QIcon, QAction, QColor

# 导入数据存储模块
import sys
import os
import pandas as pd
import numpy as np
import datetime
import traceback
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

class DataLoaderThread(QThread):
    """数据加载线程，用于异步加载数据，避免界面卡顿"""
    
    # 定义信号
    data_loaded = pyqtSignal(pd.DataFrame)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(int)
    
    def __init__(self, data_type, data_category, query_params=None):
        super().__init__()
        self.data_type = data_type
        self.data_category = data_category
        self.query_params = query_params if query_params else {}
        self.pg_manager = None
        self.redis_manager = None
    
    def run(self):
        """线程运行函数"""
        try:
            # 连接数据库
            self.pg_manager = PostgreSQLManager()
            self.redis_manager = RedisManager()
            
            # 根据数据类型和类别获取数据
            if self.data_type == "个股数据":
                df = self.get_stock_data()
            elif self.data_type == "指数数据":
                df = self.get_index_data()
            elif self.data_type == "板块数据":
                df = self.get_sector_data()
            elif self.data_type == "市场数据":
                df = self.get_market_data()
            else:
                df = pd.DataFrame()
            
            # 发送数据加载完成信号
            self.data_loaded.emit(df)
            
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
    
    def get_stock_data(self):
        """获取个股数据"""
        category = self.data_category
        params = self.query_params
        
        # 检查Redis缓存
        cache_key = f"stock:{category}:{params.get('stock_code', '')}"
        cached_data = self.redis_manager.get_value(cache_key)
        if cached_data is not None:
            return cached_data
        
        # 从PostgreSQL获取数据
        if category == "基本信息":
            # 先检查数据库中是否有数据
            sql = """SELECT * FROM "股票基本信息" """
            if 'stock_code' in params and params['stock_code']:
                sql += f"WHERE \"股票代码\" LIKE '%{params['stock_code']}%' OR \"股票名称\" LIKE '%{params['stock_code']}%'"
            
            df = self.pg_manager.query_df(sql)
            
            # 如果数据库中没有数据，则从akshare获取
            if df.empty:
                try:
                    # 使用akshare获取A股上市公司基本信息
                    df = ak.stock_info_a_code_name()
                    # 重命名列以符合中文命名规范
                    df.columns = ["股票代码", "股票名称"]
                    
                    # 获取行业信息
                    industry_df = ak.stock_industry()
                    # 合并数据
                    df = pd.merge(df, industry_df, left_on="股票代码", right_on="代码", how="left")
                    df = df[["股票代码", "股票名称", "行业"]]
                    
                    # 保存到数据库
                    self.pg_manager.create_table("股票基本信息", {
                        "股票代码": "VARCHAR(10) PRIMARY KEY",
                        "股票名称": "VARCHAR(50) NOT NULL",
                        "行业": "VARCHAR(50)"
                    })
                    self.pg_manager.insert_df("股票基本信息", df)
                except Exception as e:
                    print(f"获取股票基本信息失败: {e}")
            
        elif category == "日线行情":
            stock_code = params.get('stock_code', '')
            start_date = params.get('start_date', '')
            end_date = params.get('end_date', '')
            
            if not stock_code:
                return pd.DataFrame()
            
            # 构建SQL查询
            sql = f"""SELECT * FROM \"股票日线行情\" 
                   WHERE \"股票代码\" = '{stock_code}' """
            
            if start_date and end_date:
                sql += f"AND \"交易日期\" BETWEEN '{start_date}' AND '{end_date}' "
            
            sql += "ORDER BY \"交易日期\" DESC"
            
            df = self.pg_manager.query_df(sql)
            
            # 如果数据库中没有数据，则从akshare获取
            if df.empty:
                try:
                    # 使用akshare获取股票日线数据
                    df = ak.stock_zh_a_hist(symbol=stock_code, start_date=start_date, end_date=end_date)
                    # 重命名列以符合中文命名规范
                    df.columns = ["交易日期", "开盘价", "最高价", "最低价", "收盘价", "涨跌幅", "成交量", "成交额", "振幅", "换手率"]
                    # 添加股票代码列
                    df["股票代码"] = stock_code
                    
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
                except Exception as e:
                    print(f"获取股票日线行情失败: {e}")
        
        elif category == "财务数据":
            stock_code = params.get('stock_code', '')
            if not stock_code:
                return pd.DataFrame()
                
            # 构建SQL查询
            sql = f"""SELECT * FROM \"股票财务数据\" 
                   WHERE \"股票代码\" = '{stock_code}' 
                   ORDER BY \"报告期\" DESC"""
            
            df = self.pg_manager.query_df(sql)
            
            # 如果数据库中没有数据，则从akshare获取
            if df.empty:
                try:
                    # 使用akshare获取财务数据
                    income_df = ak.stock_financial_report_sina(stock=stock_code, symbol="利润表")
                    balance_df = ak.stock_financial_report_sina(stock=stock_code, symbol="资产负债表")
                    cash_flow_df = ak.stock_financial_report_sina(stock=stock_code, symbol="现金流量表")
                    
                    # 处理数据，合并报表
                    # 这里简化处理，实际应用中需要更复杂的数据处理
                    df = income_df[["报表日期", "营业收入", "净利润"]]
                    df.columns = ["报告期", "营业收入", "净利润"]
                    df["股票代码"] = stock_code
                    
                    # 保存到数据库
                    self.pg_manager.create_table("股票财务数据", {
                        "股票代码": "VARCHAR(10) NOT NULL",
                        "报告期": "DATE NOT NULL",
                        "营业收入": "NUMERIC(20,2)",
                        "净利润": "NUMERIC(20,2)",
                        "PRIMARY KEY": "(股票代码, 报告期)"
                    })
                    self.pg_manager.insert_df("股票财务数据", df)
                except Exception as e:
                    print(f"获取股票财务数据失败: {e}")
        
        # 缓存数据到Redis
        if not df.empty:
            self.redis_manager.set_value(cache_key, df, expire=3600)  # 缓存1小时
        
        return df
    
    def get_index_data(self):
        """获取指数数据"""
        category = self.data_category
        params = self.query_params
        
        # 检查Redis缓存
        cache_key = f"index:{category}:{params.get('index_code', '')}"
        cached_data = self.redis_manager.get_value(cache_key)
        if cached_data is not None:
            return cached_data
        
        # 从PostgreSQL获取数据
        if category == "指数基本信息":
            sql = """SELECT * FROM \"指数基本信息\" """
            if 'index_code' in params and params['index_code']:
                sql += f"WHERE \"指数代码\" LIKE '%{params['index_code']}%' OR \"指数名称\" LIKE '%{params['index_code']}%'"
            
            df = self.pg_manager.query_df(sql)
            
            # 如果数据库中没有数据，则从akshare获取
            if df.empty:
                try:
                    # 使用akshare获取指数基本信息
                    df = ak.index_stock_info()
                    # 重命名列以符合中文命名规范
                    df.columns = ["指数代码", "指数名称", "发布日期", "基日", "基点"]
                    
                    # 保存到数据库
                    self.pg_manager.create_table("指数基本信息", {
                        "指数代码": "VARCHAR(20) PRIMARY KEY",
                        "指数名称": "VARCHAR(50) NOT NULL",
                        "发布日期": "DATE",
                        "基日": "DATE",
                        "基点": "NUMERIC(10,2)"
                    })
                    self.pg_manager.insert_df("指数基本信息", df)
                except Exception as e:
                    print(f"获取指数基本信息失败: {e}")
        
        elif category == "指数行情":
            index_code = params.get('index_code', '')
            start_date = params.get('start_date', '')
            end_date = params.get('end_date', '')
            
            if not index_code:
                return pd.DataFrame()
            
            # 构建SQL查询
            sql = f"""SELECT * FROM \"指数行情\" 
                   WHERE \"指数代码\" = '{index_code}' """
            
            if start_date and end_date:
                sql += f"AND \"交易日期\" BETWEEN '{start_date}' AND '{end_date}' "
            
            sql += "ORDER BY \"交易日期\" DESC"
            
            df = self.pg_manager.query_df(sql)
            
            # 如果数据库中没有数据，则从akshare获取
            if df.empty:
                try:
                    # 使用akshare获取指数行情数据
                    df = ak.index_zh_a_hist(symbol=index_code, start_date=start_date, end_date=end_date)
                    # 重命名列以符合中文命名规范
                    df.columns = ["交易日期", "开盘点位", "最高点位", "最低点位", "收盘点位", "涨跌幅", "成交量", "成交额"]
                    # 添加指数代码列
                    df["指数代码"] = index_code
                    
                    # 保存到数据库
                    self.pg_manager.create_table("指数行情", {
                        "指数代码": "VARCHAR(20) NOT NULL",
                        "交易日期": "DATE NOT NULL",
                        "开盘点位": "NUMERIC(10,2)",
                        "最高点位": "NUMERIC(10,2)",
                        "最低点位": "NUMERIC(10,2)",
                        "收盘点位": "NUMERIC(10,2)",
                        "涨跌幅": "NUMERIC(10,2)",
                        "成交量": "NUMERIC(20,0)",
                        "成交额": "NUMERIC(20,2)",
                        "PRIMARY KEY": "(指数代码, 交易日期)"
                    })
                    self.pg_manager.insert_df("指数行情", df)
                except Exception as e:
                    print(f"获取指数行情失败: {e}")
        
        # 缓存数据到Redis
        if not df.empty:
            self.redis_manager.set_value(cache_key, df, expire=3600)  # 缓存1小时
        
        return df
    
    def get_sector_data(self):
        """获取板块数据"""
        category = self.data_category
        params = self.query_params
        
        # 检查Redis缓存
        cache_key = f"sector:{category}"
        cached_data = self.redis_manager.get_value(cache_key)
        if cached_data is not None:
            return cached_data
        
        # 从PostgreSQL获取数据
        if category == "行业板块":
            sql = """SELECT * FROM \"行业板块\" """
            df = self.pg_manager.query_df(sql)
            
            # 如果数据库中没有数据，则从akshare获取
            if df.empty:
                try:
                    # 使用akshare获取行业板块数据
                    df = ak.stock_sector_spot(indicator="行业")
                    # 重命名列以符合中文命名规范
                    df.columns = ["板块名称", "涨跌幅", "总市值", "换手率", "上涨家数", "下跌家数", "领涨股票", "领涨股票代码", "领涨股票涨跌幅"]
                    
                    # 保存到数据库
                    self.pg_manager.create_table("行业板块", {
                        "板块名称": "VARCHAR(50) PRIMARY KEY",
                        "涨跌幅": "NUMERIC(10,2)",
                        "总市值": "NUMERIC(20,2)",
                        "换手率": "NUMERIC(10,2)",
                        "上涨家数": "INTEGER",
                        "下跌家数": "INTEGER",
                        "领涨股票": "VARCHAR(50)",
                        "领涨股票代码": "VARCHAR(10)",
                        "领涨股票涨跌幅": "NUMERIC(10,2)"
                    })
                    self.pg_manager.insert_df("行业板块", df)
                except Exception as e:
                    print(f"获取行业板块数据失败: {e}")
        
        elif category == "概念板块":
            sql = """SELECT * FROM \"概念板块\" """
            df = self.pg_manager.query_df(sql)
            
            # 如果数据库中没有数据，则从akshare获取
            if df.empty:
                try:
                    # 使用akshare获取概念板块数据
                    df = ak.stock_sector_spot(indicator="概念")
                    # 重命名列以符合中文命名规范
                    df.columns = ["板块名称", "涨跌幅", "总市值", "换手率", "上涨家数", "下跌家数", "领涨股票", "领涨股票代码", "领涨股票涨跌幅"]
                    
                    # 保存到数据库
                    self.pg_manager.create_table("概念板块", {
                        "板块名称": "VARCHAR(50) PRIMARY KEY",
                        "涨跌幅": "NUMERIC(10,2)",
                        "总市值": "NUMERIC(20,2)",
                        "换手率": "NUMERIC(10,2)",
                        "上涨家数": "INTEGER",
                        "下跌家数": "INTEGER",
                        "领涨股票": "VARCHAR(50)",
                        "领涨股票代码": "VARCHAR(10)",
                        "领涨股票涨跌幅": "NUMERIC(10,2)"
                    })
                    self.pg_manager.insert_df("概念板块", df)
                except Exception as e:
                    print(f"获取概念板块数据失败: {e}")
        
        # 缓存数据到Redis
        if not df.empty:
            self.redis_manager.set_value(cache_key, df, expire=1800)  # 缓存30分钟
        
        return df
    
    def get_market_data(self):
        """获取市场数据"""
        category = self.data_category
        params = self.query_params
        
        # 检查Redis缓存
        cache_key = f"market:{category}"
        cached_data = self.redis_manager.get_value(cache_key)
        if cached_data is not None:
            return cached_data
        
        # 从PostgreSQL获取数据
        if category == "市场总貌":
            # 获取当前日期
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            
            sql = f"""SELECT * FROM \"市场总貌\" WHERE \"交易日期\" = '{today}'"""
            df = self.pg_manager.query_df(sql)
            
            # 如果数据库中没有数据，则从akshare获取
            if df.empty:
                try:
                    # 使用akshare获取市场总貌数据
                    df = ak.stock_zh_a_spot_em()
                    # 重命名列以符合中文命名规范
                    df.columns = ["股票代码", "股票名称", "最新价", "涨跌幅", "涨跌额", "成交量", "成交额", "振幅", "最高价", "最低价", "今开价", "昨收价", "量比", "换手率", "市盈率", "市净率"]
                    # 添加交易日期列
                    df["交易日期"] = today
                    
                    # 保存到数据库
                    self.pg_manager.create_table("市场总貌", {
                        "股票代码": "VARCHAR(10) NOT NULL",
                        "股票名称": "VARCHAR(50) NOT NULL",
                        "最新价": "NUMERIC(10,2)",
                        "涨跌幅": "NUMERIC(10,2)",
                        "涨跌额": "NUMERIC(10,2)",
                        "成交量": "NUMERIC(20,0)",
                        "成交额": "NUMERIC(20,2)",
                        "振幅": "NUMERIC(10,2)",
                        "最高价": "NUMERIC(10,2)",
                        "最低价": "NUMERIC(10,2)",
                        "今开价": "NUMERIC(10,2)",
                        "昨收价": "NUMERIC(10,2)",
                        "量比": "NUMERIC(10,2)",
                        "换手率": "NUMERIC(10,2)",
                        "市盈率": "NUMERIC(10,2)",
                        "市净率": "NUMERIC(10,2)",
                        "交易日期": "DATE NOT NULL",
                        "PRIMARY KEY": "(股票代码, 交易日期)"
                    })
                    self.pg_manager.insert_df("市场总貌", df)
                except Exception as e:
                    print(f"获取市场总貌数据失败: {e}")
        
        elif category == "龙虎榜":
            # 获取当前日期
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            
            sql = f"""SELECT * FROM \"龙虎榜\" WHERE \"交易日期\" = '{today}'"""
            df = self.pg_manager.query_df(sql)
            
            # 如果数据库中没有数据，则从akshare获取
            if df.empty:
                try:
                    # 使用akshare获取龙虎榜数据
                    df = ak.stock_lhb_detail_em(trade_date=today)
                    if not df.empty:
                        # 重命名列以符合中文命名规范
                        df.columns = ["序号", "股票代码", "股票名称", "收盘价", "涨跌幅", "龙虎榜净买额", "龙虎榜买入额", "龙虎榜卖出额", "龙虎榜成交额", "总成交额", "龙虎榜成交额占比", "换手率", "上榜原因"]
                        # 添加交易日期列
                        df["交易日期"] = today
                        
                        # 保存到数据库
                        self.pg_manager.create_table("龙虎榜", {
                            "序号": "INTEGER",
                            "股票代码": "VARCHAR(10) NOT NULL",
                            "股票名称": "VARCHAR(50) NOT NULL",
                            "收盘价": "NUMERIC(10,2)",
                            "涨跌幅": "NUMERIC(10,2)",
                            "龙虎榜净买额": "NUMERIC(20,2)",
                            "龙虎榜买入额": "NUMERIC(20,2)",
                            "龙虎榜卖出额": "NUMERIC(20,2)",
                            "龙虎榜成交额": "NUMERIC(20,2)",
                            "总成交额": "NUMERIC(20,2)",
                            "龙虎榜成交额占比": "NUMERIC(10,2)",
                            "换手率": "NUMERIC(10,2)",
                            "上榜原因": "VARCHAR(100)",
                            "交易日期": "DATE NOT NULL",
                            "PRIMARY KEY": "(股票代码, 交易日期)"
                        })
                        self.pg_manager.insert_df("龙虎榜", df)
                except Exception as e:
                    print(f"获取龙虎榜数据失败: {e}")
        
        # 缓存数据到Redis
        if not df.empty:
            self.redis_manager.set_value(cache_key, df, expire=1800)  # 缓存30分钟
        
        return df


class DataView(QWidget):
    """数据浏览和查询界面"""
    
    def __init__(self):
        super().__init__()
        
        # 初始化数据库连接
        self.pg_manager = None
        self.redis_manager = None
        self.init_db_connection()
        
        # 初始化UI组件
        self.init_ui()
        
        # 初始化数据模型
        self.init_models()
        
        # 连接信号和槽
        self.connect_signals_slots()
        
        # 加载初始数据
        self.load_initial_data()
    
    def init_db_connection(self):
        """初始化数据库连接"""
        try:
            self.pg_manager = PostgreSQLManager()
            self.redis_manager = RedisManager()
        except Exception as e:
            QMessageBox.critical(self, "数据库连接错误", f"连接数据库失败: {str(e)}")
            print(f"数据库连接错误: {e}")
    
    def init_ui(self):
        """初始化UI组件"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # 创建顶部工具栏
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(10)
        
        # 数据类型下拉框
        self.data_type_combo = QComboBox()
        self.data_type_combo.addItems(["个股数据", "指数数据", "板块数据", "市场数据"])
        self.data_type_combo.setMinimumWidth(120)
        toolbar_layout.addWidget(QLabel("数据类型:"))
        toolbar_layout.addWidget(self.data_type_combo)
        
        # 具体数据类别下拉框
        self.data_category_combo = QComboBox()
        self.data_category_combo.setMinimumWidth(120)
        toolbar_layout.addWidget(QLabel("数据类别:"))
        toolbar_layout.addWidget(self.data_category_combo)
        
        # 添加弹性空间
        toolbar_layout.addStretch(1)
        
        # 刷新按钮
        self.refresh_button = QPushButton("刷新数据")
        self.refresh_button.setMinimumWidth(100)
        toolbar_layout.addWidget(self.refresh_button)
        
        # 导出按钮
        self.export_button = QPushButton("导出数据")
        self.export_button.setMinimumWidth(100)
        toolbar_layout.addWidget(self.export_button)
        
        # 添加工具栏到主布局
        main_layout.addLayout(toolbar_layout)
        
        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)
        main_layout.addWidget(splitter, 1)  # 设置拉伸因子
        
        # 创建查询条件区域
        query_widget = QWidget()
        query_layout = QVBoxLayout(query_widget)
        query_layout.setContentsMargins(5, 5, 5, 5)
        
        # 查询条件组框
        query_group = QGroupBox("查询条件")
        query_form_layout = QFormLayout()
        query_form_layout.setSpacing(10)
        
        # 股票代码/名称查询
        code_layout = QHBoxLayout()
        self.stock_code_edit = QLineEdit()
        self.stock_code_edit.setPlaceholderText("输入股票代码或名称")
        code_layout.addWidget(self.stock_code_edit)
        
        # 添加股票选择按钮
        self.stock_select_button = QToolButton()
        self.stock_select_button.setText("...")
        self.stock_select_button.setToolTip("选择股票")
        code_layout.addWidget(self.stock_select_button)
        
        query_form_layout.addRow("股票代码/名称:", code_layout)
        
        # 日期范围查询
        date_layout = QHBoxLayout()
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QDate.currentDate().addMonths(-1))
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QDate.currentDate())
        date_layout.addWidget(self.start_date_edit)
        date_layout.addWidget(QLabel("至"))
        date_layout.addWidget(self.end_date_edit)
        query_form_layout.addRow("日期范围:", date_layout)
        
        # 高级条件
        self.condition_edit = QLineEdit()
        self.condition_edit.setPlaceholderText("输入高级查询条件")
        query_form_layout.addRow("高级条件:", self.condition_edit)
        
        # 查询按钮
        buttons_layout = QHBoxLayout()
        self.query_button = QPushButton("查询")
        self.query_button.setMinimumWidth(100)
        self.clear_button = QPushButton("清除条件")
        self.clear_button.setMinimumWidth(100)
        buttons_layout.addWidget(self.query_button)
        buttons_layout.addWidget(self.clear_button)
        buttons_layout.addStretch(1)
        query_form_layout.addRow("", buttons_layout)
        
        # 设置查询条件组框布局
        query_group.setLayout(query_form_layout)
        query_layout.addWidget(query_group)
        
        # 添加查询条件区域到分割器
        splitter.addWidget(query_widget)
        
        # 创建数据显示区域
        data_widget = QWidget()
        data_layout = QVBoxLayout(data_widget)
        data_layout.setContentsMargins(5, 5, 5, 5)
        
        # 创建数据表格
        self.table_view = QTableView()
        self.table_view.setSortingEnabled(True)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        data_layout.addWidget(self.table_view)
        
        # 添加数据显示区域到分割器
        splitter.addWidget(data_widget)
        
        # 设置分割器比例
        splitter.setSizes([150, 450])
        
        # 创建状态栏
        status_layout = QHBoxLayout()
        
        # 状态标签
        self.status_label = QLabel("就绪")
        status_layout.addWidget(self.status_label)
        
        # 添加弹性空间
        status_layout.addStretch(1)
        
        # 记录数量标签
        self.record_count_label = QLabel("记录数: 0")
        status_layout.addWidget(self.record_count_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.progress_bar)
        
        # 添加状态栏到主布局
        main_layout.addLayout(status_layout)
    
    def init_models(self):
        """初始化数据模型"""
        # 创建表格数据模型
        self.table_model = QStandardItemModel()
        
        # 创建排序过滤代理模型
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.table_model)
        
        # 设置表格视图的模型
        self.table_view.setModel(self.proxy_model)
        
        # 数据加载线程
        self.data_loader_thread = None
    
    def connect_signals_slots(self):
        """连接信号和槽"""
        # 数据类型变化时更新数据类别
        self.data_type_combo.currentIndexChanged.connect(self.update_data_categories)
        
        # 刷新按钮点击事件
        self.refresh_button.clicked.connect(self.refresh_data)
        
        # 查询按钮点击事件
        self.query_button.clicked.connect(self.query_data)
        
        # 清除条件按钮点击事件
        self.clear_button.clicked.connect(self.clear_query_conditions)
        
        # 导出按钮点击事件
        self.export_button.clicked.connect(self.export_data)
        
        # 股票选择按钮点击事件
        self.stock_select_button.clicked.connect(self.show_stock_selector)
        
        # 表格右键菜单
        self.table_view.customContextMenuRequested.connect(self.show_table_context_menu)
    
    def load_initial_data(self):
        """加载初始数据"""
        # 更新数据类别
        self.update_data_categories()
        
        # 加载默认数据 - 股票基本信息
        self.data_type_combo.setCurrentText("个股数据")
        self.data_category_combo.setCurrentText("基本信息")
        self.refresh_data()
    
    def update_data_categories(self, index=0):
        """根据选择的数据类型更新数据类别"""
        self.data_category_combo.clear()
        
        # 根据选择的数据类型设置对应的数据类别
        data_type = self.data_type_combo.currentText()
        
        if data_type == "个股数据":
            self.data_category_combo.addItems(["基本信息", "日线行情", "分钟行情", "财务数据", "公告信息"])
            # 更新查询条件标签
            self.stock_code_edit.setPlaceholderText("输入股票代码或名称")
            # 启用日期范围
            self.start_date_edit.setEnabled(True)
            self.end_date_edit.setEnabled(True)
        elif data_type == "指数数据":
            self.data_category_combo.addItems(["指数基本信息", "指数行情", "指数成分股"])
            # 更新查询条件标签
            self.stock_code_edit.setPlaceholderText("输入指数代码或名称")
            # 启用日期范围
            self.start_date_edit.setEnabled(True)
            self.end_date_edit.setEnabled(True)
        elif data_type == "板块数据":
            self.data_category_combo.addItems(["行业板块", "概念板块", "地区板块"])
            # 更新查询条件标签
            self.stock_code_edit.setPlaceholderText("输入板块名称")
            # 板块数据不需要日期范围
            self.start_date_edit.setEnabled(False)
            self.end_date_edit.setEnabled(False)
        elif data_type == "市场数据":
            self.data_category_combo.addItems(["市场总貌", "融资融券", "沪深港通", "龙虎榜"])
            # 更新查询条件标签
            self.stock_code_edit.setPlaceholderText("输入筛选条件")
            # 启用日期范围
            self.start_date_edit.setEnabled(True)
            self.end_date_edit.setEnabled(True)
    
    def refresh_data(self):
        """刷新数据"""
        # 获取当前选择的数据类型和类别
        data_type = self.data_type_combo.currentText()
        data_category = self.data_category_combo.currentText()
        
        # 更新状态
        self.status_label.setText(f"正在加载{data_type}-{data_category}数据...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 禁用按钮，避免重复操作
        self.refresh_button.setEnabled(False)
        self.query_button.setEnabled(False)
        
        # 创建并启动数据加载线程
        self.data_loader_thread = DataLoaderThread(data_type, data_category)
        self.data_loader_thread.data_loaded.connect(self.on_data_loaded)
        self.data_loader_thread.error_occurred.connect(self.on_data_error)
        self.data_loader_thread.progress_updated.connect(self.progress_bar.setValue)
        self.data_loader_thread.start()
    
    def query_data(self):
        """查询数据"""
        # 获取查询条件
        stock_code = self.stock_code_edit.text().strip()
        start_date = self.start_date_edit.date().toString("yyyy-MM-dd")
        end_date = self.end_date_edit.date().toString("yyyy-MM-dd")
        condition = self.condition_edit.text().strip()
        
        # 获取当前选择的数据类型和类别
        data_type = self.data_type_combo.currentText()
        data_category = self.data_category_combo.currentText()
        
        # 构建查询参数
        query_params = {
            'stock_code': stock_code,
            'index_code': stock_code,  # 用于指数查询
            'start_date': start_date,
            'end_date': end_date,
            'condition': condition
        }
        
        # 更新状态
        self.status_label.setText(f"正在查询{data_type}-{data_category}数据...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 禁用按钮，避免重复操作
        self.refresh_button.setEnabled(False)
        self.query_button.setEnabled(False)
        
        # 创建并启动数据加载线程
        self.data_loader_thread = DataLoaderThread(data_type, data_category, query_params)
        self.data_loader_thread.data_loaded.connect(self.on_data_loaded)
        self.data_loader_thread.error_occurred.connect(self.on_data_error)
        self.data_loader_thread.progress_updated.connect(self.progress_bar.setValue)
        self.data_loader_thread.start()
    
    def on_data_loaded(self, df):
        """数据加载完成回调"""
        # 更新表格模型
        self.update_table_model(df)
        
        # 更新状态
        self.status_label.setText("数据加载完成")
        self.record_count_label.setText(f"记录数: {len(df)}")
        self.progress_bar.setVisible(False)
        
        # 恢复按钮状态
        self.refresh_button.setEnabled(True)
        self.query_button.setEnabled(True)
    
    def on_data_error(self, error_msg):
        """数据加载错误回调"""
        # 显示错误信息
        QMessageBox.critical(self, "数据加载错误", error_msg)
        
        # 更新状态
        self.status_label.setText("数据加载失败")
        self.progress_bar.setVisible(False)
        
        # 恢复按钮状态
        self.refresh_button.setEnabled(True)
        self.query_button.setEnabled(True)
    
    def update_table_model(self, df):
        """更新表格模型"""
        # 清空现有数据
        self.table_model.clear()
        
        if df.empty:
            self.status_label.setText("没有找到符合条件的数据")
            return
        
        # 设置表头
        headers = df.columns.tolist()
        self.table_model.setHorizontalHeaderLabels(headers)
        
        # 添加数据行
        for i in range(len(df)):
            row_data = df.iloc[i]
            items = []
            
            for col in headers:
                value = row_data[col]
                
                # 根据数据类型设置单元格格式
                if pd.isna(value):
                    item = QStandardItem("")
                elif isinstance(value, (int, float)):
                    # 数值类型右对齐
                    item = QStandardItem(f"{value}")
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    
                    # 涨跌幅设置颜色
                    if "涨跌幅" in col and value != 0:
                        if value > 0:
                            item.setForeground(QColor("red"))
                        else:
                            item.setForeground(QColor("green"))
                else:
                    item = QStandardItem(f"{value}")
                
                items.append(item)
            
            self.table_model.appendRow(items)
        
        # 调整表格列宽
        self.table_view.resizeColumnsToContents()
    
    def clear_query_conditions(self):
        """清除查询条件"""
        self.stock_code_edit.clear()
        self.start_date_edit.setDate(QDate.currentDate().addMonths(-1))
        self.end_date_edit.setDate(QDate.currentDate())
        self.condition_edit.clear()
    
    def export_data(self):
        """导出数据"""
        # 检查是否有数据可导出
        if self.table_model.rowCount() == 0:
            QMessageBox.warning(self, "导出警告", "没有数据可导出")
            return
        
        # 获取当前数据类型和类别
        data_type = self.data_type_combo.currentText()
        data_category = self.data_category_combo.currentText()
        
        # 选择保存文件
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "导出数据",
            f"{data_type}_{data_category}_{QDate.currentDate().toString('yyyyMMdd')}.csv",
            "CSV文件 (*.csv);;Excel文件 (*.xlsx)"
        )
        
        if not file_name:
            return
        
        try:
            # 将表格数据转换为DataFrame
            headers = [self.table_model.headerData(i, Qt.Orientation.Horizontal) for i in range(self.table_model.columnCount())]
            data = []
            
            for row in range(self.table_model.rowCount()):
                row_data = []
                for col in range(self.table_model.columnCount()):
                    item = self.table_model.item(row, col)
                    row_data.append(item.text() if item else "")
                data.append(row_data)
            
            df = pd.DataFrame(data, columns=headers)
            
            # 根据文件扩展名保存
            if file_name.endswith(".csv"):
                df.to_csv(file_name, index=False, encoding="utf-8-sig")
            elif file_name.endswith(".xlsx"):
                df.to_excel(file_name, index=False)
            
            QMessageBox.information(self, "导出成功", f"数据已成功导出到: {file_name}")
            
        except Exception as e:
            QMessageBox.critical(self, "导出错误", f"导出数据时发生错误: {str(e)}")
    
    def show_stock_selector(self):
        """显示股票选择器"""
        # 获取当前数据类型
        data_type = self.data_type_combo.currentText()
        
        # 根据数据类型显示不同的选择器
        if data_type == "个股数据":
            # 从数据库获取股票列表
            try:
                sql = """SELECT "股票代码", "股票名称" FROM "股票基本信息" ORDER BY "股票代码"""
                df = self.pg_manager.query_df(sql)
                
                if df.empty:
                    QMessageBox.warning(self, "数据缺失", "股票基本信息数据不存在，请先刷新股票基本信息")
                    return
                
                # 创建选择对话框
                dialog = QDialog(self)
                dialog.setWindowTitle("选择股票")
                dialog.setMinimumSize(400, 500)
                
                layout = QVBoxLayout(dialog)
                
                # 搜索框
                search_layout = QHBoxLayout()
                search_edit = QLineEdit()
                search_edit.setPlaceholderText("输入股票代码或名称搜索")
                search_layout.addWidget(search_edit)
                layout.addLayout(search_layout)
                
                # 股票列表
                stock_list = QTableView()
                stock_list.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
                stock_list.setSelectionMode(QTableView.SelectionMode.SingleSelection)
                stock_list.setAlternatingRowColors(True)
                
                # 创建模型
                model = QStandardItemModel()
                model.setHorizontalHeaderLabels(["股票代码", "股票名称"])
                
                # 添加数据
                for i in range(len(df)):
                    code = QStandardItem(df.iloc[i]["股票代码"])
                    name = QStandardItem(df.iloc[i]["股票名称"])
                    model.appendRow([code, name])
                
                # 创建过滤代理模型
                proxy_model = QSortFilterProxyModel()
                proxy_model.setSourceModel(model)
                proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
                
                # 设置模型
                stock_list.setModel(proxy_model)
                stock_list.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
                layout.addWidget(stock_list)
                
                # 按钮
                button_layout = QHBoxLayout()
                ok_button = QPushButton("确定")
                cancel_button = QPushButton("取消")
                button_layout.addWidget(ok_button)
                button_layout.addWidget(cancel_button)
                layout.addLayout(button_layout)
                
                # 连接信号
                def on_search_changed(text):
                    proxy_model.setFilterRegularExpression(text)
                    proxy_model.setFilterKeyColumn(-1)  # 搜索所有列
                
                def on_ok_clicked():
                    indexes = stock_list.selectedIndexes()
                    if indexes:
                        row = proxy_model.mapToSource(indexes[0]).row()
                        code = model.item(row, 0).text()
                        self.stock_code_edit.setText(code)
                    dialog.accept()
                
                def on_cancel_clicked():
                    dialog.reject()
                
                def on_double_clicked(index):
                    row = proxy_model.mapToSource(index).row()
                    code = model.item(row, 0).text()
                    self.stock_code_edit.setText(code)
                    dialog.accept()
                
                search_edit.textChanged.connect(on_search_changed)
                ok_button.clicked.connect(on_ok_clicked)
                cancel_button.clicked.connect(on_cancel_clicked)
                stock_list.doubleClicked.connect(on_double_clicked)
                
                # 显示对话框
                dialog.exec()
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"获取股票列表失败: {str(e)}")
        
        elif data_type == "指数数据":
            # 类似实现指数选择器
            try:
                sql = """SELECT "指数代码", "指数名称" FROM "指数基本信息" ORDER BY "指数代码"""
                df = self.pg_manager.query_df(sql)
                
                if df.empty:
                    QMessageBox.warning(self, "数据缺失", "指数基本信息数据不存在，请先刷新指数基本信息")
                    return
                
                # 创建选择对话框
                dialog = QDialog(self)
                dialog.setWindowTitle("选择指数")
                dialog.setMinimumSize(400, 500)
                
                layout = QVBoxLayout(dialog)
                
                # 搜索框
                search_layout = QHBoxLayout()
                search_edit = QLineEdit()
                search_edit.setPlaceholderText("输入指数代码或名称搜索")
                search_layout.addWidget(search_edit)
                layout.addLayout(search_layout)
                
                # 指数列表
                index_list = QTableView()
                index_list.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
                index_list.setSelectionMode(QTableView.SelectionMode.SingleSelection)
                index_list.setAlternatingRowColors(True)
                
                # 创建模型
                model = QStandardItemModel()
                model.setHorizontalHeaderLabels(["指数代码", "指数名称"])
                
                # 添加数据
                for i in range(len(df)):
                    code = QStandardItem(df.iloc[i]["指数代码"])
                    name = QStandardItem(df.iloc[i]["指数名称"])
                    model.appendRow([code, name])
                
                # 创建过滤代理模型
                proxy_model = QSortFilterProxyModel()
                proxy_model.setSourceModel(model)
                proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
                
                # 设置模型
                index_list.setModel(proxy_model)
                index_list.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
                layout.addWidget(index_list)
                
                # 按钮
                button_layout = QHBoxLayout()
                ok_button = QPushButton("确定")
                cancel_button = QPushButton("取消")
                button_layout.addWidget(ok_button)
                button_layout.addWidget(cancel_button)
                layout.addLayout(button_layout)
                
                # 连接信号
                def on_search_changed(text):
                    proxy_model.setFilterRegularExpression(text)
                    proxy_model.setFilterKeyColumn(-1)  # 搜索所有列
                
                def on_ok_clicked():
                    indexes = index_list.selectedIndexes()
                    if indexes:
                        row = proxy_model.mapToSource(indexes[0]).row()
                        code = model.item(row, 0).text()
                        self.stock_code_edit.setText(code)
                    dialog.accept()
                
                def on_cancel_clicked():
                    dialog.reject()
                
                def on_double_clicked(index):
                    row = proxy_model.mapToSource(index).row()
                    code = model.item(row, 0).text()
                    self.stock_code_edit.setText(code)
                    dialog.accept()
                
                search_edit.textChanged.connect(on_search_changed)
                ok_button.clicked.connect(on_ok_clicked)
                cancel_button.clicked.connect(on_cancel_clicked)
                index_list.doubleClicked.connect(on_double_clicked)
                
                # 显示对话框
                dialog.exec()
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"获取指数列表失败: {str(e)}")
        
        elif data_type == "板块数据":
            # 板块选择器
            try:
                # 根据当前选择的板块类别获取数据
                category = self.data_category_combo.currentText()
                table_name = ""
                
                if category == "行业板块":
                    table_name = "行业板块"
                elif category == "概念板块":
                    table_name = "概念板块"
                elif category == "地区板块":
                    table_name = "地区板块"
                else:
                    table_name = "行业板块"
                
                sql = f"""SELECT "板块名称" FROM \"{table_name}\" ORDER BY "板块名称"""
                df = self.pg_manager.query_df(sql)
                
                if df.empty:
                    QMessageBox.warning(self, "数据缺失", f"{category}数据不存在，请先刷新{category}数据")
                    return
                
                # 创建选择对话框
                dialog = QDialog(self)
                dialog.setWindowTitle("选择板块")
                dialog.setMinimumSize(400, 500)
                
                layout = QVBoxLayout(dialog)
                
                # 搜索框
                search_layout = QHBoxLayout()
                search_edit = QLineEdit()
                search_edit.setPlaceholderText("输入板块名称搜索")
                search_layout.addWidget(search_edit)
                layout.addLayout(search_layout)
                
                # 板块列表
                sector_list = QTableView()
                sector_list.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
                sector_list.setSelectionMode(QTableView.SelectionMode.SingleSelection)
                sector_list.setAlternatingRowColors(True)
                
                # 创建模型
                model = QStandardItemModel()
                model.setHorizontalHeaderLabels(["板块名称"])
                
                # 添加数据
                for i in range(len(df)):
                    name = QStandardItem(df.iloc[i]["板块名称"])
                    model.appendRow([name])
                
                # 创建过滤代理模型
                proxy_model = QSortFilterProxyModel()
                proxy_model.setSourceModel(model)
                proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
                
                # 设置模型
                sector_list.setModel(proxy_model)
                sector_list.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
                layout.addWidget(sector_list)
                
                # 按钮
                button_layout = QHBoxLayout()
                ok_button = QPushButton("确定")
                cancel_button = QPushButton("取消")
                button_layout.addWidget(ok_button)
                button_layout.addWidget(cancel_button)
                layout.addLayout(button_layout)
                
                # 连接信号
                def on_search_changed(text):
                    proxy_model.setFilterRegularExpression(text)
                    proxy_model.setFilterKeyColumn(-1)  # 搜索所有列
                
                def on_ok_clicked():
                    indexes = sector_list.selectedIndexes()
                    if indexes:
                        row = proxy_model.mapToSource(indexes[0]).row()
                        name = model.item(row, 0).text()
                        self.stock_code_edit.setText(name)
                    dialog.accept()
                
                def on_cancel_clicked():
                    dialog.reject()
                
                def on_double_clicked(index):
                    row = proxy_model.mapToSource(index).row()
                    name = model.item(row, 0).text()
                    self.stock_code_edit.setText(name)
                    dialog.accept()
                
                search_edit.textChanged.connect(on_search_changed)
                ok_button.clicked.connect(on_ok_clicked)
                cancel_button.clicked.connect(on_cancel_clicked)
                sector_list.doubleClicked.connect(on_double_clicked)
                
                # 显示对话框
                dialog.exec()
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"获取板块列表失败: {str(e)}")
    
    def show_table_context_menu(self, pos):
        """显示表格右键菜单"""
        # 获取当前选中的行
        indexes = self.table_view.selectedIndexes()
        if not indexes:
            return
        
        # 创建右键菜单
        menu = QMenu(self)
        
        # 添加菜单项
        copy_action = QAction("复制选中单元格", self)
        copy_row_action = QAction("复制整行", self)
        export_action = QAction("导出数据", self)
        
        menu.addAction(copy_action)
        menu.addAction(copy_row_action)
        menu.addSeparator()
        menu.addAction(export_action)
        
        # 连接信号
        def copy_cell():
            index = self.table_view.currentIndex()
            if index.isValid():
                cell_text = self.proxy_model.data(index)
                QApplication.clipboard().setText(str(cell_text))
        
        def copy_row():
            row_texts = []
            model = self.proxy_model
            row = self.table_view.currentIndex().row()
            
            for col in range(model.columnCount()):
                cell_text = model.data(model.index(row, col))
                row_texts.append(str(cell_text))
            
            QApplication.clipboard().setText("\t".join(row_texts))
        
        # 连接信号
        copy_action.triggered.connect(copy_cell)
        copy_row_action.triggered.connect(copy_row)
        export_action.triggered.connect(self.export_data)
        
        # 显示菜单
        menu.exec(self.table_view.viewport().mapToGlobal(pos))


if __name__ == "__main__":
    # 测试代码
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = DataView()
    window.show()
    sys.exit(app.exec())