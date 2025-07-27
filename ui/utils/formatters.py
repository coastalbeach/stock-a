#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据格式化工具
提供各种数据的格式化显示功能
"""

from datetime import datetime, date
from typing import Union, Optional
import locale


def format_number(value, decimals=2, thousands_sep=True):
    """
    格式化数字显示
    
    Args:
        value: 数值
        decimals: 小数位数
        thousands_sep: 是否使用千位分隔符
        
    Returns:
        str: 格式化后的字符串
    """
    try:
        num_value = float(value)
        
        if thousands_sep:
            if decimals == 0:
                return f"{num_value:,.0f}"
            else:
                return f"{num_value:,.{decimals}f}"
        else:
            if decimals == 0:
                return f"{num_value:.0f}"
            else:
                return f"{num_value:.{decimals}f}"
                
    except (ValueError, TypeError):
        return "--"


def format_percentage(value, decimals=2, show_sign=True):
    """
    格式化百分比显示
    
    Args:
        value: 百分比值（如0.05表示5%）
        decimals: 小数位数
        show_sign: 是否显示正负号
        
    Returns:
        str: 格式化后的百分比字符串
    """
    try:
        percent_value = float(value) * 100
        
        if show_sign and percent_value > 0:
            return f"+{percent_value:.{decimals}f}%"
        else:
            return f"{percent_value:.{decimals}f}%"
            
    except (ValueError, TypeError):
        return "--"


def format_currency(value, currency='CNY', decimals=2):
    """
    格式化货币显示
    
    Args:
        value: 金额
        currency: 货币类型
        decimals: 小数位数
        
    Returns:
        str: 格式化后的货币字符串
    """
    try:
        amount = float(value)
        
        if currency == 'CNY':
            return f"¥{amount:,.{decimals}f}"
        elif currency == 'USD':
            return f"${amount:,.{decimals}f}"
        elif currency == 'HKD':
            return f"HK${amount:,.{decimals}f}"
        else:
            return f"{amount:,.{decimals}f} {currency}"
            
    except (ValueError, TypeError):
        return "--"


def format_volume(volume):
    """
    格式化成交量显示
    
    Args:
        volume: 成交量
        
    Returns:
        str: 格式化后的成交量字符串
    """
    try:
        vol = int(volume)
        
        if vol >= 100000000:  # 亿
            return f"{vol / 100000000:.2f}亿"
        elif vol >= 10000:  # 万
            return f"{vol / 10000:.2f}万"
        else:
            return f"{vol:,}"
            
    except (ValueError, TypeError):
        return "--"


def format_market_cap(market_cap):
    """
    格式化市值显示
    
    Args:
        market_cap: 市值
        
    Returns:
        str: 格式化后的市值字符串
    """
    try:
        cap = float(market_cap)
        
        if cap >= 1000000000000:  # 万亿
            return f"{cap / 1000000000000:.2f}万亿"
        elif cap >= 100000000:  # 亿
            return f"{cap / 100000000:.2f}亿"
        elif cap >= 10000:  # 万
            return f"{cap / 10000:.2f}万"
        else:
            return f"{cap:,.0f}"
            
    except (ValueError, TypeError):
        return "--"


def format_price_change(current_price, previous_price, show_percentage=True):
    """
    格式化价格变化显示
    
    Args:
        current_price: 当前价格
        previous_price: 前一价格
        show_percentage: 是否显示百分比
        
    Returns:
        tuple: (变化值字符串, 变化百分比字符串, 颜色)
    """
    try:
        current = float(current_price)
        previous = float(previous_price)
        
        change = current - previous
        change_percent = (change / previous) * 100 if previous != 0 else 0
        
        # 确定颜色
        if change > 0:
            color = "#F44336"  # 红色（上涨）
            sign = "+"
        elif change < 0:
            color = "#4CAF50"  # 绿色（下跌）
            sign = ""
        else:
            color = "#FFFFFF"  # 白色（平盘）
            sign = ""
            
        change_str = f"{sign}{change:.2f}"
        percent_str = f"{sign}{change_percent:.2f}%" if show_percentage else ""
        
        return change_str, percent_str, color
        
    except (ValueError, TypeError):
        return "--", "--", "#FFFFFF"


def format_date(date_value, format_str='%Y-%m-%d'):
    """
    格式化日期显示
    
    Args:
        date_value: 日期值
        format_str: 格式字符串
        
    Returns:
        str: 格式化后的日期字符串
    """
    try:
        if isinstance(date_value, str):
            # 尝试解析字符串日期
            if 'T' in date_value:  # ISO格式
                dt = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
            else:
                dt = datetime.strptime(date_value, '%Y-%m-%d')
        elif isinstance(date_value, datetime):
            dt = date_value
        elif isinstance(date_value, date):
            dt = datetime.combine(date_value, datetime.min.time())
        else:
            return "--"
            
        return dt.strftime(format_str)
        
    except (ValueError, TypeError):
        return "--"


def format_time(time_value, format_str='%H:%M:%S'):
    """
    格式化时间显示
    
    Args:
        time_value: 时间值
        format_str: 格式字符串
        
    Returns:
        str: 格式化后的时间字符串
    """
    try:
        if isinstance(time_value, str):
            dt = datetime.fromisoformat(time_value.replace('Z', '+00:00'))
        elif isinstance(time_value, datetime):
            dt = time_value
        else:
            return "--"
            
        return dt.strftime(format_str)
        
    except (ValueError, TypeError):
        return "--"


def format_datetime(datetime_value, format_str='%Y-%m-%d %H:%M:%S'):
    """
    格式化日期时间显示
    
    Args:
        datetime_value: 日期时间值
        format_str: 格式字符串
        
    Returns:
        str: 格式化后的日期时间字符串
    """
    return format_date(datetime_value, format_str)


def format_ratio(value, decimals=2):
    """
    格式化比率显示
    
    Args:
        value: 比率值
        decimals: 小数位数
        
    Returns:
        str: 格式化后的比率字符串
    """
    try:
        ratio = float(value)
        return f"{ratio:.{decimals}f}"
    except (ValueError, TypeError):
        return "--"


def format_pe_ratio(pe_value):
    """
    格式化市盈率显示
    
    Args:
        pe_value: 市盈率值
        
    Returns:
        str: 格式化后的市盈率字符串
    """
    try:
        pe = float(pe_value)
        if pe < 0:
            return "--"  # 负市盈率显示为--
        elif pe > 1000:
            return ">1000"  # 过高的市盈率
        else:
            return f"{pe:.2f}"
    except (ValueError, TypeError):
        return "--"


def format_pb_ratio(pb_value):
    """
    格式化市净率显示
    
    Args:
        pb_value: 市净率值
        
    Returns:
        str: 格式化后的市净率字符串
    """
    try:
        pb = float(pb_value)
        if pb < 0:
            return "--"  # 负市净率显示为--
        else:
            return f"{pb:.2f}"
    except (ValueError, TypeError):
        return "--"


def format_turnover_rate(turnover):
    """
    格式化换手率显示
    
    Args:
        turnover: 换手率值（小数形式，如0.05表示5%）
        
    Returns:
        str: 格式化后的换手率字符串
    """
    return format_percentage(turnover, decimals=2, show_sign=False)


def format_amplitude(high, low, previous_close):
    """
    格式化振幅显示
    
    Args:
        high: 最高价
        low: 最低价
        previous_close: 前收盘价
        
    Returns:
        str: 格式化后的振幅字符串
    """
    try:
        high_price = float(high)
        low_price = float(low)
        prev_close = float(previous_close)
        
        if prev_close == 0:
            return "--"
            
        amplitude = ((high_price - low_price) / prev_close) * 100
        return f"{amplitude:.2f}%"
        
    except (ValueError, TypeError):
        return "--"


def format_file_size(size_bytes):
    """
    格式化文件大小显示
    
    Args:
        size_bytes: 文件大小（字节）
        
    Returns:
        str: 格式化后的文件大小字符串
    """
    try:
        size = int(size_bytes)
        
        if size >= 1024**3:  # GB
            return f"{size / (1024**3):.2f} GB"
        elif size >= 1024**2:  # MB
            return f"{size / (1024**2):.2f} MB"
        elif size >= 1024:  # KB
            return f"{size / 1024:.2f} KB"
        else:
            return f"{size} B"
            
    except (ValueError, TypeError):
        return "--"


def format_duration(seconds):
    """
    格式化时长显示
    
    Args:
        seconds: 秒数
        
    Returns:
        str: 格式化后的时长字符串
    """
    try:
        total_seconds = int(seconds)
        
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"
            
    except (ValueError, TypeError):
        return "--"


def format_stock_name(name, max_length=10):
    """
    格式化股票名称显示
    
    Args:
        name: 股票名称
        max_length: 最大显示长度
        
    Returns:
        str: 格式化后的股票名称
    """
    if not name:
        return "--"
        
    if len(name) > max_length:
        return name[:max_length-2] + "..."
    else:
        return name


def format_industry(industry):
    """
    格式化行业显示
    
    Args:
        industry: 行业名称
        
    Returns:
        str: 格式化后的行业名称
    """
    if not industry:
        return "其他"
    return industry


def format_concept(concepts, max_count=3):
    """
    格式化概念显示
    
    Args:
        concepts: 概念列表或字符串
        max_count: 最大显示数量
        
    Returns:
        str: 格式化后的概念字符串
    """
    if not concepts:
        return "--"
        
    if isinstance(concepts, str):
        concept_list = concepts.split(',')
    else:
        concept_list = concepts
        
    if len(concept_list) > max_count:
        return ', '.join(concept_list[:max_count]) + '...'
    else:
        return ', '.join(concept_list)