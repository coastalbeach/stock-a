#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
策略管理器模块

负责策略的发现、加载、注册和执行，以及交易信号的保存。
"""

from .json_strategy_loader import JSONStrategyLoader, JSONStrategy

import os
import importlib
import inspect
import pandas as pd
from pathlib import Path
from typing import List, Dict, Type, Optional, Any
from datetime import date, datetime

# 添加项目根目录到系统路径，以便导入其他模块
project_root = str(Path(__file__).resolve().parent.parent.parent) # core/strategy/strategy_manager.py -> stock-a
if project_root not in os.sys.path:
    os.sys.path.append(project_root)

from core.strategy.strategy_base import StrategyBase
# 假设有数据管理模块，用于获取数据和保存信号
from db import PostgreSQLManager, RedisManager
import json
import hashlib

class StrategyManager:
    """策略管理器"""

    def __init__(self, strategies_dir: Optional[str] = None, json_strategies_dir: Optional[str] = None):
        """
        初始化策略管理器

        Args:
            strategies_dir (Optional[str]): 存放策略文件的目录路径。如果为None，则默认为当前文件所在目录。
            json_strategies_dir (Optional[str]): 存放JSON策略文件的目录路径。如果为None，则默认为当前文件所在目录的strategies子目录。
        """
        self.strategies: Dict[str, Type[StrategyBase]] = {}
        self.loaded_strategies: Dict[str, StrategyBase] = {}
        self.pg_manager = PostgreSQLManager()
        self.redis_manager = RedisManager()
        self._create_signal_table_if_not_exists()

        if strategies_dir is None:
            self.strategies_dir = Path(__file__).parent
        else:
            self.strategies_dir = Path(strategies_dir)
        
        # 初始化JSON策略加载器
        self.json_strategy_loader = JSONStrategyLoader(json_strategies_dir)
        
        # 发现并注册Python策略
        self._discover_strategies()
        
        # 发现并注册JSON策略
        self._discover_json_strategies()

    def _discover_strategies(self):
        """自动发现并注册Python策略"""
        for filepath in self.strategies_dir.glob('*.py'):
            if filepath.name == '__init__.py' or filepath.name == Path(__file__).name or filepath.name == 'strategy_base.py' or filepath.name == 'json_strategy_loader.py':
                continue
            
            module_name = f"core.strategy.{filepath.stem}" # 需要根据实际项目结构调整
            try:
                module = importlib.import_module(module_name)
                for name, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and issubclass(obj, StrategyBase) and obj is not StrategyBase and obj is not JSONStrategy:
                        self.register_strategy(obj.name if hasattr(obj, 'name') and obj.name else name, obj)
            except ImportError as e:
                print(f"导入策略模块 {module_name} 失败: {e}")
            except Exception as e:
                print(f"加载策略模块 {module_name} 时发生错误: {e}")
    
    def _discover_json_strategies(self):
        """自动发现并注册JSON策略"""
        json_strategies = self.json_strategy_loader.discover_strategies()
        for strategy_name, strategy_info in json_strategies.items():
            try:
                # 创建一个工厂函数，用于创建JSONStrategy实例
                def create_json_strategy(name=strategy_name, strategy_def=strategy_info['definition'], file_path=strategy_info['file_path']):
                    return self.json_strategy_loader.create_strategy_from_dict(strategy_def, file_path)
                
                # 注册策略工厂函数
                self.register_strategy(strategy_name, create_json_strategy)
                print(f"JSON策略 '{strategy_name}' 已注册。")
            except Exception as e:
                print(f"注册JSON策略 '{strategy_name}' 时发生错误: {e}")

    def register_strategy(self, name: str, strategy_class_or_factory: Any):
        """
        注册策略

        Args:
            name (str): 策略名称
            strategy_class_or_factory (Any): 策略类或工厂函数
        """
        if name in self.strategies:
            print(f"警告: 策略 '{name}' 已注册，将被覆盖。")
        self.strategies[name] = strategy_class_or_factory
        print(f"策略 '{name}' 已注册。")

    def load_strategy(self, name: str, **kwargs) -> Optional[StrategyBase]:
        """
        加载并实例化一个策略

        Args:
            name (str): 要加载的策略名称
            **kwargs: 传递给策略构造函数的参数

        Returns:
            Optional[StrategyBase]: 实例化的策略对象，如果策略不存在则返回None
        """
        if name not in self.strategies:
            print(f"错误: 策略 '{name}' 未注册。")
            return None
        
        if name not in self.loaded_strategies:
            try:
                strategy_class_or_factory = self.strategies[name]
                
                # 检查是否为工厂函数（用于JSON策略）
                if callable(strategy_class_or_factory) and not inspect.isclass(strategy_class_or_factory):
                    strategy_instance = strategy_class_or_factory()
                    if kwargs:
                        # 对于JSONStrategy，使用set_parameters方法设置参数
                        if isinstance(strategy_instance, JSONStrategy):
                            strategy_instance.set_parameters(kwargs)
                        else:
                            # 对于其他策略，可能需要其他方式设置参数
                            pass
                else:
                    # 对于Python类策略，直接实例化
                    strategy_instance = strategy_class_or_factory(name=name, **kwargs)
                
                self.loaded_strategies[name] = strategy_instance
                print(f"策略 '{name}' 已加载。")
            except Exception as e:
                print(f"加载策略 '{name}' 失败: {e}")
                return None
        return self.loaded_strategies[name]

    def get_available_strategies(self) -> List[str]:
        """获取所有已注册的策略名称"""
        return list(self.strategies.keys())

    def run_strategy(self, strategy_name: str, data: pd.DataFrame, 
                        save_signals: bool = True, 
                        use_cached_signals: bool = True, 
                        **kwargs) -> Optional[pd.DataFrame]:
        """
        运行指定策略并生成交易信号，或从缓存/数据库加载已有信号。

        Args:
            strategy_name (str): 策略名称。
            data (pd.DataFrame): 输入数据，用于生成信号（如果未从缓存加载）。
            save_signals (bool, optional): 是否保存新生成的信号。Defaults to True。
            use_cached_signals (bool, optional): 是否尝试从缓存/数据库加载信号。Defaults to True。
            **kwargs: 传递给策略的额外参数，也用于构建缓存键和参数哈希。

        Returns:
            Optional[pd.DataFrame]: 包含交易信号的DataFrame，如果策略不存在或运行失败则返回None。
        """
        # 提取策略参数，用于追踪参数变化和缓存查询
        # 从kwargs中移除内部控制参数，剩下的作为策略的实际参数
        internal_params = ['save_signals', 'use_cached_signals']
        strategy_params = {k: v for k, v in kwargs.items() if k not in internal_params and not k.startswith('_')}

        if use_cached_signals:
            print(f"尝试从缓存/数据库加载策略 '{strategy_name}' (参数: {strategy_params}) 的信号...")
            # 假设我们需要特定日期范围或股票的信号，这里简化为获取所有相关信号
            # 在实际应用中，可能需要从 data DataFrame 推断日期范围和股票代码
            # 或者将 date_range 和 stock_codes 作为参数传递给 run_strategy
            cached_signals_df = self.get_signals(strategy_name, strategy_params)
            if cached_signals_df is not None and not cached_signals_df.empty:
                print(f"成功从缓存/数据库加载 {len(cached_signals_df)} 条策略 '{strategy_name}' 的信号。")
                # 将从数据库加载的列名转换回策略期望的列名
                db_to_strategy_column_mapping = {
                    'signal_date': '日期',
                    'stock_code': '股票代码',
                    'signal_type': '信号类型',
                    'signal_price': '信号价格',
                    'signal_strength': '信号强度',
                    'remarks': '备注'
                }
                cached_signals_df.rename(columns=db_to_strategy_column_mapping, inplace=True)
                return cached_signals_df
            else:
                print(f"缓存/数据库中未找到策略 '{strategy_name}' (参数: {strategy_params}) 的信号，将重新计算。")

        strategy_instance = self.load_strategy(strategy_name, **strategy_params) # 传递实际的策略参数
        if not strategy_instance:
            return None
        
        try:
            print(f"开始运行策略 '{strategy_name}' (参数: {strategy_params})...")
            signals_df = strategy_instance.generate_signals(data) # data 可能是原始行情数据
            print(f"策略 '{strategy_name}' 运行完成，生成 {len(signals_df) if signals_df is not None else 0} 条信号。")
            
            if save_signals and signals_df is not None and not signals_df.empty:
                self.save_signals(signals_df, strategy_name, strategy_params)
            return signals_df
        except Exception as e:
            print(f"运行策略 '{strategy_name}' (参数: {strategy_params}) 失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_signals(self, strategy_name: str, strategy_params: Dict, 
                    stock_codes: Optional[List[str]] = None, 
                    start_date: Optional[date] = None, 
                    end_date: Optional[date] = None) -> Optional[pd.DataFrame]:
        """
        获取指定策略、参数、股票和日期范围的交易信号。
        首先尝试从Redis缓存获取，如果未命中则从PostgreSQL查询，并将结果缓存到Redis。

        Args:
            strategy_name (str): 策略名称。
            strategy_params (Dict): 策略参数，用于计算参数哈希。
            stock_codes (Optional[List[str]], optional): 股票代码列表。Defaults to None (所有股票).
            start_date (Optional[date], optional): 开始日期。Defaults to None.
            end_date (Optional[date], optional): 结束日期。Defaults to None.

        Returns:
            Optional[pd.DataFrame]: 包含交易信号的DataFrame，如果找不到则返回None。
        """
        params_string = json.dumps(strategy_params, sort_keys=True, ensure_ascii=False)
        params_hash = hashlib.sha256(params_string.encode('utf-8')).hexdigest()

        # 构建缓存键时，包含所有查询参数以确保特异性
        cache_key_parts = [
            f"signals_cache",
            strategy_name,
            params_hash,
            f"stocks_{'_'.join(sorted(stock_codes)) if stock_codes else 'all'}",
            f"start_{start_date.isoformat() if start_date else 'none'}",
            f"end_{end_date.isoformat() if end_date else 'none'}"
        ]
        redis_cache_key = ":".join(cache_key_parts)

        try:
            cached_signals_json = self.redis_manager.get(redis_cache_key)
            if cached_signals_json:
                print(f"从Redis缓存命中: {redis_cache_key}")
                signals_df = pd.read_json(cached_signals_json, orient='table')
                # Pandas to_json(orient='table') stores dtypes. Dates might need parsing if not auto-handled.
                if 'signal_date' in signals_df.columns:
                    signals_df['signal_date'] = pd.to_datetime(signals_df['signal_date']).dt.date
                if 'signal_time' in signals_df.columns and signals_df['signal_time'].notna().any():
                     # Handle potential NaT or None before converting to time
                    signals_df['signal_time'] = pd.to_datetime(signals_df['signal_time'], errors='coerce').dt.time
                return signals_df
        except Exception as e:
            print(f"从Redis获取信号失败: {e}")

        # 如果缓存未命中，从PostgreSQL查询
        query_parts = ["SELECT strategy_name, strategy_params_hash, stock_code, signal_date, signal_time, signal_type, signal_price, signal_strength, remarks, created_at FROM trading_signals"]
        conditions = ["strategy_name = %(strategy_name)s", "strategy_params_hash = %(params_hash)s"]
        query_params = {"strategy_name": strategy_name, "params_hash": params_hash}

        if stock_codes:
            conditions.append("stock_code = ANY(%(stock_codes)s)")
            query_params['stock_codes'] = stock_codes
        if start_date:
            conditions.append("signal_date >= %(start_date)s")
            query_params['start_date'] = start_date
        if end_date:
            conditions.append("signal_date <= %(end_date)s")
            query_params['end_date'] = end_date
        
        if conditions:
            query_parts.append("WHERE " + " AND ".join(conditions))
        
        query_parts.append("ORDER BY signal_date, stock_code, signal_time")
        sql_query = " ".join(query_parts) + ";"

        try:
            signals_df = self.pg_manager.fetch_df(sql_query, query_params)
            if signals_df is not None and not signals_df.empty:
                print(f"从PostgreSQL获取 {len(signals_df)} 条信号。")
                # 将从数据库获取的原始数据（列名与数据库一致）缓存到Redis
                # 注意：这里缓存的是查询结果，不是原始生成时的signals_df
                try:
                    # 使用 orient='table' 来保留更多 schema 信息，包括 dtypes
                    self.redis_manager.set(redis_cache_key, signals_df.to_json(orient='table', date_format='iso'), expire_seconds=3600) # 缓存1小时
                    print(f"信号已缓存到Redis: {redis_cache_key}")
                except Exception as e:
                    print(f"缓存信号到Redis失败: {e}")
                return signals_df
            else:
                print("在PostgreSQL中未找到匹配的信号。")
                return None
        except Exception as e:
            print(f"从PostgreSQL获取信号失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _create_signal_table_if_not_exists(self):
        """创建交易信号表 (如果不存在)"""
        table_name = "trading_signals"
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id SERIAL PRIMARY KEY,
            strategy_name VARCHAR(255) NOT NULL,
            strategy_params_hash VARCHAR(64) NOT NULL, -- SHA256 hash
            stock_code VARCHAR(20) NOT NULL,
            signal_date DATE NOT NULL,
            signal_time TIME,
            signal_type VARCHAR(50) NOT NULL, -- '买入', '卖出', '持仓'
            signal_price NUMERIC(20, 4),
            signal_strength NUMERIC(10, 4),
            remarks TEXT,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (strategy_name, strategy_params_hash, stock_code, signal_date, signal_type) -- 复合唯一键，防止重复信号
        );
        """
        if self.pg_manager.execute(create_table_sql):
            print(f"表 '{table_name}' 已检查/创建。")
        else:
            print(f"检查/创建表 '{table_name}' 失败。")

    def save_signals(self, signals_df: pd.DataFrame, strategy_name: str, params: Dict = None):
        """
        保存策略生成的交易信号到PostgreSQL，并缓存到Redis。

        Args:
            signals_df (pd.DataFrame): 包含交易信号的DataFrame。
                                     预期列: '日期', '股票代码', '信号类型', '信号价格', '信号强度', '备注'。
            strategy_name (str): 策略名称。
            params (Dict, optional): 策略参数，用于追踪参数变化。
        """
        if signals_df.empty:
            print(f"策略 '{strategy_name}' 未生成任何信号，无需保存。")
            return

        table_name = "trading_signals"

        df_to_save = signals_df.copy()
        
        if params:
            params_string = json.dumps(params, sort_keys=True, ensure_ascii=False)
            params_hash = hashlib.sha256(params_string.encode('utf-8')).hexdigest()
        else:
            params_hash = hashlib.sha256("".encode('utf-8')).hexdigest()

        df_to_save['strategy_name'] = strategy_name
        df_to_save['strategy_params_hash'] = params_hash
        
        column_mapping = {
            '日期': 'signal_date',
            '股票代码': 'stock_code',
            '信号类型': 'signal_type',
            '信号价格': 'signal_price',
            '信号强度': 'signal_strength',
            '备注': 'remarks'
        }
        df_to_save.rename(columns=column_mapping, inplace=True)

        required_db_cols = ['strategy_name', 'strategy_params_hash', 'stock_code', 'signal_date', 'signal_type', 
                              'signal_price', 'signal_strength', 'remarks', 'signal_time']
        for col in required_db_cols:
            if col not in df_to_save.columns:
                df_to_save[col] = None
        
        df_to_save['signal_date'] = pd.to_datetime(df_to_save['signal_date']).dt.date
        if 'signal_time' in df_to_save.columns and pd.api.types.is_datetime64_any_dtype(df_to_save['signal_time']):
             df_to_save['signal_time'] = pd.to_datetime(df_to_save['signal_time']).dt.time
        elif 'signal_time' in df_to_save.columns:
            try:
                df_to_save['signal_time'] = pd.to_datetime(df_to_save['signal_time']).dt.time
            except:
                df_to_save['signal_time'] = None

        conflict_cols = ['strategy_name', 'strategy_params_hash', 'stock_code', 'signal_date', 'signal_type']
        update_cols = ['signal_price', 'signal_strength', 'remarks', 'created_at']
        update_cols = [col for col in update_cols if col in df_to_save.columns or col == 'created_at']
        
        try:
            success = self.pg_manager.insert_df(table_name, df_to_save[required_db_cols], 
                                                conflict_columns=conflict_cols, 
                                                update_columns=update_cols)
            if success:
                print(f"策略 '{strategy_name}' 的 {len(df_to_save)} 条信号已成功保存到 PostgreSQL 表 '{table_name}'。")
            else:
                print(f"保存策略 '{strategy_name}' 信号到 PostgreSQL 失败。")
        except Exception as e:
            print(f"保存策略 '{strategy_name}' 信号到 PostgreSQL 时发生错误: {e}")
            import traceback
            traceback.print_exc()
            return # 如果PG保存失败，则不进行Redis缓存

        # 成功保存到PostgreSQL后，缓存到Redis
        # 注意：这里我们缓存的是 `df_to_save`，它已经经过列名映射和类型转换
        # 为了与 get_signals 的缓存键生成逻辑保持一致性（虽然 get_signals 的缓存键更细化），
        # 这里可以考虑一个更通用的缓存键，或者不在此处进行与 get_signals 相同的细粒度缓存，
        # 因为 save_signals 保存的是一个批次的结果。
        # 一个简单的做法是，当信号被保存/更新时，主动失效相关的 get_signals 缓存项，
        # 或者，如果 get_signals 总是查询最新数据，那么这里的缓存主要是为了 run_strategy 内部的优化（如果它也查缓存的话）。
        # 目前的设计是 get_signals 自己管理它的缓存。save_signals 可以考虑清除或更新一个“批次”缓存。
        # 为简单起见，此处不添加Redis缓存逻辑，让 get_signals 按需缓存。
        # 如果需要，可以添加一个简单的“最新信号集”缓存，例如：
        # redis_batch_cache_key = f"signals_batch_cache:{strategy_name}:{params_hash}"
        # try:
        #     self.redis_manager.set(redis_batch_cache_key, df_to_save.to_json(orient='table', date_format='iso'), expire_seconds=3600)
        #     print(f"批次信号已缓存到Redis: {redis_batch_cache_key}")
        # except Exception as e:
        #     print(f"缓存批次信号到Redis失败: {e}")

    def run_all_strategies(self, data_map: Dict[str, pd.DataFrame], **kwargs) -> Dict[str, Optional[pd.DataFrame]]:
        """
        运行所有已加载的策略

        Args:
            data_map (Dict[str, pd.DataFrame]): 一个字典，键是策略名称，值是该策略对应的数据。
                                                如果所有策略使用相同数据，可以传入一个通用数据，并在内部处理。
            **kwargs: 传递给策略加载时的参数

        Returns:
            Dict[str, Optional[pd.DataFrame]]: 字典，键是策略名称，值是生成的信号DataFrame或None
        """
        results = {}
        for strategy_name in self.loaded_strategies.keys():
            if strategy_name not in data_map:
                print(f"警告: 策略 '{strategy_name}' 没有提供对应的数据，跳过执行。")
                results[strategy_name] = None
                continue
            results[strategy_name] = self.run_strategy(strategy_name, data_map[strategy_name], **kwargs)
        return results

# 示例用法
if __name__ == '__main__':
    # 假设在 core/strategy/ 目录下有一个 my_custom_strategy.py 文件，其中定义了一个 MyCustomStrategy 类
    # 1. 创建一个示例策略文件 core/strategy/example_strategy.py
    example_strategy_content = """
from core.strategy.strategy_base import StrategyBase
import pandas as pd

class ExampleStrategy(StrategyBase):
    def __init__(self, name: str, lookback_period: int = 20):
        super().__init__(name)
        self.lookback_period = lookback_period
        print(f'{self.name} initialized with lookback_period={self.lookback_period}')

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        signals = []
        # 简单示例：收盘价高于过去 lookback_period 天的均线则买入
        if '收盘' not in data.columns or '日期' not in data.columns or '股票代码' not in data.columns:
            print("数据缺少必要的列: '收盘', '日期', '股票代码'")
            return pd.DataFrame(columns=['日期', '股票代码', '信号'])
        
        data['均线'] = data['收盘'].rolling(window=self.lookback_period).mean()
        for i in range(len(data)):
            if pd.notna(data['均线'].iloc[i]) and data['收盘'].iloc[i] > data['均线'].iloc[i]:
                signals.append({'日期': data['日期'].iloc[i], '股票代码': data['股票代码'].iloc[i], '信号': '买入'})
            elif pd.notna(data['均线'].iloc[i]) and data['收盘'].iloc[i] < data['均线'].iloc[i]:
                signals.append({'日期': data['日期'].iloc[i], '股票代码': data['股票代码'].iloc[i], '信号': '卖出'})
            else:
                signals.append({'日期': data['日期'].iloc[i], '股票代码': data['股票代码'].iloc[i], '信号': '持仓'})
        return pd.DataFrame(signals)
"""
    example_strategy_file = Path(__file__).parent / "example_strategy.py"
    with open(example_strategy_file, 'w', encoding='utf-8') as f:
        f.write(example_strategy_content)
    print(f"示例策略文件 {example_strategy_file} 已创建。")

    # 2. 初始化策略管理器
    # strategy_manager会自动发现同目录下的策略（除了自己和base）
    manager = StrategyManager()

    # 3. 查看可用策略
    available_strategies = manager.get_available_strategies()
    print(f"可用策略: {available_strategies}")

    if "ExampleStrategy" in available_strategies:
        # 4. 准备示例数据 (实际应用中应从数据源获取)
        sample_data = pd.DataFrame({
            '日期': pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04', '2023-01-05'] * 4),
            '股票代码': ['000001'] * 5 + ['000002'] * 5 + ['000003'] * 5 + ['000004'] * 5, # 模拟多只股票
            '开盘': [10, 10.2, 10.1, 10.5, 10.3] * 4,
            '收盘': [10.2, 10.1, 10.5, 10.3, 10.6] * 4,
            '最高': [10.3, 10.3, 10.6, 10.5, 10.7] * 4,
            '最低': [9.9, 10.0, 10.0, 10.2, 10.2] * 4,
            '成交量': [1000, 1200, 1100, 1500, 1300] * 4
        })
        
        # 确保数据按股票代码和日期排序，这对于很多策略是必要的
        sample_data = sample_data.sort_values(by=['股票代码', '日期']).reset_index(drop=True)

        # 5. 运行单个策略
        # 假设 ExampleStrategy 需要 lookback_period 参数
        signals = manager.run_strategy("ExampleStrategy", sample_data.copy(), lookback_period=3) # 传递参数
        if signals is not None:
            print("\nExampleStrategy 信号:")
            print(signals)
            
            # 6. (可选) 保存信号 - 在 StrategyManager 中实现
            # manager.save_signals(signals, "ExampleStrategy")

    # 清理示例文件
    if example_strategy_file.exists():
        os.remove(example_strategy_file)
        print(f"示例策略文件 {example_strategy_file} 已删除。")