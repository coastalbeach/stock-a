#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
JSON策略加载器

该模块提供了从JSON文件加载策略定义的功能，允许用户通过简单的JSON文件定义策略，
而不需要编写Python代码。
"""

import json
import os
import re
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
import pandas as pd
import numpy as np

from .strategy_base import StrategyBase


class JSONStrategyLoader:
    """
    JSON策略加载器
    
    负责从JSON文件加载策略定义，并创建相应的策略实例。
    """
    
    def __init__(self, strategies_dir: Optional[str] = None):
        """
        初始化JSON策略加载器
        
        Args:
            strategies_dir: JSON策略文件的目录。如果为None，则使用默认目录。
        """
        if strategies_dir is None:
            self.strategies_dir = Path(__file__).parent / "strategies"
        else:
            self.strategies_dir = Path(strategies_dir)
            
        # 确保策略目录存在
        self.strategies_dir.mkdir(parents=True, exist_ok=True)
        
        # 缓存已加载的策略模式
        self._strategy_schemas = {}
    
    def load_strategy_from_json(self, json_path: Union[str, Path]) -> 'JSONStrategy':
        """
        从JSON文件加载策略
        
        Args:
            json_path: JSON策略文件路径
            
        Returns:
            JSONStrategy: 加载的策略实例
        """
        json_path = Path(json_path)
        if not json_path.exists():
            raise FileNotFoundError(f"策略文件不存在: {json_path}")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            strategy_def = json.load(f)
            
        return self.create_strategy_from_dict(strategy_def, strategy_path=json_path)
    
    def create_strategy_from_dict(self, strategy_def: Dict[str, Any], 
                                 strategy_path: Optional[Union[str, Path]] = None) -> 'JSONStrategy':
        """
        从字典创建策略实例
        
        Args:
            strategy_def: 策略定义字典
            strategy_path: 策略文件路径（可选）
            
        Returns:
            JSONStrategy: 创建的策略实例
        """
        # 验证策略定义
        self._validate_strategy_definition(strategy_def)
        
        # 创建策略实例
        strategy = JSONStrategy(
            name=strategy_def.get('name', 'Unnamed Strategy'),
            description=strategy_def.get('description', ''),
            required_data=strategy_def.get('required_data', []),
            buy_conditions=strategy_def.get('buy_conditions', []),
            sell_conditions=strategy_def.get('sell_conditions', []),
            parameters=strategy_def.get('parameters', {}),
            source_file=strategy_path
        )
        
        return strategy
    
    def _validate_strategy_definition(self, strategy_def: Dict[str, Any]) -> None:
        """
        验证策略定义是否有效
        
        Args:
            strategy_def: 策略定义字典
            
        Raises:
            ValueError: 如果策略定义无效
        """
        # 检查必需字段
        required_fields = ['name', 'buy_conditions', 'sell_conditions']
        for field in required_fields:
            if field not in strategy_def:
                raise ValueError(f"策略定义缺少必需字段: {field}")
        
        # 检查条件格式
        for condition_type in ['buy_conditions', 'sell_conditions']:
            if not isinstance(strategy_def[condition_type], list):
                raise ValueError(f"{condition_type} 必须是条件列表")
    
    def discover_strategies(self) -> Dict[str, Dict[str, Any]]:
        """
        发现并加载目录中的所有JSON策略
        
        Returns:
            Dict[str, Dict[str, Any]]: 策略名称到策略定义的映射
        """
        strategies = {}
        
        # 递归搜索所有JSON文件
        for json_file in self.strategies_dir.glob('**/*.json'):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    strategy_def = json.load(f)
                
                if 'name' in strategy_def:
                    strategies[strategy_def['name']] = {
                        'definition': strategy_def,
                        'file_path': json_file
                    }
            except Exception as e:
                print(f"加载策略文件 {json_file} 时出错: {e}")
        
        return strategies
    
    def get_strategy_schema(self) -> Dict[str, Any]:
        """
        获取JSON策略的模式定义
        
        Returns:
            Dict[str, Any]: 策略JSON模式
        """
        return {
            "type": "object",
            "required": ["name", "buy_conditions", "sell_conditions"],
            "properties": {
                "name": {
                    "type": "string",
                    "description": "策略名称"
                },
                "description": {
                    "type": "string",
                    "description": "策略描述"
                },
                "required_data": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "策略所需的数据列"
                },
                "parameters": {
                    "type": "object",
                    "description": "策略参数",
                    "additionalProperties": {
                        "type": "object",
                        "required": ["type", "default"],
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["integer", "number", "string", "boolean"]
                            },
                            "default": {
                                "description": "参数默认值"
                            },
                            "min": {
                                "type": "number",
                                "description": "最小值（仅适用于数值类型）"
                            },
                            "max": {
                                "type": "number",
                                "description": "最大值（仅适用于数值类型）"
                            },
                            "description": {
                                "type": "string",
                                "description": "参数描述"
                            }
                        }
                    }
                },
                "buy_conditions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["condition"],
                        "properties": {
                            "condition": {
                                "type": "string",
                                "description": "买入条件表达式"
                            },
                            "description": {
                                "type": "string",
                                "description": "条件描述"
                            },
                            "strength": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 1,
                                "description": "信号强度（0-1）"
                            }
                        }
                    },
                    "description": "买入条件列表"
                },
                "sell_conditions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["condition"],
                        "properties": {
                            "condition": {
                                "type": "string",
                                "description": "卖出条件表达式"
                            },
                            "description": {
                                "type": "string",
                                "description": "条件描述"
                            },
                            "strength": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 1,
                                "description": "信号强度（0-1）"
                            }
                        }
                    },
                    "description": "卖出条件列表"
                }
            }
        }


class JSONStrategy(StrategyBase):
    """
    基于JSON定义的策略
    
    通过JSON文件定义的策略，支持动态条件评估。
    """
    
    def __init__(self, name: str, description: str = "", 
                 required_data: List[str] = None,
                 buy_conditions: List[Dict[str, Any]] = None, 
                 sell_conditions: List[Dict[str, Any]] = None,
                 parameters: Dict[str, Dict[str, Any]] = None,
                 source_file: Optional[Union[str, Path]] = None):
        """
        初始化JSON策略
        
        Args:
            name: 策略名称
            description: 策略描述
            required_data: 策略所需的数据列
            buy_conditions: 买入条件列表
            sell_conditions: 卖出条件列表
            parameters: 策略参数
            source_file: 策略源文件路径
        """
        super().__init__(name)
        self.description = description
        self.required_data = required_data or []
        self.buy_conditions = buy_conditions or []
        self.sell_conditions = sell_conditions or []
        self.parameters = parameters or {}
        self.source_file = Path(source_file) if source_file else None
        
        # 初始化参数值为默认值
        self.param_values = {}
        for param_name, param_def in self.parameters.items():
            self.param_values[param_name] = param_def.get('default')
    
    def set_parameters(self, params: Dict[str, Any]) -> None:
        """
        设置策略参数
        
        Args:
            params: 参数名称到值的映射
        """
        for param_name, value in params.items():
            if param_name in self.parameters:
                # 验证参数值
                param_def = self.parameters[param_name]
                param_type = param_def.get('type')
                
                # 类型转换
                if param_type == 'integer':
                    value = int(value)
                elif param_type == 'number':
                    value = float(value)
                elif param_type == 'boolean':
                    if isinstance(value, str):
                        value = value.lower() in ('true', 'yes', '1')
                
                # 范围检查
                if param_type in ('integer', 'number'):
                    if 'min' in param_def and value < param_def['min']:
                        raise ValueError(f"参数 {param_name} 的值 {value} 小于最小值 {param_def['min']}")
                    if 'max' in param_def and value > param_def['max']:
                        raise ValueError(f"参数 {param_name} 的值 {value} 大于最大值 {param_def['max']}")
                
                self.param_values[param_name] = value
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        生成交易信号
        
        Args:
            data: 输入的行情数据
            
        Returns:
            包含交易信号的DataFrame
        """
        # 检查必需的数据列
        for col in self.required_data:
            if col not in data.columns:
                raise ValueError(f"数据缺少必需的列: {col}")
        
        # 创建信号DataFrame
        signals = []
        
        # 为条件评估准备环境
        env = self._prepare_evaluation_environment(data)
        
        # 逐行评估条件
        for i in range(len(data)):
            row_env = self._prepare_row_environment(data, i, env)
            
            # 评估买入条件
            buy_signal = False
            buy_strength = 0.0
            buy_reason = ""
            
            for condition in self.buy_conditions:
                try:
                    if self._evaluate_condition(condition['condition'], row_env):
                        buy_signal = True
                        strength = condition.get('strength', 1.0)
                        if strength > buy_strength:
                            buy_strength = strength
                            buy_reason = condition.get('description', condition['condition'])
                except Exception as e:
                    print(f"评估买入条件 '{condition['condition']}' 时出错: {e}")
            
            # 评估卖出条件
            sell_signal = False
            sell_strength = 0.0
            sell_reason = ""
            
            for condition in self.sell_conditions:
                try:
                    if self._evaluate_condition(condition['condition'], row_env):
                        sell_signal = True
                        strength = condition.get('strength', 1.0)
                        if strength > sell_strength:
                            sell_strength = strength
                            sell_reason = condition.get('description', condition['condition'])
                except Exception as e:
                    print(f"评估卖出条件 '{condition['condition']}' 时出错: {e}")
            
            # 确定最终信号
            signal_type = "持仓"  # 默认为持仓
            signal_strength = 0.0
            signal_reason = ""
            
            if buy_signal and sell_signal:
                # 买卖信号同时出现，选择强度更高的
                if buy_strength >= sell_strength:
                    signal_type = "买入"
                    signal_strength = buy_strength
                    signal_reason = buy_reason
                else:
                    signal_type = "卖出"
                    signal_strength = sell_strength
                    signal_reason = sell_reason
            elif buy_signal:
                signal_type = "买入"
                signal_strength = buy_strength
                signal_reason = buy_reason
            elif sell_signal:
                signal_type = "卖出"
                signal_strength = sell_strength
                signal_reason = sell_reason
            
            # 添加信号
            signal = {
                '日期': data['日期'].iloc[i] if '日期' in data.columns else pd.Timestamp('today'),
                '股票代码': data['股票代码'].iloc[i] if '股票代码' in data.columns else '',
                '信号类型': signal_type,
                '信号价格': data['收盘'].iloc[i] if '收盘' in data.columns else 0.0,
                '信号强度': signal_strength,
                '备注': signal_reason
            }
            signals.append(signal)
        
        return pd.DataFrame(signals)
    
    def _prepare_evaluation_environment(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        准备条件评估环境
        
        Args:
            data: 输入的行情数据
            
        Returns:
            评估环境字典
        """
        env = {
            'data': data,
            'len': len,
            'abs': abs,
            'min': min,
            'max': max,
            'sum': sum,
            'round': round,
            'pd': pd,
            'np': np,
            # 添加常用的技术指标函数
            'SMA': lambda series, window: series.rolling(window=window).mean(),
            'EMA': lambda series, window: series.ewm(span=window, adjust=False).mean(),
            'RSI': self._calculate_rsi,
            'MACD': self._calculate_macd,
            'BOLL': self._calculate_bollinger_bands,
            'ATR': lambda high, low, close, period: pd.Series(np.nan, index=high.index) if len(high) < period else pd.Series(
                [max(high.iloc[i] - low.iloc[i], abs(high.iloc[i] - close.iloc[i-1]), abs(low.iloc[i] - close.iloc[i-1])) 
                 for i in range(1, len(high))]).rolling(window=period).mean(),
            'HIGHEST': lambda data, period: data.rolling(window=period).max(),
            'LOWEST': lambda data, period: data.rolling(window=period).min(),
            # 添加参数
            'params': self.param_values
        }
        return env
    
    def _prepare_row_environment(self, data: pd.DataFrame, index: int, base_env: Dict[str, Any]) -> Dict[str, Any]:
        """
        准备单行数据的评估环境
        
        Args:
            data: 输入的行情数据
            index: 当前行索引
            base_env: 基础评估环境
            
        Returns:
            行评估环境字典
        """
        row_env = base_env.copy()
        
        # 添加当前行数据
        row = data.iloc[index]
        for col in data.columns:
            row_env[col] = row[col]
        
        # 添加历史数据访问函数
        def history(field: str, periods: int = 1, include_current: bool = True) -> pd.Series:
            """
            获取历史数据
            
            Args:
                field: 字段名
                periods: 历史周期数
                include_current: 是否包含当前值
                
            Returns:
                历史数据Series
            """
            if field not in data.columns:
                raise ValueError(f"字段 {field} 不存在")
                
            if include_current:
                start_idx = max(0, index - periods + 1)
                end_idx = index + 1  # 包含当前行
            else:
                start_idx = max(0, index - periods)
                end_idx = index  # 不包含当前行
                
            return data[field].iloc[start_idx:end_idx]
        
        row_env['history'] = history
        row_env['index'] = index
        
        return row_env
    
    def _evaluate_condition(self, condition: str, env: Dict[str, Any]) -> bool:
        """
        评估条件表达式
        
        Args:
            condition: 条件表达式
            env: 评估环境
            
        Returns:
            条件评估结果
        """
        # 安全地评估表达式
        try:
            # 替换常见的比较操作符，使表达式更易读
            condition = condition.replace('>=', ' >= ')
            condition = condition.replace('<=', ' <= ')
            condition = condition.replace('!=', ' != ')
            condition = condition.replace('==', ' == ')
            condition = condition.replace('>', ' > ')
            condition = condition.replace('<', ' < ')
            
            # 替换 AND 和 OR 操作符
            condition = re.sub(r'\b(?i:and)\b', ' and ', condition)
            condition = re.sub(r'\b(?i:or)\b', ' or ', condition)
            
            # 评估表达式
            return eval(condition, {"__builtins__": {}}, env)
        except Exception as e:
            print(f"评估条件 '{condition}' 时出错: {e}")
            return False
    
    def _calculate_rsi(self, series: pd.Series, window: int = 14) -> pd.Series:
        """
        计算RSI指标
        
        Args:
            series: 价格序列
            window: 周期
            
        Returns:
            RSI值序列
        """
        delta = series.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=window).mean()
        avg_loss = loss.rolling(window=window).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_macd(self, series: pd.Series, fast_period: int = 12, 
                       slow_period: int = 26, signal_period: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        计算MACD指标
        
        Args:
            series: 价格序列
            fast_period: 快线周期
            slow_period: 慢线周期
            signal_period: 信号线周期
            
        Returns:
            (MACD线, 信号线, 柱状图)
        """
        ema_fast = series.ewm(span=fast_period, adjust=False).mean()
        ema_slow = series.ewm(span=slow_period, adjust=False).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def _calculate_bollinger_bands(self, series: pd.Series, window: int = 20, 
                                  num_std: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        计算布林带指标
        
        Args:
            series: 价格序列
            window: 移动平均周期
            num_std: 标准差倍数
            
        Returns:
            (中轨, 上轨, 下轨)
        """
        middle_band = series.rolling(window=window).mean()
        std_dev = series.rolling(window=window).std()
        
        upper_band = middle_band + (std_dev * num_std)
        lower_band = middle_band - (std_dev * num_std)
        
        return middle_band, upper_band, lower_band
    
    def get_param_schema(self) -> Dict[str, Dict[str, Any]]:
        """
        获取参数模式
        
        Returns:
            参数模式字典
        """
        return self.parameters
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将策略转换为字典
        
        Returns:
            策略定义字典
        """
        return {
            'name': self.name,
            'description': self.description,
            'required_data': self.required_data,
            'parameters': self.parameters,
            'buy_conditions': self.buy_conditions,
            'sell_conditions': self.sell_conditions
        }
    
    def save(self, file_path: Optional[Union[str, Path]] = None) -> Path:
        """
        保存策略到JSON文件
        
        Args:
            file_path: 文件路径。如果为None，则使用源文件路径或生成新路径。
            
        Returns:
            保存的文件路径
        """
        if file_path is None:
            if self.source_file is not None:
                file_path = self.source_file
            else:
                # 生成文件名
                strategies_dir = Path(__file__).parent / "strategies"
                strategies_dir.mkdir(parents=True, exist_ok=True)
                file_path = strategies_dir / f"{self.name.replace(' ', '_').lower()}.json"
        else:
            file_path = Path(file_path)
        
        # 确保目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存策略定义
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        
        # 更新源文件路径
        self.source_file = file_path
        
        return file_path
    
    def __repr__(self) -> str:
        return f"JSONStrategy(name='{self.name}', conditions={len(self.buy_conditions)}买入/{len(self.sell_conditions)}卖出)"