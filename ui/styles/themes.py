#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
主题样式定义
包含深色主题和浅色主题的样式表
"""

class DarkTheme:
    """
    深色主题样式
    参考专业财经软件的深色配色方案
    """
    
    @staticmethod
    def get_stylesheet():
        """获取深色主题样式表"""
        return """
        /* 主窗口样式 */
        QMainWindow {
            background-color: #1e1e1e;
            color: #ffffff;
        }
        
        /* 菜单栏样式 */
        QMenuBar {
            background-color: #2d2d2d;
            color: #ffffff;
            border-bottom: 1px solid #404040;
            padding: 2px;
        }
        
        QMenuBar::item {
            background-color: transparent;
            padding: 4px 8px;
            margin: 1px;
        }
        
        QMenuBar::item:selected {
            background-color: #404040;
            border-radius: 3px;
        }
        
        QMenu {
            background-color: #2d2d2d;
            color: #ffffff;
            border: 1px solid #404040;
            padding: 2px;
        }
        
        QMenu::item {
            padding: 5px 20px;
            margin: 1px;
        }
        
        QMenu::item:selected {
            background-color: #404040;
            border-radius: 3px;
        }
        
        QMenu::separator {
            height: 1px;
            background-color: #404040;
            margin: 2px 5px;
        }
        
        /* 工具栏样式 */
        QToolBar {
            background-color: #2d2d2d;
            border: none;
            spacing: 2px;
            padding: 2px;
        }
        
        QToolButton {
            background-color: transparent;
            color: #ffffff;
            border: none;
            padding: 5px;
            margin: 1px;
            border-radius: 3px;
        }
        
        QToolButton:hover {
            background-color: #404040;
        }
        
        QToolButton:pressed {
            background-color: #505050;
        }
        
        /* 状态栏样式 */
        QStatusBar {
            background-color: #2d2d2d;
            color: #ffffff;
            border-top: 1px solid #404040;
        }
        
        /* 停靠窗口样式 */
        QDockWidget {
            background-color: #1e1e1e;
            color: #ffffff;
            titlebar-close-icon: none;
            titlebar-normal-icon: none;
        }
        
        QDockWidget::title {
            background-color: #2d2d2d;
            color: #ffffff;
            padding: 5px;
            border-bottom: 1px solid #404040;
        }
        
        /* 标签页样式 */
        QTabWidget::pane {
            border: 1px solid #404040;
            background-color: #1e1e1e;
        }
        
        QTabBar::tab {
            background-color: #2d2d2d;
            color: #ffffff;
            padding: 8px 16px;
            margin-right: 2px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        
        QTabBar::tab:selected {
            background-color: #1e1e1e;
            border-bottom: 2px solid #0078d4;
        }
        
        QTabBar::tab:hover {
            background-color: #404040;
        }
        
        /* 按钮样式 */
        QPushButton {
            background-color: #0078d4;
            color: #ffffff;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
            font-weight: bold;
        }
        
        QPushButton:hover {
            background-color: #106ebe;
        }
        
        QPushButton:pressed {
            background-color: #005a9e;
        }
        
        QPushButton:disabled {
            background-color: #404040;
            color: #808080;
        }
        
        /* 次要按钮样式 */
        QPushButton[class="secondary"] {
            background-color: #404040;
            color: #ffffff;
        }
        
        QPushButton[class="secondary"]:hover {
            background-color: #505050;
        }
        
        /* 表格样式 */
        QTableWidget, QTableView {
            background-color: #1e1e1e;
            color: #ffffff;
            gridline-color: #404040;
            selection-background-color: #0078d4;
            alternate-background-color: #252525;
        }
        
        QHeaderView::section {
            background-color: #2d2d2d;
            color: #ffffff;
            padding: 5px;
            border: 1px solid #404040;
            font-weight: bold;
        }
        
        QTableWidget::item, QTableView::item {
            padding: 5px;
            border-bottom: 1px solid #404040;
        }
        
        QTableWidget::item:selected, QTableView::item:selected {
            background-color: #0078d4;
        }
        
        /* 树形控件样式 */
        QTreeWidget, QTreeView {
            background-color: #1e1e1e;
            color: #ffffff;
            selection-background-color: #0078d4;
            alternate-background-color: #252525;
        }
        
        QTreeWidget::item, QTreeView::item {
            padding: 3px;
            border-bottom: 1px solid #404040;
        }
        
        QTreeWidget::item:selected, QTreeView::item:selected {
            background-color: #0078d4;
        }
        
        QTreeWidget::branch:has-children:!has-siblings:closed,
        QTreeWidget::branch:closed:has-children:has-siblings {
            border-image: none;
            image: url(:/icons/branch-closed.png);
        }
        
        QTreeWidget::branch:open:has-children:!has-siblings,
        QTreeWidget::branch:open:has-children:has-siblings {
            border-image: none;
            image: url(:/icons/branch-open.png);
        }
        
        /* 输入框样式 */
        QLineEdit, QTextEdit, QPlainTextEdit {
            background-color: #2d2d2d;
            color: #ffffff;
            border: 1px solid #404040;
            padding: 5px;
            border-radius: 3px;
        }
        
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
            border-color: #0078d4;
        }
        
        /* 组合框样式 */
        QComboBox {
            background-color: #2d2d2d;
            color: #ffffff;
            border: 1px solid #404040;
            padding: 5px;
            border-radius: 3px;
        }
        
        QComboBox:hover {
            border-color: #0078d4;
        }
        
        QComboBox::drop-down {
            border: none;
            width: 20px;
        }
        
        QComboBox::down-arrow {
            image: url(:/icons/down-arrow.png);
            width: 12px;
            height: 12px;
        }
        
        QComboBox QAbstractItemView {
            background-color: #2d2d2d;
            color: #ffffff;
            border: 1px solid #404040;
            selection-background-color: #0078d4;
        }
        
        /* 数值输入框样式 */
        QSpinBox, QDoubleSpinBox {
            background-color: #2d2d2d;
            color: #ffffff;
            border: 1px solid #404040;
            padding: 5px;
            border-radius: 3px;
        }
        
        QSpinBox:focus, QDoubleSpinBox:focus {
            border-color: #0078d4;
        }
        
        /* 日期选择器样式 */
        QDateEdit {
            background-color: #2d2d2d;
            color: #ffffff;
            border: 1px solid #404040;
            padding: 5px;
            border-radius: 3px;
        }
        
        QDateEdit:focus {
            border-color: #0078d4;
        }
        
        /* 进度条样式 */
        QProgressBar {
            background-color: #2d2d2d;
            border: 1px solid #404040;
            border-radius: 3px;
            text-align: center;
            color: #ffffff;
        }
        
        QProgressBar::chunk {
            background-color: #0078d4;
            border-radius: 2px;
        }
        
        /* 滚动条样式 */
        QScrollBar:vertical {
            background-color: #2d2d2d;
            width: 12px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:vertical {
            background-color: #505050;
            border-radius: 6px;
            min-height: 20px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #606060;
        }
        
        QScrollBar:horizontal {
            background-color: #2d2d2d;
            height: 12px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:horizontal {
            background-color: #505050;
            border-radius: 6px;
            min-width: 20px;
        }
        
        QScrollBar::handle:horizontal:hover {
            background-color: #606060;
        }
        
        QScrollBar::add-line, QScrollBar::sub-line {
            border: none;
            background: none;
        }
        
        /* 分组框样式 */
        QGroupBox {
            color: #ffffff;
            border: 1px solid #404040;
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 10px;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
            color: #ffffff;
            font-weight: bold;
        }
        
        /* 框架样式 */
        QFrame {
            background-color: #1e1e1e;
            border: 1px solid #404040;
        }
        
        /* 标签样式 */
        QLabel {
            color: #ffffff;
            background-color: transparent;
        }
        
        /* 股票价格颜色 */
        QLabel[class="price-up"] {
            color: #ff4444;
            font-weight: bold;
        }
        
        QLabel[class="price-down"] {
            color: #00aa00;
            font-weight: bold;
        }
        
        QLabel[class="price-flat"] {
            color: #ffffff;
            font-weight: bold;
        }
        
        /* 分割器样式 */
        QSplitter::handle {
            background-color: #404040;
        }
        
        QSplitter::handle:horizontal {
            width: 3px;
        }
        
        QSplitter::handle:vertical {
            height: 3px;
        }
        
        /* 复选框样式 */
        QCheckBox {
            color: #ffffff;
            spacing: 5px;
        }
        
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
        }
        
        QCheckBox::indicator:unchecked {
            background-color: #2d2d2d;
            border: 1px solid #404040;
            border-radius: 3px;
        }
        
        QCheckBox::indicator:checked {
            background-color: #0078d4;
            border: 1px solid #0078d4;
            border-radius: 3px;
            image: url(:/icons/check.png);
        }
        
        /* 单选按钮样式 */
        QRadioButton {
            color: #ffffff;
            spacing: 5px;
        }
        
        QRadioButton::indicator {
            width: 16px;
            height: 16px;
        }
        
        QRadioButton::indicator:unchecked {
            background-color: #2d2d2d;
            border: 1px solid #404040;
            border-radius: 8px;
        }
        
        QRadioButton::indicator:checked {
            background-color: #0078d4;
            border: 1px solid #0078d4;
            border-radius: 8px;
        }
        """


class LightTheme:
    """
    浅色主题样式
    传统的浅色配色方案
    """
    
    @staticmethod
    def get_stylesheet():
        """获取浅色主题样式表"""
        return """
        /* 主窗口样式 */
        QMainWindow {
            background-color: #ffffff;
            color: #000000;
        }
        
        /* 菜单栏样式 */
        QMenuBar {
            background-color: #f0f0f0;
            color: #000000;
            border-bottom: 1px solid #d0d0d0;
            padding: 2px;
        }
        
        QMenuBar::item {
            background-color: transparent;
            padding: 4px 8px;
            margin: 1px;
        }
        
        QMenuBar::item:selected {
            background-color: #e0e0e0;
            border-radius: 3px;
        }
        
        QMenu {
            background-color: #ffffff;
            color: #000000;
            border: 1px solid #d0d0d0;
            padding: 2px;
        }
        
        QMenu::item {
            padding: 5px 20px;
            margin: 1px;
        }
        
        QMenu::item:selected {
            background-color: #e0e0e0;
            border-radius: 3px;
        }
        
        QMenu::separator {
            height: 1px;
            background-color: #d0d0d0;
            margin: 2px 5px;
        }
        
        /* 工具栏样式 */
        QToolBar {
            background-color: #f0f0f0;
            border: none;
            spacing: 2px;
            padding: 2px;
        }
        
        QToolButton {
            background-color: transparent;
            color: #000000;
            border: none;
            padding: 5px;
            margin: 1px;
            border-radius: 3px;
        }
        
        QToolButton:hover {
            background-color: #e0e0e0;
        }
        
        QToolButton:pressed {
            background-color: #d0d0d0;
        }
        
        /* 状态栏样式 */
        QStatusBar {
            background-color: #f0f0f0;
            color: #000000;
            border-top: 1px solid #d0d0d0;
        }
        
        /* 停靠窗口样式 */
        QDockWidget {
            background-color: #ffffff;
            color: #000000;
        }
        
        QDockWidget::title {
            background-color: #f0f0f0;
            color: #000000;
            padding: 5px;
            border-bottom: 1px solid #d0d0d0;
        }
        
        /* 标签页样式 */
        QTabWidget::pane {
            border: 1px solid #d0d0d0;
            background-color: #ffffff;
        }
        
        QTabBar::tab {
            background-color: #f0f0f0;
            color: #000000;
            padding: 8px 16px;
            margin-right: 2px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        
        QTabBar::tab:selected {
            background-color: #ffffff;
            border-bottom: 2px solid #0078d4;
        }
        
        QTabBar::tab:hover {
            background-color: #e0e0e0;
        }
        
        /* 按钮样式 */
        QPushButton {
            background-color: #0078d4;
            color: #ffffff;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
            font-weight: bold;
        }
        
        QPushButton:hover {
            background-color: #106ebe;
        }
        
        QPushButton:pressed {
            background-color: #005a9e;
        }
        
        QPushButton:disabled {
            background-color: #d0d0d0;
            color: #808080;
        }
        
        /* 表格样式 */
        QTableWidget, QTableView {
            background-color: #ffffff;
            color: #000000;
            gridline-color: #d0d0d0;
            selection-background-color: #0078d4;
            alternate-background-color: #f8f8f8;
        }
        
        QHeaderView::section {
            background-color: #f0f0f0;
            color: #000000;
            padding: 5px;
            border: 1px solid #d0d0d0;
            font-weight: bold;
        }
        
        QTableWidget::item, QTableView::item {
            padding: 5px;
            border-bottom: 1px solid #e0e0e0;
        }
        
        QTableWidget::item:selected, QTableView::item:selected {
            background-color: #0078d4;
            color: #ffffff;
        }
        
        /* 树形控件样式 */
        QTreeWidget, QTreeView {
            background-color: #ffffff;
            color: #000000;
            selection-background-color: #0078d4;
            alternate-background-color: #f8f8f8;
        }
        
        QTreeWidget::item, QTreeView::item {
            padding: 3px;
            border-bottom: 1px solid #e0e0e0;
        }
        
        QTreeWidget::item:selected, QTreeView::item:selected {
            background-color: #0078d4;
            color: #ffffff;
        }
        
        /* 输入框样式 */
        QLineEdit, QTextEdit, QPlainTextEdit {
            background-color: #ffffff;
            color: #000000;
            border: 1px solid #d0d0d0;
            padding: 5px;
            border-radius: 3px;
        }
        
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
            border-color: #0078d4;
        }
        
        /* 组合框样式 */
        QComboBox {
            background-color: #ffffff;
            color: #000000;
            border: 1px solid #d0d0d0;
            padding: 5px;
            border-radius: 3px;
        }
        
        QComboBox:hover {
            border-color: #0078d4;
        }
        
        QComboBox QAbstractItemView {
            background-color: #ffffff;
            color: #000000;
            border: 1px solid #d0d0d0;
            selection-background-color: #0078d4;
        }
        
        /* 股票价格颜色 */
        QLabel[class="price-up"] {
            color: #ff0000;
            font-weight: bold;
        }
        
        QLabel[class="price-down"] {
            color: #008000;
            font-weight: bold;
        }
        
        QLabel[class="price-flat"] {
            color: #000000;
            font-weight: bold;
        }
        """