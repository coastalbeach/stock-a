#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
关于对话框
显示应用程序信息、版本信息和开发者信息
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTextEdit, QTabWidget, QWidget,
    QFrame, QScrollArea
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QPixmap, QFont, QDesktopServices
import sys
import platform


class AboutDialog(QDialog):
    """
    关于对话框
    显示应用程序的详细信息
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("关于 Stock-A")
        self.setModal(True)
        self.setFixedSize(500, 400)
        
        # 创建标签页
        tab_widget = QTabWidget()
        
        # 关于标签页
        self.setup_about_tab(tab_widget)
        
        # 系统信息标签页
        self.setup_system_tab(tab_widget)
        
        # 许可证标签页
        self.setup_license_tab(tab_widget)
        
        # 致谢标签页
        self.setup_credits_tab(tab_widget)
        
        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        
        # 主布局
        layout = QVBoxLayout(self)
        layout.addWidget(tab_widget)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
    def setup_about_tab(self, tab_widget):
        """设置关于标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 应用程序图标和名称
        header_layout = QHBoxLayout()
        
        # 图标（如果有的话）
        icon_label = QLabel()
        # icon_label.setPixmap(QPixmap("resources/icons/app_icon.png").scaled(64, 64))
        icon_label.setFixedSize(64, 64)
        icon_label.setStyleSheet("background-color: #2196F3; border-radius: 8px;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setText("SA")
        icon_label.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        header_layout.addWidget(icon_label)
        
        # 应用信息
        info_layout = QVBoxLayout()
        
        app_name = QLabel("Stock-A 量化分析系统")
        app_name.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        info_layout.addWidget(app_name)
        
        version_label = QLabel("版本 1.0.0")
        version_label.setFont(QFont("Arial", 12))
        info_layout.addWidget(version_label)
        
        build_label = QLabel("构建日期: 2024-01-01")
        build_label.setFont(QFont("Arial", 10))
        build_label.setStyleSheet("color: #666;")
        info_layout.addWidget(build_label)
        
        header_layout.addLayout(info_layout)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)
        
        # 描述信息
        description = QLabel(
            "Stock-A 是一个专业的股票量化分析系统，基于 PyQt6 开发。\n\n"
            "主要功能包括：\n"
            "• 实时股票数据获取和显示\n"
            "• 专业的K线图表和技术指标分析\n"
            "• 量化策略回测和优化\n"
            "• 投资组合管理和风险控制\n"
            "• 自定义选股和预警系统\n\n"
            "本软件采用模块化设计，支持多种数据源和交易接口，\n"
            "为量化投资者提供完整的分析和交易解决方案。"
        )
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(description)
        
        # 开发者信息
        developer_layout = QVBoxLayout()
        
        developer_label = QLabel("开发者信息:")
        developer_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        developer_layout.addWidget(developer_label)
        
        developer_info = QLabel(
            "开发者: Stock-A Team\n"
            "邮箱: contact@stock-a.com\n"
            "网站: https://www.stock-a.com"
        )
        developer_layout.addWidget(developer_info)
        
        layout.addLayout(developer_layout)
        
        # 链接按钮
        link_layout = QHBoxLayout()
        
        website_btn = QPushButton("访问官网")
        website_btn.clicked.connect(lambda: self.open_url("https://www.stock-a.com"))
        link_layout.addWidget(website_btn)
        
        github_btn = QPushButton("GitHub")
        github_btn.clicked.connect(lambda: self.open_url("https://github.com/stock-a/stock-a"))
        link_layout.addWidget(github_btn)
        
        docs_btn = QPushButton("使用文档")
        docs_btn.clicked.connect(lambda: self.open_url("https://docs.stock-a.com"))
        link_layout.addWidget(docs_btn)
        
        link_layout.addStretch()
        layout.addLayout(link_layout)
        
        layout.addStretch()
        tab_widget.addTab(tab, "关于")
        
    def setup_system_tab(self, tab_widget):
        """设置系统信息标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 系统信息
        system_info = QTextEdit()
        system_info.setReadOnly(True)
        system_info.setFont(QFont("Consolas", 10))
        
        # 收集系统信息
        info_text = self.get_system_info()
        system_info.setPlainText(info_text)
        
        layout.addWidget(QLabel("系统信息:"))
        layout.addWidget(system_info)
        
        tab_widget.addTab(tab, "系统信息")
        
    def setup_license_tab(self, tab_widget):
        """设置许可证标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 许可证信息
        license_text = QTextEdit()
        license_text.setReadOnly(True)
        license_text.setFont(QFont("Consolas", 10))
        
        license_content = """
MIT License

Copyright (c) 2024 Stock-A Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
        
        license_text.setPlainText(license_content)
        
        layout.addWidget(QLabel("软件许可证:"))
        layout.addWidget(license_text)
        
        tab_widget.addTab(tab, "许可证")
        
    def setup_credits_tab(self, tab_widget):
        """设置致谢标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 滚动区域
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # 致谢内容
        credits_content = [
            ("开发框架", [
                "PyQt6 - 跨平台GUI框架",
                "Python 3.8+ - 编程语言",
                "NumPy - 数值计算库",
                "Pandas - 数据分析库",
                "Matplotlib - 图表绘制库",
                "PyQtGraph - 实时图表库"
            ]),
            ("数据源", [
                "AKShare - 开源金融数据接口",
                "Tushare - 金融数据平台",
                "Yahoo Finance - 国际金融数据",
                "新浪财经 - 实时行情数据"
            ]),
            ("技术指标", [
                "TA-Lib - 技术分析库",
                "Backtrader - 回测框架",
                "Zipline - 量化交易库",
                "PyAlgoTrade - 算法交易库"
            ]),
            ("UI设计参考", [
                "同花顺 iFinder - 专业金融终端",
                "Wind - 万得金融终端",
                "东方财富 - 金融数据平台",
                "通达信 - 证券分析软件"
            ]),
            ("开源项目", [
                "Material Design - 设计规范",
                "Font Awesome - 图标库",
                "Qt Company - Qt框架",
                "Python Software Foundation - Python语言"
            ])
        ]
        
        for category, items in credits_content:
            # 分类标题
            category_label = QLabel(category)
            category_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            category_label.setStyleSheet("color: #2196F3; margin-top: 10px;")
            scroll_layout.addWidget(category_label)
            
            # 项目列表
            for item in items:
                item_label = QLabel(f"• {item}")
                item_label.setStyleSheet("margin-left: 20px; margin-bottom: 2px;")
                scroll_layout.addWidget(item_label)
        
        # 特别感谢
        thanks_label = QLabel("特别感谢")
        thanks_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        thanks_label.setStyleSheet("color: #2196F3; margin-top: 20px;")
        scroll_layout.addWidget(thanks_label)
        
        thanks_text = QLabel(
            "感谢所有为开源社区贡献代码和文档的开发者们，\n"
            "感谢提供数据接口和技术支持的各个平台，\n"
            "感谢用户的反馈和建议，让我们不断改进和完善。"
        )
        thanks_text.setWordWrap(True)
        thanks_text.setStyleSheet("margin-left: 20px; margin-top: 10px;")
        scroll_layout.addWidget(thanks_text)
        
        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        
        layout.addWidget(scroll_area)
        
        tab_widget.addTab(tab, "致谢")
        
    def get_system_info(self):
        """获取系统信息"""
        info_lines = [
            "=== 应用程序信息 ===",
            f"应用名称: Stock-A 量化分析系统",
            f"版本: 1.0.0",
            f"构建日期: 2024-01-01",
            "",
            "=== Python 环境 ===",
            f"Python 版本: {sys.version}",
            f"Python 路径: {sys.executable}",
            "",
            "=== 系统信息 ===",
            f"操作系统: {platform.system()}",
            f"系统版本: {platform.release()}",
            f"系统架构: {platform.machine()}",
            f"处理器: {platform.processor()}",
            f"计算机名: {platform.node()}",
            "",
            "=== PyQt6 信息 ==="
        ]
        
        try:
            from PyQt6.QtCore import QT_VERSION_STR, PYQT_VERSION_STR
            info_lines.extend([
                f"Qt 版本: {QT_VERSION_STR}",
                f"PyQt6 版本: {PYQT_VERSION_STR}"
            ])
        except ImportError:
            info_lines.append("PyQt6 信息获取失败")
        
        info_lines.extend([
            "",
            "=== 已安装的包 ==="
        ])
        
        # 尝试获取关键包的版本信息
        packages = [
            'numpy', 'pandas', 'matplotlib', 'pyqtgraph',
            'akshare', 'tushare', 'requests', 'sqlalchemy'
        ]
        
        for package in packages:
            try:
                import importlib
                module = importlib.import_module(package)
                version = getattr(module, '__version__', '未知版本')
                info_lines.append(f"{package}: {version}")
            except ImportError:
                info_lines.append(f"{package}: 未安装")
        
        return "\n".join(info_lines)
        
    def open_url(self, url):
        """打开URL链接"""
        QDesktopServices.openUrl(QUrl(url))