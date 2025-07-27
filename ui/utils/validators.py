#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
输入验证器
提供各种输入数据的验证功能
"""

from PyQt6.QtGui import QValidator
from PyQt6.QtCore import QRegularExpression
from PyQt6.QtGui import QRegularExpressionValidator
import re
from typing import Union, Tuple


class StockCodeValidator(QValidator):
    """
    股票代码验证器
    支持A股、港股、美股等不同市场的股票代码格式
    """
    
    def __init__(self, market='A', parent=None):
        super().__init__(parent)
        self.market = market
        
    def validate(self, input_str, pos):
        """
        验证股票代码
        
        Args:
            input_str: 输入字符串
            pos: 光标位置
            
        Returns:
            tuple: (状态, 字符串, 位置)
        """
        if not input_str:
            return (QValidator.State.Intermediate, input_str, pos)
            
        if self.market == 'A':
            # A股代码：6位数字
            if re.match(r'^\d{0,6}$', input_str):
                if len(input_str) == 6:
                    return (QValidator.State.Acceptable, input_str, pos)
                else:
                    return (QValidator.State.Intermediate, input_str, pos)
        elif self.market == 'HK':
            # 港股代码：1-5位数字
            if re.match(r'^\d{1,5}$', input_str):
                return (QValidator.State.Acceptable, input_str, pos)
        elif self.market == 'US':
            # 美股代码：1-5位字母
            if re.match(r'^[A-Za-z]{1,5}$', input_str):
                return (QValidator.State.Acceptable, input_str, pos)
            elif re.match(r'^[A-Za-z]{0,5}$', input_str):
                return (QValidator.State.Intermediate, input_str, pos)
                
        return (QValidator.State.Invalid, input_str, pos)
        
    def fixup(self, input_str):
        """
        修复输入字符串
        
        Args:
            input_str: 输入字符串
            
        Returns:
            str: 修复后的字符串
        """
        if self.market == 'A':
            # 移除非数字字符
            return re.sub(r'\D', '', input_str)[:6]
        elif self.market == 'HK':
            return re.sub(r'\D', '', input_str)[:5]
        elif self.market == 'US':
            # 移除非字母字符并转换为大写
            return re.sub(r'[^A-Za-z]', '', input_str).upper()[:5]
            
        return input_str


class NumberValidator(QValidator):
    """
    数字验证器
    支持整数和浮点数验证
    """
    
    def __init__(self, min_value=None, max_value=None, decimals=2, parent=None):
        super().__init__(parent)
        self.min_value = min_value
        self.max_value = max_value
        self.decimals = decimals
        
    def validate(self, input_str, pos):
        """
        验证数字输入
        
        Args:
            input_str: 输入字符串
            pos: 光标位置
            
        Returns:
            tuple: (状态, 字符串, 位置)
        """
        if not input_str or input_str == '-':
            return (QValidator.State.Intermediate, input_str, pos)
            
        # 检查是否为有效的数字格式
        if self.decimals > 0:
            pattern = r'^-?\d*\.?\d*$'
        else:
            pattern = r'^-?\d*$'
            
        if not re.match(pattern, input_str):
            return (QValidator.State.Invalid, input_str, pos)
            
        # 检查小数位数
        if '.' in input_str:
            decimal_part = input_str.split('.')[1]
            if len(decimal_part) > self.decimals:
                return (QValidator.State.Invalid, input_str, pos)
                
        try:
            value = float(input_str)
            
            # 检查范围
            if self.min_value is not None and value < self.min_value:
                return (QValidator.State.Invalid, input_str, pos)
            if self.max_value is not None and value > self.max_value:
                return (QValidator.State.Invalid, input_str, pos)
                
            return (QValidator.State.Acceptable, input_str, pos)
            
        except ValueError:
            return (QValidator.State.Intermediate, input_str, pos)
            
    def fixup(self, input_str):
        """
        修复输入字符串
        
        Args:
            input_str: 输入字符串
            
        Returns:
            str: 修复后的字符串
        """
        try:
            value = float(input_str)
            
            # 限制范围
            if self.min_value is not None:
                value = max(value, self.min_value)
            if self.max_value is not None:
                value = min(value, self.max_value)
                
            # 限制小数位数
            if self.decimals == 0:
                return str(int(value))
            else:
                return f"{value:.{self.decimals}f}"
                
        except ValueError:
            return "0"


class PercentageValidator(NumberValidator):
    """
    百分比验证器
    验证0-100之间的百分比值
    """
    
    def __init__(self, parent=None):
        super().__init__(min_value=0, max_value=100, decimals=2, parent=parent)


def validate_stock_code(code, market='A'):
    """
    验证股票代码
    
    Args:
        code: 股票代码
        market: 市场类型 ('A', 'HK', 'US')
        
    Returns:
        bool: 是否有效
    """
    if not code:
        return False
        
    if market == 'A':
        # A股代码：6位数字，以0、3、6开头
        return bool(re.match(r'^[036]\d{5}$', code))
    elif market == 'HK':
        # 港股代码：1-5位数字
        return bool(re.match(r'^\d{1,5}$', code))
    elif market == 'US':
        # 美股代码：1-5位字母
        return bool(re.match(r'^[A-Z]{1,5}$', code.upper()))
        
    return False


def validate_number(value, min_value=None, max_value=None, decimals=None):
    """
    验证数字
    
    Args:
        value: 要验证的值
        min_value: 最小值
        max_value: 最大值
        decimals: 最大小数位数
        
    Returns:
        bool: 是否有效
    """
    try:
        num_value = float(value)
        
        # 检查范围
        if min_value is not None and num_value < min_value:
            return False
        if max_value is not None and num_value > max_value:
            return False
            
        # 检查小数位数
        if decimals is not None:
            decimal_str = str(value)
            if '.' in decimal_str:
                decimal_part = decimal_str.split('.')[1]
                if len(decimal_part) > decimals:
                    return False
                    
        return True
        
    except (ValueError, TypeError):
        return False


def validate_percentage(value):
    """
    验证百分比值
    
    Args:
        value: 要验证的值
        
    Returns:
        bool: 是否有效（0-100之间）
    """
    return validate_number(value, min_value=0, max_value=100, decimals=2)


def validate_price(price):
    """
    验证价格
    
    Args:
        price: 价格值
        
    Returns:
        bool: 是否有效（大于0，最多2位小数）
    """
    return validate_number(price, min_value=0.01, decimals=2)


def validate_volume(volume):
    """
    验证成交量
    
    Args:
        volume: 成交量
        
    Returns:
        bool: 是否有效（非负整数）
    """
    try:
        vol_value = int(volume)
        return vol_value >= 0
    except (ValueError, TypeError):
        return False


def validate_date_range(start_date, end_date):
    """
    验证日期范围
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
        
    Returns:
        bool: 是否有效（开始日期不能晚于结束日期）
    """
    try:
        from datetime import datetime
        
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
            
        return start_date <= end_date
        
    except (ValueError, TypeError):
        return False


def validate_email(email):
    """
    验证邮箱地址
    
    Args:
        email: 邮箱地址
        
    Returns:
        bool: 是否有效
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_phone(phone):
    """
    验证手机号码
    
    Args:
        phone: 手机号码
        
    Returns:
        bool: 是否有效
    """
    # 中国大陆手机号码格式
    pattern = r'^1[3-9]\d{9}$'
    return bool(re.match(pattern, phone))


def sanitize_filename(filename):
    """
    清理文件名，移除不安全字符
    
    Args:
        filename: 原始文件名
        
    Returns:
        str: 清理后的文件名
    """
    # 移除或替换不安全字符
    unsafe_chars = r'[<>:"/\\|?*]'
    safe_filename = re.sub(unsafe_chars, '_', filename)
    
    # 移除前后空格和点
    safe_filename = safe_filename.strip(' .')
    
    # 确保文件名不为空
    if not safe_filename:
        safe_filename = 'untitled'
        
    return safe_filename


def validate_api_key(api_key, min_length=16):
    """
    验证API密钥格式
    
    Args:
        api_key: API密钥
        min_length: 最小长度
        
    Returns:
        bool: 是否有效
    """
    if not api_key or len(api_key) < min_length:
        return False
        
    # 检查是否包含有效字符（字母、数字、部分特殊字符）
    pattern = r'^[A-Za-z0-9_-]+$'
    return bool(re.match(pattern, api_key))