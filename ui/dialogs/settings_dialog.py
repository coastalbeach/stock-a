#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
设置对话框
用于配置应用程序的各种参数和选项
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QWidget, QLabel, QLineEdit, QPushButton, QComboBox,
    QSpinBox, QCheckBox, QGroupBox, QFormLayout,
    QFileDialog, QColorDialog, QFontDialog, QSlider,
    QTextEdit, QDialogButtonBox, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor
import json
import os


class SettingsDialog(QDialog):
    """
    设置对话框
    提供应用程序配置选项
    """
    
    # 信号定义
    settings_changed = pyqtSignal(dict)  # 设置变更信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = {}
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("设置")
        self.setModal(True)
        self.resize(600, 500)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        
        # 通用设置
        self.setup_general_tab()
        
        # 数据设置
        self.setup_data_tab()
        
        # 图表设置
        self.setup_chart_tab()
        
        # 交易设置
        self.setup_trading_tab()
        
        # 外观设置
        self.setup_appearance_tab()
        
        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.Apply
        )
        button_box.accepted.connect(self.accept_settings)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.apply_settings)
        
        # 主布局
        layout = QVBoxLayout(self)
        layout.addWidget(self.tab_widget)
        layout.addWidget(button_box)
        
    def setup_general_tab(self):
        """设置通用选项标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 启动设置
        startup_group = QGroupBox("启动设置")
        startup_layout = QFormLayout(startup_group)
        
        self.auto_start_check = QCheckBox("开机自动启动")
        startup_layout.addRow(self.auto_start_check)
        
        self.restore_workspace_check = QCheckBox("启动时恢复工作区")
        startup_layout.addRow(self.restore_workspace_check)
        
        self.auto_login_check = QCheckBox("自动登录")
        startup_layout.addRow(self.auto_login_check)
        
        layout.addWidget(startup_group)
        
        # 更新设置
        update_group = QGroupBox("更新设置")
        update_layout = QFormLayout(update_group)
        
        self.auto_update_check = QCheckBox("自动检查更新")
        update_layout.addRow(self.auto_update_check)
        
        self.update_frequency_combo = QComboBox()
        self.update_frequency_combo.addItems(["每天", "每周", "每月", "手动"])
        update_layout.addRow("检查频率:", self.update_frequency_combo)
        
        layout.addWidget(update_group)
        
        # 日志设置
        log_group = QGroupBox("日志设置")
        log_layout = QFormLayout(log_group)
        
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        log_layout.addRow("日志级别:", self.log_level_combo)
        
        self.log_file_edit = QLineEdit()
        log_file_layout = QHBoxLayout()
        log_file_layout.addWidget(self.log_file_edit)
        
        browse_log_btn = QPushButton("浏览")
        browse_log_btn.clicked.connect(self.browse_log_file)
        log_file_layout.addWidget(browse_log_btn)
        
        log_layout.addRow("日志文件:", log_file_layout)
        
        self.max_log_size_spin = QSpinBox()
        self.max_log_size_spin.setRange(1, 1000)
        self.max_log_size_spin.setSuffix(" MB")
        log_layout.addRow("最大日志大小:", self.max_log_size_spin)
        
        layout.addWidget(log_group)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "通用")
        
    def setup_data_tab(self):
        """设置数据选项标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 数据源设置
        datasource_group = QGroupBox("数据源设置")
        datasource_layout = QFormLayout(datasource_group)
        
        self.data_provider_combo = QComboBox()
        self.data_provider_combo.addItems(["AKShare", "Tushare", "Wind", "自定义"])
        datasource_layout.addRow("数据提供商:", self.data_provider_combo)
        
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        datasource_layout.addRow("API密钥:", self.api_key_edit)
        
        self.api_url_edit = QLineEdit()
        datasource_layout.addRow("API地址:", self.api_url_edit)
        
        layout.addWidget(datasource_group)
        
        # 数据更新设置
        update_group = QGroupBox("数据更新设置")
        update_layout = QFormLayout(update_group)
        
        self.auto_update_data_check = QCheckBox("自动更新数据")
        update_layout.addRow(self.auto_update_data_check)
        
        self.update_interval_spin = QSpinBox()
        self.update_interval_spin.setRange(1, 3600)
        self.update_interval_spin.setSuffix(" 秒")
        update_layout.addRow("更新间隔:", self.update_interval_spin)
        
        self.market_hours_check = QCheckBox("仅在交易时间更新")
        update_layout.addRow(self.market_hours_check)
        
        layout.addWidget(update_group)
        
        # 数据存储设置
        storage_group = QGroupBox("数据存储设置")
        storage_layout = QFormLayout(storage_group)
        
        self.db_type_combo = QComboBox()
        self.db_type_combo.addItems(["SQLite", "PostgreSQL", "MySQL", "Redis"])
        storage_layout.addRow("数据库类型:", self.db_type_combo)
        
        self.db_host_edit = QLineEdit()
        storage_layout.addRow("数据库主机:", self.db_host_edit)
        
        self.db_port_spin = QSpinBox()
        self.db_port_spin.setRange(1, 65535)
        storage_layout.addRow("端口:", self.db_port_spin)
        
        self.db_name_edit = QLineEdit()
        storage_layout.addRow("数据库名:", self.db_name_edit)
        
        self.db_user_edit = QLineEdit()
        storage_layout.addRow("用户名:", self.db_user_edit)
        
        self.db_password_edit = QLineEdit()
        self.db_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        storage_layout.addRow("密码:", self.db_password_edit)
        
        # 测试连接按钮
        test_conn_btn = QPushButton("测试连接")
        test_conn_btn.clicked.connect(self.test_database_connection)
        storage_layout.addRow(test_conn_btn)
        
        layout.addWidget(storage_group)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "数据")
        
    def setup_chart_tab(self):
        """设置图表选项标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 图表外观设置
        appearance_group = QGroupBox("图表外观")
        appearance_layout = QFormLayout(appearance_group)
        
        self.chart_theme_combo = QComboBox()
        self.chart_theme_combo.addItems(["深色", "浅色", "自定义"])
        appearance_layout.addRow("图表主题:", self.chart_theme_combo)
        
        # 背景颜色
        self.bg_color_btn = QPushButton("选择颜色")
        self.bg_color_btn.clicked.connect(lambda: self.choose_color('background'))
        appearance_layout.addRow("背景颜色:", self.bg_color_btn)
        
        # 网格设置
        self.show_grid_check = QCheckBox("显示网格")
        appearance_layout.addRow(self.show_grid_check)
        
        self.grid_color_btn = QPushButton("网格颜色")
        self.grid_color_btn.clicked.connect(lambda: self.choose_color('grid'))
        appearance_layout.addRow("网格颜色:", self.grid_color_btn)
        
        layout.addWidget(appearance_group)
        
        # K线设置
        kline_group = QGroupBox("K线设置")
        kline_layout = QFormLayout(kline_group)
        
        self.candle_width_spin = QSpinBox()
        self.candle_width_spin.setRange(1, 20)
        kline_layout.addRow("K线宽度:", self.candle_width_spin)
        
        self.up_color_btn = QPushButton("上涨颜色")
        self.up_color_btn.clicked.connect(lambda: self.choose_color('up'))
        kline_layout.addRow("上涨颜色:", self.up_color_btn)
        
        self.down_color_btn = QPushButton("下跌颜色")
        self.down_color_btn.clicked.connect(lambda: self.choose_color('down'))
        kline_layout.addRow("下跌颜色:", self.down_color_btn)
        
        layout.addWidget(kline_group)
        
        # 技术指标设置
        indicator_group = QGroupBox("技术指标")
        indicator_layout = QFormLayout(indicator_group)
        
        self.default_ma_edit = QLineEdit("5,10,20,30")
        indicator_layout.addRow("默认MA周期:", self.default_ma_edit)
        
        self.macd_params_edit = QLineEdit("12,26,9")
        indicator_layout.addRow("MACD参数:", self.macd_params_edit)
        
        self.rsi_period_spin = QSpinBox()
        self.rsi_period_spin.setRange(5, 50)
        indicator_layout.addRow("RSI周期:", self.rsi_period_spin)
        
        layout.addWidget(indicator_group)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "图表")
        
    def setup_trading_tab(self):
        """设置交易选项标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 交易账户设置
        account_group = QGroupBox("交易账户")
        account_layout = QFormLayout(account_group)
        
        self.broker_combo = QComboBox()
        self.broker_combo.addItems(["模拟交易", "华泰证券", "中信证券", "招商证券", "其他"])
        account_layout.addRow("券商:", self.broker_combo)
        
        self.account_id_edit = QLineEdit()
        account_layout.addRow("账户ID:", self.account_id_edit)
        
        self.trading_password_edit = QLineEdit()
        self.trading_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        account_layout.addRow("交易密码:", self.trading_password_edit)
        
        layout.addWidget(account_group)
        
        # 风险控制设置
        risk_group = QGroupBox("风险控制")
        risk_layout = QFormLayout(risk_group)
        
        self.max_position_spin = QSpinBox()
        self.max_position_spin.setRange(1, 100)
        self.max_position_spin.setSuffix("%")
        risk_layout.addRow("单股最大仓位:", self.max_position_spin)
        
        self.stop_loss_spin = QSpinBox()
        self.stop_loss_spin.setRange(1, 50)
        self.stop_loss_spin.setSuffix("%")
        risk_layout.addRow("止损比例:", self.stop_loss_spin)
        
        self.take_profit_spin = QSpinBox()
        self.take_profit_spin.setRange(1, 100)
        self.take_profit_spin.setSuffix("%")
        risk_layout.addRow("止盈比例:", self.take_profit_spin)
        
        self.max_drawdown_spin = QSpinBox()
        self.max_drawdown_spin.setRange(1, 50)
        self.max_drawdown_spin.setSuffix("%")
        risk_layout.addRow("最大回撤:", self.max_drawdown_spin)
        
        layout.addWidget(risk_group)
        
        # 交易提醒设置
        alert_group = QGroupBox("交易提醒")
        alert_layout = QFormLayout(alert_group)
        
        self.price_alert_check = QCheckBox("价格提醒")
        alert_layout.addRow(self.price_alert_check)
        
        self.volume_alert_check = QCheckBox("成交量异常提醒")
        alert_layout.addRow(self.volume_alert_check)
        
        self.signal_alert_check = QCheckBox("交易信号提醒")
        alert_layout.addRow(self.signal_alert_check)
        
        self.email_alert_check = QCheckBox("邮件提醒")
        alert_layout.addRow(self.email_alert_check)
        
        self.email_edit = QLineEdit()
        alert_layout.addRow("邮箱地址:", self.email_edit)
        
        layout.addWidget(alert_group)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "交易")
        
    def setup_appearance_tab(self):
        """设置外观选项标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 主题设置
        theme_group = QGroupBox("主题设置")
        theme_layout = QFormLayout(theme_group)
        
        self.ui_theme_combo = QComboBox()
        self.ui_theme_combo.addItems(["深色", "浅色", "跟随系统"])
        theme_layout.addRow("界面主题:", self.ui_theme_combo)
        
        self.accent_color_btn = QPushButton("强调色")
        self.accent_color_btn.clicked.connect(lambda: self.choose_color('accent'))
        theme_layout.addRow("强调色:", self.accent_color_btn)
        
        layout.addWidget(theme_group)
        
        # 字体设置
        font_group = QGroupBox("字体设置")
        font_layout = QFormLayout(font_group)
        
        self.ui_font_btn = QPushButton("选择字体")
        self.ui_font_btn.clicked.connect(self.choose_ui_font)
        font_layout.addRow("界面字体:", self.ui_font_btn)
        
        self.chart_font_btn = QPushButton("选择字体")
        self.chart_font_btn.clicked.connect(self.choose_chart_font)
        font_layout.addRow("图表字体:", self.chart_font_btn)
        
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 24)
        font_layout.addRow("字体大小:", self.font_size_spin)
        
        layout.addWidget(font_group)
        
        # 界面设置
        ui_group = QGroupBox("界面设置")
        ui_layout = QFormLayout(ui_group)
        
        self.show_toolbar_check = QCheckBox("显示工具栏")
        ui_layout.addRow(self.show_toolbar_check)
        
        self.show_statusbar_check = QCheckBox("显示状态栏")
        ui_layout.addRow(self.show_statusbar_check)
        
        self.animation_check = QCheckBox("启用动画效果")
        ui_layout.addRow(self.animation_check)
        
        self.transparency_slider = QSlider(Qt.Orientation.Horizontal)
        self.transparency_slider.setRange(50, 100)
        ui_layout.addRow("窗口透明度:", self.transparency_slider)
        
        layout.addWidget(ui_group)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "外观")
        
    def browse_log_file(self):
        """浏览日志文件"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "选择日志文件", "", "日志文件 (*.log);;所有文件 (*)"
        )
        if file_path:
            self.log_file_edit.setText(file_path)
            
    def choose_color(self, color_type):
        """选择颜色"""
        color = QColorDialog.getColor(QColor(255, 255, 255), self)
        if color.isValid():
            # 更新按钮颜色显示
            button = self.sender()
            button.setStyleSheet(f"background-color: {color.name()};")
            
            # 保存颜色设置
            if not hasattr(self, 'colors'):
                self.colors = {}
            self.colors[color_type] = color.name()
            
    def choose_ui_font(self):
        """选择界面字体"""
        font, ok = QFontDialog.getFont(QFont(), self)
        if ok:
            self.ui_font = font
            self.ui_font_btn.setText(f"{font.family()} {font.pointSize()}pt")
            
    def choose_chart_font(self):
        """选择图表字体"""
        font, ok = QFontDialog.getFont(QFont(), self)
        if ok:
            self.chart_font = font
            self.chart_font_btn.setText(f"{font.family()} {font.pointSize()}pt")
            
    def test_database_connection(self):
        """测试数据库连接"""
        # TODO: 实现数据库连接测试
        QMessageBox.information(self, "连接测试", "数据库连接测试功能待实现")
        
    def load_settings(self):
        """加载设置"""
        settings_file = "config/ui_settings.json"
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    self.settings = json.load(f)
                self.apply_settings_to_ui()
            except Exception as e:
                print(f"加载设置失败: {e}")
        else:
            # 使用默认设置
            self.load_default_settings()
            
    def load_default_settings(self):
        """加载默认设置"""
        self.settings = {
            'general': {
                'auto_start': False,
                'restore_workspace': True,
                'auto_login': False,
                'auto_update': True,
                'update_frequency': '每周',
                'log_level': 'INFO',
                'log_file': 'logs/app.log',
                'max_log_size': 100
            },
            'data': {
                'provider': 'AKShare',
                'api_key': '',
                'api_url': '',
                'auto_update': True,
                'update_interval': 5,
                'market_hours_only': True,
                'db_type': 'SQLite',
                'db_host': 'localhost',
                'db_port': 5432,
                'db_name': 'stock_data',
                'db_user': '',
                'db_password': ''
            },
            'chart': {
                'theme': '深色',
                'show_grid': True,
                'candle_width': 5,
                'default_ma': '5,10,20,30',
                'macd_params': '12,26,9',
                'rsi_period': 14
            },
            'trading': {
                'broker': '模拟交易',
                'account_id': '',
                'max_position': 20,
                'stop_loss': 10,
                'take_profit': 20,
                'max_drawdown': 15,
                'price_alert': True,
                'volume_alert': True,
                'signal_alert': True,
                'email_alert': False,
                'email': ''
            },
            'appearance': {
                'ui_theme': '深色',
                'font_size': 12,
                'show_toolbar': True,
                'show_statusbar': True,
                'animation': True,
                'transparency': 100
            }
        }
        self.apply_settings_to_ui()
        
    def apply_settings_to_ui(self):
        """将设置应用到UI控件"""
        # 通用设置
        general = self.settings.get('general', {})
        self.auto_start_check.setChecked(general.get('auto_start', False))
        self.restore_workspace_check.setChecked(general.get('restore_workspace', True))
        self.auto_login_check.setChecked(general.get('auto_login', False))
        self.auto_update_check.setChecked(general.get('auto_update', True))
        self.update_frequency_combo.setCurrentText(general.get('update_frequency', '每周'))
        self.log_level_combo.setCurrentText(general.get('log_level', 'INFO'))
        self.log_file_edit.setText(general.get('log_file', 'logs/app.log'))
        self.max_log_size_spin.setValue(general.get('max_log_size', 100))
        
        # 数据设置
        data = self.settings.get('data', {})
        self.data_provider_combo.setCurrentText(data.get('provider', 'AKShare'))
        self.api_key_edit.setText(data.get('api_key', ''))
        self.api_url_edit.setText(data.get('api_url', ''))
        self.auto_update_data_check.setChecked(data.get('auto_update', True))
        self.update_interval_spin.setValue(data.get('update_interval', 5))
        self.market_hours_check.setChecked(data.get('market_hours_only', True))
        self.db_type_combo.setCurrentText(data.get('db_type', 'SQLite'))
        self.db_host_edit.setText(data.get('db_host', 'localhost'))
        self.db_port_spin.setValue(data.get('db_port', 5432))
        self.db_name_edit.setText(data.get('db_name', 'stock_data'))
        self.db_user_edit.setText(data.get('db_user', ''))
        self.db_password_edit.setText(data.get('db_password', ''))
        
        # 图表设置
        chart = self.settings.get('chart', {})
        self.chart_theme_combo.setCurrentText(chart.get('theme', '深色'))
        self.show_grid_check.setChecked(chart.get('show_grid', True))
        self.candle_width_spin.setValue(chart.get('candle_width', 5))
        self.default_ma_edit.setText(chart.get('default_ma', '5,10,20,30'))
        self.macd_params_edit.setText(chart.get('macd_params', '12,26,9'))
        self.rsi_period_spin.setValue(chart.get('rsi_period', 14))
        
        # 交易设置
        trading = self.settings.get('trading', {})
        self.broker_combo.setCurrentText(trading.get('broker', '模拟交易'))
        self.account_id_edit.setText(trading.get('account_id', ''))
        self.max_position_spin.setValue(trading.get('max_position', 20))
        self.stop_loss_spin.setValue(trading.get('stop_loss', 10))
        self.take_profit_spin.setValue(trading.get('take_profit', 20))
        self.max_drawdown_spin.setValue(trading.get('max_drawdown', 15))
        self.price_alert_check.setChecked(trading.get('price_alert', True))
        self.volume_alert_check.setChecked(trading.get('volume_alert', True))
        self.signal_alert_check.setChecked(trading.get('signal_alert', True))
        self.email_alert_check.setChecked(trading.get('email_alert', False))
        self.email_edit.setText(trading.get('email', ''))
        
        # 外观设置
        appearance = self.settings.get('appearance', {})
        self.ui_theme_combo.setCurrentText(appearance.get('ui_theme', '深色'))
        self.font_size_spin.setValue(appearance.get('font_size', 12))
        self.show_toolbar_check.setChecked(appearance.get('show_toolbar', True))
        self.show_statusbar_check.setChecked(appearance.get('show_statusbar', True))
        self.animation_check.setChecked(appearance.get('animation', True))
        self.transparency_slider.setValue(appearance.get('transparency', 100))
        
    def collect_settings_from_ui(self):
        """从UI控件收集设置"""
        self.settings = {
            'general': {
                'auto_start': self.auto_start_check.isChecked(),
                'restore_workspace': self.restore_workspace_check.isChecked(),
                'auto_login': self.auto_login_check.isChecked(),
                'auto_update': self.auto_update_check.isChecked(),
                'update_frequency': self.update_frequency_combo.currentText(),
                'log_level': self.log_level_combo.currentText(),
                'log_file': self.log_file_edit.text(),
                'max_log_size': self.max_log_size_spin.value()
            },
            'data': {
                'provider': self.data_provider_combo.currentText(),
                'api_key': self.api_key_edit.text(),
                'api_url': self.api_url_edit.text(),
                'auto_update': self.auto_update_data_check.isChecked(),
                'update_interval': self.update_interval_spin.value(),
                'market_hours_only': self.market_hours_check.isChecked(),
                'db_type': self.db_type_combo.currentText(),
                'db_host': self.db_host_edit.text(),
                'db_port': self.db_port_spin.value(),
                'db_name': self.db_name_edit.text(),
                'db_user': self.db_user_edit.text(),
                'db_password': self.db_password_edit.text()
            },
            'chart': {
                'theme': self.chart_theme_combo.currentText(),
                'show_grid': self.show_grid_check.isChecked(),
                'candle_width': self.candle_width_spin.value(),
                'default_ma': self.default_ma_edit.text(),
                'macd_params': self.macd_params_edit.text(),
                'rsi_period': self.rsi_period_spin.value()
            },
            'trading': {
                'broker': self.broker_combo.currentText(),
                'account_id': self.account_id_edit.text(),
                'max_position': self.max_position_spin.value(),
                'stop_loss': self.stop_loss_spin.value(),
                'take_profit': self.take_profit_spin.value(),
                'max_drawdown': self.max_drawdown_spin.value(),
                'price_alert': self.price_alert_check.isChecked(),
                'volume_alert': self.volume_alert_check.isChecked(),
                'signal_alert': self.signal_alert_check.isChecked(),
                'email_alert': self.email_alert_check.isChecked(),
                'email': self.email_edit.text()
            },
            'appearance': {
                'ui_theme': self.ui_theme_combo.currentText(),
                'font_size': self.font_size_spin.value(),
                'show_toolbar': self.show_toolbar_check.isChecked(),
                'show_statusbar': self.show_statusbar_check.isChecked(),
                'animation': self.animation_check.isChecked(),
                'transparency': self.transparency_slider.value()
            }
        }
        
        # 添加颜色和字体设置
        if hasattr(self, 'colors'):
            self.settings['colors'] = self.colors
        if hasattr(self, 'ui_font'):
            self.settings['ui_font'] = self.ui_font.toString()
        if hasattr(self, 'chart_font'):
            self.settings['chart_font'] = self.chart_font.toString()
            
    def save_settings(self):
        """保存设置到文件"""
        settings_file = "config/ui_settings.json"
        os.makedirs(os.path.dirname(settings_file), exist_ok=True)
        
        try:
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            QMessageBox.warning(self, "保存失败", f"保存设置失败: {e}")
            
    def apply_settings(self):
        """应用设置"""
        self.collect_settings_from_ui()
        self.save_settings()
        self.settings_changed.emit(self.settings)
        
    def accept_settings(self):
        """接受设置并关闭对话框"""
        self.apply_settings()
        self.accept()
        
    def get_settings(self):
        """获取当前设置"""
        return self.settings