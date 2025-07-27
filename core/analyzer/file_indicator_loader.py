# -*- coding: utf-8 -*-
"""
文件指标加载器模块

负责从JSON/YAML文件加载衍生指标定义，实现指标定义与运行程序的完全分离。
每个指标都有独立的配置文件，包含所属表、所需信息、运算逻辑等一切信息。
支持从数据库任意表中获取数据，包括日、周、月频数据。

特点：
1. 指标定义与代码完全分离
2. 支持复杂的数据源配置（多表、多列、多频率）
3. 支持灵活的运算逻辑定义
4. 只需编辑配置文件即可新增/删除指标
5. 支持条件逻辑、数学运算、技术分析函数
"""

import os
import sys
import json
import yaml
import logging
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Union, Optional, Any, Callable
from datetime import datetime, timedelta

# 添加项目根目录到系统路径
project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

# 导入项目模块
from db.enhanced_postgresql_manager import EnhancedPostgreSQLManager
from utils.config_loader import load_connection_config

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class IndicatorCalculationEngine:
    """指标计算引擎
    
    负责解析和执行指标定义文件中的运算逻辑。
    支持各种数学运算、条件判断、技术分析函数等。
    """
    
    def __init__(self):
        """初始化计算引擎"""
        # 注册内置函数
        self.functions = {
            # 数学函数
            'abs': abs,
            'max': max,
            'min': min,
            'sum': sum,
            'mean': np.mean,
            'std': np.std,
            'sqrt': np.sqrt,
            'log': np.log,
            'exp': np.exp,
            
            # 技术分析函数
            'sma': self._sma,
            'ema': self._ema,
            'rsi': self._rsi,
            'macd': self._macd,
            'bollinger': self._bollinger,
            'crossover': self._crossover,
            'crossunder': self._crossunder,
            
            # 条件函数
            'if_then_else': self._if_then_else,
            'greater_than': lambda x, y: x > y,
            'less_than': lambda x, y: x < y,
            'equal_to': lambda x, y: x == y,
            'and_': lambda x, y: x and y,
            'or_': lambda x, y: x or y,
            'not_': lambda x: not x,
            
            # 数据处理函数
            'shift': self._shift,
            'rolling_max': self._rolling_max,
            'rolling_min': self._rolling_min,
            'rolling_mean': self._rolling_mean,
            'pct_change': self._pct_change,
            'rank': self._rank,
        }
    
    def calculate(self, formula: Union[str, Dict], data: Dict[str, pd.Series]) -> pd.Series:
        """计算指标值
        
        Args:
            formula: 计算公式，可以是字符串表达式或字典结构
            data: 数据字典，键为列名，值为pandas Series
            
        Returns:
            pd.Series: 计算结果
        """
        if isinstance(formula, str):
            return self._evaluate_expression(formula, data)
        elif isinstance(formula, dict):
            return self._evaluate_structured_formula(formula, data)
        else:
            raise ValueError(f"不支持的公式类型: {type(formula)}")
    
    def _evaluate_expression(self, expression: str, data: Dict[str, pd.Series]) -> pd.Series:
        """计算字符串表达式
        
        Args:
            expression: 字符串表达式，如 "close > sma(close, 20)"
            data: 数据字典
            
        Returns:
            pd.Series: 计算结果
        """
        # 创建安全的执行环境
        safe_dict = {
            '__builtins__': {},
            'np': np,
            'pd': pd,
        }
        
        # 添加数据列
        safe_dict.update(data)
        
        # 添加函数
        safe_dict.update(self.functions)
        
        try:
            result = eval(expression, safe_dict)
            if isinstance(result, (int, float, bool)):
                # 如果结果是标量，创建与数据长度相同的Series
                index = next(iter(data.values())).index
                result = pd.Series([result] * len(index), index=index)
            return result
        except Exception as e:
            logger.error(f"计算表达式失败: {expression}, 错误: {e}")
            raise
    
    def _evaluate_structured_formula(self, formula: Dict, data: Dict[str, pd.Series]) -> pd.Series:
        """计算结构化公式
        
        Args:
            formula: 结构化公式字典
            data: 数据字典
            
        Returns:
            pd.Series: 计算结果
        """
        operation = formula.get('operation')
        
        if operation == 'condition':
            # 条件判断
            condition = self._evaluate_condition(formula['condition'], data)
            true_value = self._get_value(formula['true_value'], data)
            false_value = self._get_value(formula['false_value'], data)
            return pd.Series(np.where(condition, true_value, false_value), index=condition.index)
        
        elif operation == 'crossover':
            # 金叉
            series1 = self._get_value(formula['series1'], data)
            series2 = self._get_value(formula['series2'], data)
            return self._crossover(series1, series2)
        
        elif operation == 'crossunder':
            # 死叉
            series1 = self._get_value(formula['series1'], data)
            series2 = self._get_value(formula['series2'], data)
            return self._crossunder(series1, series2)
        
        elif operation == 'function':
            # 函数调用
            func_name = formula['function']
            args = [self._get_value(arg, data) for arg in formula.get('args', [])]
            kwargs = {k: self._get_value(v, data) for k, v in formula.get('kwargs', {}).items()}
            
            if func_name in self.functions:
                return self.functions[func_name](*args, **kwargs)
            else:
                raise ValueError(f"未知函数: {func_name}")
        
        else:
            raise ValueError(f"未知操作: {operation}")
    
    def _evaluate_condition(self, condition: Dict, data: Dict[str, pd.Series]) -> pd.Series:
        """计算条件表达式
        
        Args:
            condition: 条件字典
            data: 数据字典
            
        Returns:
            pd.Series: 布尔值Series
        """
        operator = condition['operator']
        left = self._get_value(condition['left'], data)
        right = self._get_value(condition['right'], data)
        
        if operator == '>':
            return left > right
        elif operator == '<':
            return left < right
        elif operator == '>=':
            return left >= right
        elif operator == '<=':
            return left <= right
        elif operator == '==':
            return left == right
        elif operator == '!=':
            return left != right
        elif operator == 'and':
            return left & right
        elif operator == 'or':
            return left | right
        else:
            raise ValueError(f"未知操作符: {operator}")
    
    def _get_value(self, value_def: Union[str, int, float, Dict], data: Dict[str, pd.Series]) -> Union[pd.Series, float, int]:
        """获取值
        
        Args:
            value_def: 值定义，可以是列名、常数或嵌套公式
            data: 数据字典
            
        Returns:
            值或Series
        """
        if isinstance(value_def, (int, float)):
            return value_def
        elif isinstance(value_def, str):
            if value_def in data:
                return data[value_def]
            else:
                # 尝试作为表达式计算
                return self._evaluate_expression(value_def, data)
        elif isinstance(value_def, dict):
            return self._evaluate_structured_formula(value_def, data)
        else:
            raise ValueError(f"不支持的值类型: {type(value_def)}")
    
    # 技术分析函数实现
    def _sma(self, series: pd.Series, period: int) -> pd.Series:
        """简单移动平均"""
        return series.rolling(window=period).mean()
    
    def _ema(self, series: pd.Series, period: int) -> pd.Series:
        """指数移动平均"""
        return series.ewm(span=period).mean()
    
    def _rsi(self, series: pd.Series, period: int = 14) -> pd.Series:
        """相对强弱指数"""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _macd(self, series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
        """MACD指标"""
        ema_fast = self._ema(series, fast)
        ema_slow = self._ema(series, slow)
        macd_line = ema_fast - ema_slow
        signal_line = self._ema(macd_line, signal)
        histogram = macd_line - signal_line
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }
    
    def _bollinger(self, series: pd.Series, period: int = 20, std_dev: float = 2) -> Dict[str, pd.Series]:
        """布林带"""
        sma = self._sma(series, period)
        std = series.rolling(window=period).std()
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        return {
            'upper': upper,
            'middle': sma,
            'lower': lower
        }
    
    def _crossover(self, series1: pd.Series, series2: pd.Series) -> pd.Series:
        """金叉：series1从下方穿过series2"""
        return (series1 > series2) & (series1.shift(1) <= series2.shift(1))
    
    def _crossunder(self, series1: pd.Series, series2: pd.Series) -> pd.Series:
        """死叉：series1从上方穿过series2"""
        return (series1 < series2) & (series1.shift(1) >= series2.shift(1))
    
    def _if_then_else(self, condition: pd.Series, true_value: Union[pd.Series, float], false_value: Union[pd.Series, float]) -> pd.Series:
        """条件选择"""
        return pd.Series(np.where(condition, true_value, false_value), index=condition.index)
    
    def _shift(self, series: pd.Series, periods: int) -> pd.Series:
        """数据移位"""
        return series.shift(periods)
    
    def _rolling_max(self, series: pd.Series, window: int) -> pd.Series:
        """滚动最大值"""
        return series.rolling(window=window).max()
    
    def _rolling_min(self, series: pd.Series, window: int) -> pd.Series:
        """滚动最小值"""
        return series.rolling(window=window).min()
    
    def _rolling_mean(self, series: pd.Series, window: int) -> pd.Series:
        """滚动平均值"""
        return series.rolling(window=window).mean()
    
    def _pct_change(self, series: pd.Series, periods: int = 1) -> pd.Series:
        """百分比变化"""
        return series.pct_change(periods=periods)
    
    def _rank(self, series: pd.Series, window: int = None) -> pd.Series:
        """排名"""
        if window:
            return series.rolling(window=window).rank()
        else:
            return series.rank()


class FileIndicatorLoader:
    """文件指标加载器
    
    负责从JSON/YAML文件加载衍生指标定义，实现指标定义与运行程序的完全分离。
    """
    
    def __init__(self, indicators_dir=None, db_config=None):
        """初始化加载器
        
        Args:
            indicators_dir (str, optional): 指标定义文件目录，如果为None则使用默认目录
            db_config (dict, optional): 数据库连接配置
        """
        if indicators_dir is None:
            self.indicators_dir = os.path.join(project_root, 'core', 'analyzer', 'indicators')
        else:
            self.indicators_dir = indicators_dir
        
        # 初始化数据库连接
        if db_config is None:
            self.db_config = load_connection_config()
        else:
            self.db_config = db_config
        
        self.reader = EnhancedPostgreSQLManager()
        
        # 初始化计算引擎
        self.calculation_engine = IndicatorCalculationEngine()
        
        # 加载所有指标定义
        self.indicators = self._load_all_indicators()
        
        logger.info(f"已加载 {len(self.indicators)} 个指标定义")
    
    def _load_all_indicators(self) -> Dict[str, Dict]:
        """加载所有指标定义文件
        
        Returns:
            Dict[str, Dict]: 指标名称到定义的映射
        """
        indicators = {}
        
        # 遍历所有子目录
        for entity_type in ['common', 'stock', 'industry', 'index']:
            entity_dir = os.path.join(self.indicators_dir, entity_type)
            if not os.path.exists(entity_dir):
                continue
            
            # 加载该实体类型的所有指标文件
            for file_path in Path(entity_dir).glob('*.json'):
                try:
                    indicator_def = self._load_indicator_file(file_path)
                    indicator_name = indicator_def['name']
                    indicator_def['entity_type'] = entity_type
                    indicator_def['file_path'] = str(file_path)
                    indicators[indicator_name] = indicator_def
                    logger.debug(f"加载指标: {indicator_name} ({entity_type})")
                except Exception as e:
                    logger.error(f"加载指标文件失败: {file_path}, 错误: {e}")
            
            # 加载YAML文件
            for file_path in Path(entity_dir).glob('*.yaml'):
                try:
                    indicator_def = self._load_indicator_file(file_path)
                    indicator_name = indicator_def['name']
                    indicator_def['entity_type'] = entity_type
                    indicator_def['file_path'] = str(file_path)
                    indicators[indicator_name] = indicator_def
                    logger.debug(f"加载指标: {indicator_name} ({entity_type})")
                except Exception as e:
                    logger.error(f"加载指标文件失败: {file_path}, 错误: {e}")
        
        return indicators
    
    def _load_indicator_file(self, file_path: Path) -> Dict:
        """加载单个指标定义文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            Dict: 指标定义
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            if file_path.suffix.lower() == '.json':
                return json.load(f)
            elif file_path.suffix.lower() in ['.yaml', '.yml']:
                return yaml.safe_load(f)
            else:
                raise ValueError(f"不支持的文件格式: {file_path.suffix}")
    
    def get_indicator(self, indicator_name: str) -> Optional[Dict]:
        """获取指标定义
        
        Args:
            indicator_name: 指标名称
            
        Returns:
            Optional[Dict]: 指标定义，如果不存在则返回None
        """
        return self.indicators.get(indicator_name)
    
    def get_indicators_by_entity_type(self, entity_type: str) -> Dict[str, Dict]:
        """获取指定实体类型的所有指标
        
        Args:
            entity_type: 实体类型 ('common', 'stock', 'industry', 'index')
            
        Returns:
            Dict[str, Dict]: 指标名称到定义的映射
        """
        return {name: definition for name, definition in self.indicators.items() 
                if definition.get('entity_type') == entity_type or entity_type == 'common'}
    
    def calculate_indicator(self, indicator_name: str, entity_id: str, start_date: str, end_date: str) -> pd.Series:
        """计算指标值
        
        Args:
            indicator_name: 指标名称
            entity_id: 实体ID
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            pd.Series: 计算结果
        """
        # 获取指标定义
        indicator_def = self.get_indicator(indicator_name)
        if not indicator_def:
            raise ValueError(f"未找到指标定义: {indicator_name}")
        
        # 获取数据
        data = self._fetch_data(indicator_def, entity_id, start_date, end_date)
        
        # 计算指标
        formula = indicator_def['calculation']
        result = self.calculation_engine.calculate(formula, data)
        
        # 应用后处理
        if 'post_processing' in indicator_def:
            result = self._apply_post_processing(result, indicator_def['post_processing'])
        
        return result
    
    def _fetch_data(self, indicator_def: Dict, entity_id: str, start_date: str, end_date: str) -> Dict[str, pd.Series]:
        """获取指标计算所需的数据
        
        Args:
            indicator_def: 指标定义
            entity_id: 实体ID
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            Dict[str, pd.Series]: 数据字典
        """
        data = {}
        
        # 获取数据源配置
        data_sources = indicator_def.get('data_sources', [])
        
        for source in data_sources:
            table_name = source['table']
            columns = source['columns']
            id_column = source.get('id_column', '股票代码')  # 默认ID列
            date_column = source.get('date_column', '日期')  # 默认日期列
            
            # 构建查询条件
            conditions = {id_column: entity_id}
            
            # 添加额外条件
            if 'conditions' in source:
                conditions.update(source['conditions'])
            
            # 查询数据
            try:
                df = self.reader.read_historical_data(
                    table_name=table_name,
                    conditions=conditions,
                    start_date=start_date,
                    end_date=end_date
                )
                
                if df.empty:
                    logger.warning(f"未找到数据: {table_name}, {entity_id}")
                    continue
                
                # 设置日期索引
                if date_column in df.columns:
                    df = df.set_index(date_column)
                
                # 添加列到数据字典
                for column in columns:
                    if column in df.columns:
                        # 使用别名（如果有）
                        alias = source.get('aliases', {}).get(column, column)
                        data[alias] = df[column]
                    else:
                        logger.warning(f"列不存在: {column} in {table_name}")
                        # 创建空Series
                        data[column] = pd.Series(dtype=float, index=df.index if not df.empty else [])
                
            except Exception as e:
                logger.error(f"获取数据失败: {table_name}, {entity_id}, 错误: {e}")
                # 创建空数据
                for column in columns:
                    data[column] = pd.Series(dtype=float)
        
        return data
    
    def _apply_post_processing(self, result: pd.Series, post_processing: Dict) -> pd.Series:
        """应用后处理
        
        Args:
            result: 计算结果
            post_processing: 后处理配置
            
        Returns:
            pd.Series: 处理后的结果
        """
        # 数据类型转换
        if 'dtype' in post_processing:
            dtype = post_processing['dtype']
            if dtype == 'int':
                result = result.astype(int)
            elif dtype == 'bool':
                result = result.astype(bool)
            elif dtype == 'float':
                result = result.astype(float)
        
        # 填充缺失值
        if 'fill_na' in post_processing:
            fill_value = post_processing['fill_na']
            result = result.fillna(fill_value)
        
        # 数值范围限制
        if 'clip' in post_processing:
            clip_config = post_processing['clip']
            min_val = clip_config.get('min')
            max_val = clip_config.get('max')
            result = result.clip(lower=min_val, upper=max_val)
        
        # 四舍五入
        if 'round' in post_processing:
            decimals = post_processing['round']
            result = result.round(decimals)
        
        return result
    
    def reload_indicators(self):
        """重新加载所有指标定义"""
        self.indicators = self._load_all_indicators()
        logger.info(f"重新加载了 {len(self.indicators)} 个指标定义")
    
    def validate_indicator(self, indicator_name: str) -> Dict[str, Any]:
        """验证指标定义
        
        Args:
            indicator_name: 指标名称
            
        Returns:
            Dict[str, Any]: 验证结果
        """
        indicator_def = self.get_indicator(indicator_name)
        if not indicator_def:
            return {'valid': False, 'errors': [f'指标不存在: {indicator_name}']}
        
        errors = []
        warnings = []
        
        # 检查必需字段
        required_fields = ['name', 'description', 'data_sources', 'calculation', 'output']
        for field in required_fields:
            if field not in indicator_def:
                errors.append(f'缺少必需字段: {field}')
        
        # 检查数据源配置
        if 'data_sources' in indicator_def:
            for i, source in enumerate(indicator_def['data_sources']):
                if 'table' not in source:
                    errors.append(f'数据源 {i} 缺少table字段')
                if 'columns' not in source:
                    errors.append(f'数据源 {i} 缺少columns字段')
        
        # 检查输出配置
        if 'output' in indicator_def:
            output_config = indicator_def['output']
            if 'table' not in output_config:
                errors.append('输出配置缺少table字段')
            if 'column' not in output_config:
                errors.append('输出配置缺少column字段')
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }


# 单例模式：确保全局只有一个文件指标加载器实例
_file_indicator_loader_instance = None

def get_file_indicator_loader() -> FileIndicatorLoader:
    """获取文件指标加载器单例实例
    
    Returns:
        FileIndicatorLoader: 文件指标加载器实例
    """
    global _file_indicator_loader_instance
    if _file_indicator_loader_instance is None:
        _file_indicator_loader_instance = FileIndicatorLoader()
    return _file_indicator_loader_instance


if __name__ == "__main__":
    # 测试代码
    loader = get_file_indicator_loader()
    
    # 打印所有已加载的指标
    print(f"已加载 {len(loader.indicators)} 个指标:")
    for name, definition in loader.indicators.items():
        print(f"  - {name} ({definition.get('entity_type', 'unknown')})")
    
    # 验证指标定义
    for name in loader.indicators.keys():
        validation = loader.validate_indicator(name)
        if not validation['valid']:
            print(f"指标 {name} 验证失败: {validation['errors']}")