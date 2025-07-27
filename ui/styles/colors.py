#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
颜色定义
统一管理UI中使用的颜色常量
"""

from PyQt6.QtGui import QColor


class StockColors:
    """
    股票相关颜色定义
    遵循中国股市的颜色习惯：红涨绿跌
    """
    
    # 股票价格颜色
    PRICE_UP = QColor(255, 68, 68)      # 上涨红色
    PRICE_DOWN = QColor(0, 170, 0)      # 下跌绿色
    PRICE_FLAT = QColor(255, 255, 255)  # 平盘白色
    
    # 股票价格颜色（字符串格式）
    PRICE_UP_STR = "#ff4444"
    PRICE_DOWN_STR = "#00aa00"
    PRICE_FLAT_STR = "#ffffff"
    
    # 成交量颜色
    VOLUME_UP = QColor(255, 100, 100)   # 上涨成交量
    VOLUME_DOWN = QColor(100, 200, 100) # 下跌成交量
    
    # K线颜色
    CANDLE_UP_BODY = QColor(255, 68, 68)     # 阳线实体
    CANDLE_UP_BORDER = QColor(200, 50, 50)   # 阳线边框
    CANDLE_DOWN_BODY = QColor(0, 170, 0)     # 阴线实体
    CANDLE_DOWN_BORDER = QColor(0, 120, 0)   # 阴线边框
    CANDLE_WICK = QColor(150, 150, 150)      # 影线颜色
    
    # 移动平均线颜色
    MA5 = QColor(255, 255, 0)    # MA5 黄色
    MA10 = QColor(255, 0, 255)   # MA10 紫色
    MA20 = QColor(0, 255, 255)   # MA20 青色
    MA30 = QColor(255, 165, 0)   # MA30 橙色
    MA60 = QColor(0, 255, 0)     # MA60 绿色
    
    # 技术指标颜色
    MACD_DIF = QColor(255, 255, 255)     # DIF线白色
    MACD_DEA = QColor(255, 255, 0)       # DEA线黄色
    MACD_HISTOGRAM_UP = QColor(255, 68, 68)   # MACD柱状图上涨
    MACD_HISTOGRAM_DOWN = QColor(0, 170, 0)   # MACD柱状图下跌
    
    RSI_LINE = QColor(255, 255, 0)       # RSI线黄色
    RSI_OVERBOUGHT = QColor(255, 68, 68)  # 超买线红色
    RSI_OVERSOLD = QColor(0, 170, 0)     # 超卖线绿色
    
    KDJ_K = QColor(255, 255, 255)       # K线白色
    KDJ_D = QColor(255, 255, 0)          # D线黄色
    KDJ_J = QColor(255, 0, 255)          # J线紫色
    
    # 背景颜色
    CHART_BACKGROUND = QColor(30, 30, 30)        # 图表背景深灰
    GRID_COLOR = QColor(64, 64, 64)              # 网格线颜色
    AXIS_COLOR = QColor(128, 128, 128)           # 坐标轴颜色
    TEXT_COLOR = QColor(255, 255, 255)           # 文字颜色
    
    # 界面主题颜色
    PRIMARY_COLOR = QColor(0, 120, 212)          # 主色调蓝色
    SECONDARY_COLOR = QColor(64, 64, 64)         # 次要颜色
    ACCENT_COLOR = QColor(0, 120, 212)           # 强调色
    
    # 状态颜色
    SUCCESS_COLOR = QColor(0, 170, 0)            # 成功绿色
    WARNING_COLOR = QColor(255, 165, 0)          # 警告橙色
    ERROR_COLOR = QColor(255, 68, 68)            # 错误红色
    INFO_COLOR = QColor(0, 120, 212)             # 信息蓝色
    
    @classmethod
    def get_price_color(cls, change):
        """
        根据价格变化获取对应颜色
        
        Args:
            change (float): 价格变化值
            
        Returns:
            QColor: 对应的颜色
        """
        if change > 0:
            return cls.PRICE_UP
        elif change < 0:
            return cls.PRICE_DOWN
        else:
            return cls.PRICE_FLAT
            
    @classmethod
    def get_price_color_str(cls, change):
        """
        根据价格变化获取对应颜色字符串
        
        Args:
            change (float): 价格变化值
            
        Returns:
            str: 对应的颜色字符串
        """
        if change > 0:
            return cls.PRICE_UP_STR
        elif change < 0:
            return cls.PRICE_DOWN_STR
        else:
            return cls.PRICE_FLAT_STR
            
    @classmethod
    def get_candle_colors(cls, open_price, close_price):
        """
        根据开盘价和收盘价获取K线颜色
        
        Args:
            open_price (float): 开盘价
            close_price (float): 收盘价
            
        Returns:
            tuple: (实体颜色, 边框颜色)
        """
        if close_price >= open_price:
            return cls.CANDLE_UP_BODY, cls.CANDLE_UP_BORDER
        else:
            return cls.CANDLE_DOWN_BODY, cls.CANDLE_DOWN_BORDER
            
    @classmethod
    def get_ma_color(cls, period):
        """
        根据移动平均线周期获取颜色
        
        Args:
            period (int): MA周期
            
        Returns:
            QColor: 对应的颜色
        """
        color_map = {
            5: cls.MA5,
            10: cls.MA10,
            20: cls.MA20,
            30: cls.MA30,
            60: cls.MA60
        }
        return color_map.get(period, cls.TEXT_COLOR)
        
    @classmethod
    def get_volume_color(cls, price_change):
        """
        根据价格变化获取成交量颜色
        
        Args:
            price_change (float): 价格变化
            
        Returns:
            QColor: 对应的颜色
        """
        if price_change >= 0:
            return cls.VOLUME_UP
        else:
            return cls.VOLUME_DOWN


class ThemeColors:
    """
    主题颜色定义
    """
    
    # 深色主题
    DARK_THEME = {
        'background': '#1e1e1e',
        'surface': '#2d2d2d',
        'primary': '#0078d4',
        'secondary': '#404040',
        'text': '#ffffff',
        'text_secondary': '#cccccc',
        'border': '#404040',
        'hover': '#505050',
        'selected': '#0078d4',
        'disabled': '#808080'
    }
    
    # 浅色主题
    LIGHT_THEME = {
        'background': '#ffffff',
        'surface': '#f0f0f0',
        'primary': '#0078d4',
        'secondary': '#e0e0e0',
        'text': '#000000',
        'text_secondary': '#666666',
        'border': '#d0d0d0',
        'hover': '#e0e0e0',
        'selected': '#0078d4',
        'disabled': '#cccccc'
    }
    
    @classmethod
    def get_theme_colors(cls, theme_name='dark'):
        """
        获取主题颜色
        
        Args:
            theme_name (str): 主题名称 ('dark' 或 'light')
            
        Returns:
            dict: 主题颜色字典
        """
        if theme_name.lower() == 'light':
            return cls.LIGHT_THEME
        else:
            return cls.DARK_THEME