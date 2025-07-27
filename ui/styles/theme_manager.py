#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
主题管理器
负责应用程序主题的切换和管理
"""

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal
from .themes import DarkTheme, LightTheme


class ThemeManager(QObject):
    """
    主题管理器
    负责管理和切换应用程序主题
    """
    
    # 主题变更信号
    theme_changed = pyqtSignal(str)  # 主题名称
    
    def __init__(self):
        super().__init__()
        self._current_theme = "dark"
        self._themes = {
            "dark": DarkTheme,
            "light": LightTheme
        }
    
    def get_current_theme(self):
        """
        获取当前主题名称
        
        Returns:
            str: 当前主题名称
        """
        return self._current_theme
    
    def get_available_themes(self):
        """
        获取可用主题列表
        
        Returns:
            list: 可用主题名称列表
        """
        return list(self._themes.keys())
    
    def set_theme(self, theme_name):
        """
        设置主题
        
        Args:
            theme_name (str): 主题名称
        """
        if theme_name not in self._themes:
            print(f"警告: 未知主题 '{theme_name}'，使用默认主题")
            theme_name = "dark"
        
        if theme_name != self._current_theme:
            self._current_theme = theme_name
            self._apply_theme()
            self.theme_changed.emit(theme_name)
    
    def toggle_theme(self):
        """
        切换主题（在深色和浅色之间切换）
        """
        if self._current_theme == "dark":
            self.set_theme("light")
        else:
            self.set_theme("dark")
    
    def _apply_theme(self):
        """
        应用当前主题到应用程序
        """
        app = QApplication.instance()
        if app:
            theme_class = self._themes[self._current_theme]
            stylesheet = theme_class.get_stylesheet()
            app.setStyleSheet(stylesheet)
    
    def get_current_stylesheet(self):
        """
        获取当前主题的样式表
        
        Returns:
            str: 当前主题的CSS样式表
        """
        theme_class = self._themes[self._current_theme]
        return theme_class.get_stylesheet()
    
    def get_theme_colors(self):
        """
        获取当前主题的颜色配置
        
        Returns:
            dict: 主题颜色配置
        """
        theme_class = self._themes[self._current_theme]
        if hasattr(theme_class, 'get_colors'):
            return theme_class.get_colors()
        return {}
    
    def register_theme(self, name, theme_class):
        """
        注册新主题
        
        Args:
            name (str): 主题名称
            theme_class: 主题类
        """
        self._themes[name] = theme_class
    
    def apply_to_widget(self, widget, custom_style=None):
        """
        将主题应用到特定组件
        
        Args:
            widget: 要应用主题的组件
            custom_style (str, optional): 自定义样式
        """
        if custom_style:
            widget.setStyleSheet(custom_style)
        else:
            # 应用当前主题的样式
            theme_class = self._themes[self._current_theme]
            if hasattr(theme_class, 'get_widget_style'):
                style = theme_class.get_widget_style(widget.__class__.__name__)
                if style:
                    widget.setStyleSheet(style)


# 全局主题管理器实例
theme_manager = ThemeManager()