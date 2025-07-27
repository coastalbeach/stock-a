#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
UI辅助函数
提供常用的UI组件创建和样式设置功能
"""

from PyQt6.QtWidgets import (
    QFrame, QPushButton, QLabel, QHBoxLayout, QVBoxLayout,
    QWidget, QMessageBox, QApplication
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor
from typing import Optional, Union


def create_separator(orientation='horizontal', color='#333333', thickness=1):
    """
    创建分隔线
    
    Args:
        orientation: 方向 ('horizontal' 或 'vertical')
        color: 颜色
        thickness: 厚度
    
    Returns:
        QFrame: 分隔线控件
    """
    separator = QFrame()
    
    if orientation == 'horizontal':
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFixedHeight(thickness)
    else:
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFixedWidth(thickness)
    
    separator.setFrameShadow(QFrame.Shadow.Sunken)
    separator.setStyleSheet(f"QFrame {{ background-color: {color}; }}")
    
    return separator


def create_icon_button(icon_path=None, text='', size=(32, 32), tooltip=''):
    """
    创建图标按钮
    
    Args:
        icon_path: 图标路径
        text: 按钮文本
        size: 按钮大小 (width, height)
        tooltip: 工具提示
    
    Returns:
        QPushButton: 图标按钮
    """
    button = QPushButton(text)
    
    if icon_path:
        if isinstance(icon_path, str):
            icon = QIcon(icon_path)
        else:
            # 如果传入的是颜色，创建纯色图标
            icon = create_color_icon(icon_path, size)
        button.setIcon(icon)
    
    button.setIconSize(QSize(*size))
    
    if tooltip:
        button.setToolTip(tooltip)
    
    # 设置按钮样式
    button.setStyleSheet("""
        QPushButton {
            border: 1px solid #555;
            border-radius: 4px;
            padding: 4px;
            background-color: #2b2b2b;
            color: white;
        }
        QPushButton:hover {
            background-color: #3c3c3c;
            border-color: #777;
        }
        QPushButton:pressed {
            background-color: #1e1e1e;
        }
    """)
    
    return button


def create_color_icon(color, size=(16, 16)):
    """
    创建纯色图标
    
    Args:
        color: 颜色 (QColor 或颜色字符串)
        size: 图标大小
    
    Returns:
        QIcon: 纯色图标
    """
    pixmap = QPixmap(*size)
    pixmap.fill(QColor(color) if isinstance(color, str) else color)
    return QIcon(pixmap)


def create_labeled_widget(label_text, widget, layout_type='horizontal'):
    """
    创建带标签的控件组合
    
    Args:
        label_text: 标签文本
        widget: 控件
        layout_type: 布局类型 ('horizontal' 或 'vertical')
    
    Returns:
        QWidget: 包含标签和控件的组合控件
    """
    container = QWidget()
    
    label = QLabel(label_text)
    label.setStyleSheet("QLabel { color: #cccccc; }")
    
    if layout_type == 'horizontal':
        layout = QHBoxLayout(container)
        layout.addWidget(label)
        layout.addWidget(widget)
        layout.setContentsMargins(0, 0, 0, 0)
    else:
        layout = QVBoxLayout(container)
        layout.addWidget(label)
        layout.addWidget(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
    
    return container


def set_widget_style(widget, style_dict):
    """
    设置控件样式
    
    Args:
        widget: 要设置样式的控件
        style_dict: 样式字典
    """
    style_parts = []
    
    for property_name, value in style_dict.items():
        # 将Python样式的属性名转换为CSS样式
        css_property = property_name.replace('_', '-')
        style_parts.append(f"{css_property}: {value};")
    
    style_string = " ".join(style_parts)
    widget.setStyleSheet(f"{widget.__class__.__name__} {{ {style_string} }}")


def show_message(parent, title, message, icon=QMessageBox.Icon.Information):
    """
    显示消息对话框
    
    Args:
        parent: 父控件
        title: 标题
        message: 消息内容
        icon: 图标类型
    
    Returns:
        int: 用户选择的按钮
    """
    msg_box = QMessageBox(parent)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setIcon(icon)
    
    # 设置消息框样式
    msg_box.setStyleSheet("""
        QMessageBox {
            background-color: #2b2b2b;
            color: white;
        }
        QMessageBox QPushButton {
            background-color: #3c3c3c;
            border: 1px solid #555;
            border-radius: 4px;
            padding: 6px 12px;
            color: white;
            min-width: 60px;
        }
        QMessageBox QPushButton:hover {
            background-color: #4a4a4a;
        }
        QMessageBox QPushButton:pressed {
            background-color: #1e1e1e;
        }
    """)
    
    return msg_box.exec()


def show_question(parent, title, message):
    """
    显示询问对话框
    
    Args:
        parent: 父控件
        title: 标题
        message: 消息内容
    
    Returns:
        bool: True表示用户点击了Yes，False表示点击了No
    """
    reply = QMessageBox.question(
        parent, title, message,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No
    )
    return reply == QMessageBox.StandardButton.Yes


def show_error(parent, title, message):
    """
    显示错误对话框
    
    Args:
        parent: 父控件
        title: 标题
        message: 错误消息
    """
    return show_message(parent, title, message, QMessageBox.Icon.Critical)


def show_warning(parent, title, message):
    """
    显示警告对话框
    
    Args:
        parent: 父控件
        title: 标题
        message: 警告消息
    """
    return show_message(parent, title, message, QMessageBox.Icon.Warning)


def show_info(parent, title, message):
    """
    显示信息对话框
    
    Args:
        parent: 父控件
        title: 标题
        message: 信息内容
    """
    return show_message(parent, title, message, QMessageBox.Icon.Information)


def apply_dark_style(widget):
    """
    应用深色主题样式
    
    Args:
        widget: 要应用样式的控件
    """
    dark_style = """
        QWidget {
            background-color: #2b2b2b;
            color: #ffffff;
            font-family: "Microsoft YaHei", "SimHei", sans-serif;
        }
        
        QMainWindow {
            background-color: #1e1e1e;
        }
        
        QMenuBar {
            background-color: #2b2b2b;
            border-bottom: 1px solid #555;
        }
        
        QMenuBar::item {
            background-color: transparent;
            padding: 4px 8px;
        }
        
        QMenuBar::item:selected {
            background-color: #3c3c3c;
        }
        
        QMenu {
            background-color: #2b2b2b;
            border: 1px solid #555;
        }
        
        QMenu::item {
            padding: 4px 20px;
        }
        
        QMenu::item:selected {
            background-color: #3c3c3c;
        }
        
        QToolBar {
            background-color: #2b2b2b;
            border: none;
            spacing: 2px;
        }
        
        QStatusBar {
            background-color: #2b2b2b;
            border-top: 1px solid #555;
        }
        
        QPushButton {
            background-color: #3c3c3c;
            border: 1px solid #555;
            border-radius: 4px;
            padding: 6px 12px;
            color: white;
        }
        
        QPushButton:hover {
            background-color: #4a4a4a;
        }
        
        QPushButton:pressed {
            background-color: #1e1e1e;
        }
        
        QLineEdit, QTextEdit, QPlainTextEdit {
            background-color: #1e1e1e;
            border: 1px solid #555;
            border-radius: 4px;
            padding: 4px;
            color: white;
        }
        
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
            border-color: #2196F3;
        }
        
        QComboBox {
            background-color: #3c3c3c;
            border: 1px solid #555;
            border-radius: 4px;
            padding: 4px;
            color: white;
        }
        
        QComboBox:hover {
            border-color: #777;
        }
        
        QComboBox::drop-down {
            border: none;
        }
        
        QComboBox::down-arrow {
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 4px solid #cccccc;
        }
        
        QTableWidget, QTreeWidget {
            background-color: #1e1e1e;
            alternate-background-color: #2a2a2a;
            border: 1px solid #555;
            gridline-color: #555;
            color: white;
        }
        
        QTableWidget::item, QTreeWidget::item {
            padding: 4px;
        }
        
        QTableWidget::item:selected, QTreeWidget::item:selected {
            background-color: #2196F3;
        }
        
        QHeaderView::section {
            background-color: #3c3c3c;
            border: 1px solid #555;
            padding: 4px;
            color: white;
        }
        
        QScrollBar:vertical {
            background-color: #2b2b2b;
            width: 12px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:vertical {
            background-color: #555;
            border-radius: 6px;
            min-height: 20px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #777;
        }
        
        QScrollBar:horizontal {
            background-color: #2b2b2b;
            height: 12px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:horizontal {
            background-color: #555;
            border-radius: 6px;
            min-width: 20px;
        }
        
        QScrollBar::handle:horizontal:hover {
            background-color: #777;
        }
        
        QTabWidget::pane {
            border: 1px solid #555;
            background-color: #2b2b2b;
        }
        
        QTabBar::tab {
            background-color: #3c3c3c;
            border: 1px solid #555;
            padding: 6px 12px;
            color: white;
        }
        
        QTabBar::tab:selected {
            background-color: #2196F3;
        }
        
        QTabBar::tab:hover {
            background-color: #4a4a4a;
        }
    """
    
    widget.setStyleSheet(dark_style)


def center_window(window, parent=None):
    """
    将窗口居中显示
    
    Args:
        window: 要居中的窗口
        parent: 父窗口，如果为None则相对于屏幕居中
    """
    if parent:
        # 相对于父窗口居中
        parent_geometry = parent.geometry()
        x = parent_geometry.x() + (parent_geometry.width() - window.width()) // 2
        y = parent_geometry.y() + (parent_geometry.height() - window.height()) // 2
        window.move(x, y)
    else:
        # 相对于屏幕居中
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - window.width()) // 2
        y = (screen.height() - window.height()) // 2
        window.move(x, y)


def get_stock_color(change_value):
    """
    根据涨跌值获取对应的颜色
    
    Args:
        change_value: 涨跌值
    
    Returns:
        str: 颜色字符串
    """
    if change_value > 0:
        return "#F44336"  # 红色（上涨）
    elif change_value < 0:
        return "#4CAF50"  # 绿色（下跌）
    else:
        return "#FFFFFF"  # 白色（平盘）


def format_stock_change(value, show_sign=True):
    """
    格式化股票涨跌值显示
    
    Args:
        value: 涨跌值
        show_sign: 是否显示正负号
    
    Returns:
        str: 格式化后的字符串
    """
    if value == 0:
        return "0.00"
    
    formatted = f"{abs(value):.2f}"
    
    if show_sign:
        if value > 0:
            return f"+{formatted}"
        else:
            return f"-{formatted}"
    
    return formatted