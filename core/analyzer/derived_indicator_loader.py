# -*- coding: utf-8 -*-

"""
衍生指标加载器模块

负责从配置文件加载衍生指标定义，并提供动态注册和获取指标计算函数的功能。
这种设计使得系统可以轻松添加新的衍生指标，而无需修改核心代码。
"""

import os
import sys
import yaml
import logging
import importlib
import inspect
from pathlib import Path
from typing import Dict, List, Callable, Union, Optional, Any, Tuple

# 添加项目根目录到系统路径
project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DerivedIndicatorLoader:
    """衍生指标加载器
    
    负责从配置文件加载衍生指标定义，并提供动态注册和获取指标计算函数的功能。
    """

    def __init__(self, config_path=None):
        """初始化加载器
        
        Args:
            config_path (str, optional): 配置文件路径，如果为None则使用默认路径
        """
        if config_path is None:
            self.config_path = os.path.join(project_root, 'config', 'derived_indicators.yaml')
        else:
            self.config_path = config_path
            
        # 加载配置
        self.config = self._load_config()
        
        # 初始化指标注册表
        self.indicator_registry = {
            'stock': {},
            'industry': {},
            'index': {}
        }
        
        # 加载内置指标计算函数
        self._register_builtin_indicators()
    
    def _load_config(self) -> Dict:
        """加载配置文件
        
        Returns:
            Dict: 配置字典
        """
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"成功加载衍生指标配置: {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"加载衍生指标配置失败: {e}")
            # 返回空配置
            return {
                'common_indicators': {},
                'stock_indicators': {},
                'industry_indicators': {},
                'index_indicators': {},
                'tables': {}
            }
    
    def _register_builtin_indicators(self):
        """注册内置指标计算函数"""
        from core.analyzer.derived_indicators import DerivedIndicatorCalculator
        
        # 获取DerivedIndicatorCalculator类中的所有静态方法
        for name, method in inspect.getmembers(DerivedIndicatorCalculator, predicate=inspect.isfunction):
            # 只注册以calculate_开头的方法
            if name.startswith('calculate_'):
                # 提取指标名称（去掉calculate_前缀）
                indicator_name = name[len('calculate_'):]
                
                # 注册到所有实体类型
                for entity_type in self.indicator_registry.keys():
                    self.register_indicator(entity_type, indicator_name, method)
    
    def register_indicator(self, entity_type: str, indicator_name: str, func: Callable):
        """注册指标计算函数
        
        Args:
            entity_type (str): 实体类型 ('stock', 'industry', 'index')
            indicator_name (str): 指标名称
            func (Callable): 指标计算函数
        """
        if entity_type not in self.indicator_registry:
            logger.warning(f"未知的实体类型: {entity_type}，无法注册指标")
            return
        
        self.indicator_registry[entity_type][indicator_name] = func
        logger.debug(f"已注册{entity_type}指标: {indicator_name}")
    
    def get_indicator(self, entity_type: str, indicator_name: str) -> Optional[Callable]:
        """获取指标计算函数
        
        Args:
            entity_type (str): 实体类型 ('stock', 'industry', 'index')
            indicator_name (str): 指标名称
            
        Returns:
            Optional[Callable]: 指标计算函数，如果不存在则返回None
        """
        if entity_type not in self.indicator_registry:
            logger.warning(f"未知的实体类型: {entity_type}")
            return None
        
        return self.indicator_registry[entity_type].get(indicator_name)
    
    def get_all_indicators(self, entity_type: str) -> Dict[str, Callable]:
        """获取指定实体类型的所有指标计算函数
        
        Args:
            entity_type (str): 实体类型 ('stock', 'industry', 'index')
            
        Returns:
            Dict[str, Callable]: 指标名称到计算函数的映射
        """
        if entity_type not in self.indicator_registry:
            logger.warning(f"未知的实体类型: {entity_type}")
            return {}
        
        return self.indicator_registry[entity_type].copy()
    
    def get_indicator_config(self, indicator_name: str, entity_type: str = None) -> Optional[Dict]:
        """获取指标配置
        
        Args:
            indicator_name (str): 指标名称
            entity_type (str, optional): 实体类型，如果为None则在所有类型中查找
            
        Returns:
            Optional[Dict]: 指标配置，如果不存在则返回None
        """
        # 首先在通用指标中查找
        if 'common_indicators' in self.config and indicator_name in self.config['common_indicators']:
            return self.config['common_indicators'][indicator_name]
        
        # 如果指定了实体类型，则在对应的指标中查找
        if entity_type is not None:
            config_key = f"{entity_type}_indicators"
            if config_key in self.config and indicator_name in self.config[config_key]:
                return self.config[config_key][indicator_name]
        else:
            # 在所有实体类型中查找
            for entity_type in ['stock', 'industry', 'index']:
                config_key = f"{entity_type}_indicators"
                if config_key in self.config and indicator_name in self.config[config_key]:
                    return self.config[config_key][indicator_name]
        
        return None
    
    def get_table_config(self, table_name: str) -> Optional[Dict]:
        """获取表配置
        
        Args:
            table_name (str): 表名
            
        Returns:
            Optional[Dict]: 表配置，如果不存在则返回None
        """
        if 'tables' in self.config and table_name in self.config['tables']:
            return self.config['tables'][table_name]
        
        return None
    
    def get_entity_table_name(self, entity_type: str) -> Optional[str]:
        """获取实体类型对应的衍生指标表名
        
        Args:
            entity_type (str): 实体类型 ('stock', 'industry', 'index')
            
        Returns:
            Optional[str]: 表名，如果不存在则返回None
        """
        table_map = {
            'stock': '股票衍生指标',
            'industry': '行业衍生指标',
            'index': '指数衍生指标'
        }
        
        return table_map.get(entity_type)
    
    def get_entity_id_column(self, entity_type: str) -> Optional[str]:
        """获取实体类型对应的ID列名
        
        Args:
            entity_type (str): 实体类型 ('stock', 'industry', 'index')
            
        Returns:
            Optional[str]: ID列名，如果不存在则返回None
        """
        id_column_map = {
            'stock': '股票代码',
            'industry': '行业名称',
            'index': '指数代码'
        }
        
        return id_column_map.get(entity_type)
    
    def get_entity_history_table(self, entity_type: str) -> Optional[str]:
        """获取实体类型对应的历史数据表名
        
        Args:
            entity_type (str): 实体类型 ('stock', 'industry', 'index')
            
        Returns:
            Optional[str]: 表名，如果不存在则返回None
        """
        table_map = {
            'stock': '股票历史行情_后复权',
            'industry': '行业历史行情',
            'index': '指数历史行情'
        }
        
        return table_map.get(entity_type)
    
    def register_external_indicators(self, module_path: str):
        """从外部模块注册指标计算函数
        
        Args:
            module_path (str): 模块路径，例如 'custom_indicators.stock_indicators'
        """
        try:
            # 动态导入模块
            module = importlib.import_module(module_path)
            
            # 获取模块中的所有函数
            for name, func in inspect.getmembers(module, predicate=inspect.isfunction):
                # 只注册以calculate_开头的函数
                if name.startswith('calculate_'):
                    # 提取指标名称（去掉calculate_前缀）
                    indicator_name = name[len('calculate_'):]
                    
                    # 获取函数的元数据
                    metadata = getattr(func, '__indicator_metadata__', {})
                    entity_types = metadata.get('entity_types', ['stock', 'industry', 'index'])
                    
                    # 注册到指定的实体类型
                    for entity_type in entity_types:
                        if entity_type in self.indicator_registry:
                            self.register_indicator(entity_type, indicator_name, func)
            
            logger.info(f"已从模块 {module_path} 注册外部指标")
        except Exception as e:
            logger.error(f"从模块 {module_path} 注册外部指标失败: {e}")


# 装饰器：用于标记指标计算函数的元数据
def indicator(name=None, description=None, entity_types=None, required_columns=None):
    """指标计算函数装饰器
    
    用于标记指标计算函数的元数据，便于动态注册和管理。
    
    Args:
        name (str, optional): 指标名称，如果为None则使用函数名（去掉calculate_前缀）
        description (str, optional): 指标描述
        entity_types (list, optional): 适用的实体类型列表，如果为None则适用于所有类型
        required_columns (list, optional): 计算所需的数据列
    """
    def decorator(func):
        # 设置函数的元数据
        func.__indicator_metadata__ = {
            'name': name or func.__name__[len('calculate_'):] if func.__name__.startswith('calculate_') else func.__name__,
            'description': description or func.__doc__,
            'entity_types': entity_types or ['stock', 'industry', 'index'],
            'required_columns': required_columns or []
        }
        return func
    return decorator


# 单例模式：确保全局只有一个指标加载器实例
_indicator_loader_instance = None

def get_indicator_loader() -> DerivedIndicatorLoader:
    """获取指标加载器单例实例
    
    Returns:
        DerivedIndicatorLoader: 指标加载器实例
    """
    global _indicator_loader_instance
    if _indicator_loader_instance is None:
        _indicator_loader_instance = DerivedIndicatorLoader()
    return _indicator_loader_instance


# 如果直接运行此脚本，则执行示例代码
if __name__ == "__main__":
    # 获取指标加载器实例
    loader = get_indicator_loader()
    
    # 打印所有已注册的指标
    for entity_type in ['stock', 'industry', 'index']:
        indicators = loader.get_all_indicators(entity_type)
        print(f"{entity_type}指标数量: {len(indicators)}")
        for name in indicators.keys():
            print(f"  - {name}")
    
    # 打印指标配置
    print("\n指标配置示例:")
    print(loader.get_indicator_config('golden_cross'))
    
    # 打印表配置
    print("\n表配置示例:")
    print(loader.get_table_config('股票衍生指标'))