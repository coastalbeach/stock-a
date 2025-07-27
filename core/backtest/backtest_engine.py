# -*- coding: utf-8 -*-
"""
通用回测引擎

基于backtrader框架的通用回测引擎，支持多种策略类型和数据源
"""

import os
import sys
import pandas as pd
import numpy as np
import backtrader as bt
from datetime import datetime, date
from typing import Dict, List, Any, Optional, Union, Tuple, Type
import logging

# 添加项目根目录到系统路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from core.strategy.strategy_base import StrategyBase
from core.strategy.strategy_manager import StrategyManager
from db import EnhancedPostgreSQLManager
from utils.logger import LoggerManager


class AKShareDataFeed(bt.feeds.PandasData):
    """
    AKShare数据源适配器
    
    将从数据库或AKShare获取的数据转换为Backtrader可用的格式
    """
    params = (
        ('datetime', None),  # 使用索引作为日期
        ('open', '开盘'),
        ('high', '最高'),
        ('low', '最低'),
        ('close', '收盘'),
        ('volume', '成交量'),
        ('openinterest', None),  # A股没有未平仓量
    )


class StrategyAdapter(bt.Strategy):
    """
    策略适配器
    
    将项目中的策略适配到Backtrader框架
    """
    params = (
        ('strategy_instance', None),  # 策略实例
        ('stock_code', ''),  # 股票代码
        ('commission', 0.001),  # 手续费率
        ('slippage', 0.001),  # 滑点
    )
    
    def __init__(self):
        """
        初始化策略适配器
        """
        self.logger = logging.getLogger(f"backtest.{self.p.strategy_instance.name}")
        self.strategy = self.p.strategy_instance
        
        # 交易记录
        self.trades = []
        self.orders = []
        
        # 订单状态跟踪
        self.order = None
        
        # 数据缓存
        self.data_cache = []
        
        # 信号缓存
        self.signal_cache = {}
        
        self.logger.info(f"策略适配器初始化完成: {self.strategy.name}")
    
    def next(self):
        """
        策略核心逻辑，每个bar执行一次
        """
        # 如果有未完成的订单，不执行新的交易
        if self.order:
            return
        
        # 准备数据
        current_data = self._prepare_current_data()
        
        # 获取或生成信号
        signal = self._get_signal(current_data)
        
        if signal is None:
            return
        
        # 执行交易
        self._execute_trade(signal)
    
    def _prepare_current_data(self) -> pd.DataFrame:
        """
        准备当前数据
        
        Returns:
            pd.DataFrame: 当前数据
        """
        current_bar = {
            '日期': self.data.datetime.date(),
            '股票代码': self.p.stock_code,
            '开盘': self.data.open[0],
            '最高': self.data.high[0],
            '最低': self.data.low[0],
            '收盘': self.data.close[0],
            '成交量': self.data.volume[0],
        }
        
        # 添加到缓存
        self.data_cache.append(current_bar)
        
        # 保持最近60天的数据（可配置）
        if len(self.data_cache) > 60:
            self.data_cache.pop(0)
        
        return pd.DataFrame(self.data_cache)
    
    def _get_signal(self, data: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        获取交易信号
        
        Args:
            data (pd.DataFrame): 历史数据
            
        Returns:
            Optional[Dict[str, Any]]: 交易信号
        """
        current_date = self.data.datetime.date()
        
        # 检查缓存
        if current_date in self.signal_cache:
            return self.signal_cache[current_date]
        
        try:
            # 生成信号
            signals = self.strategy.generate_signals(data)
            
            if signals.empty:
                self.signal_cache[current_date] = None
                return None
            
            # 获取当前日期的信号
            current_signals = signals[signals['日期'] == current_date]
            
            if current_signals.empty:
                self.signal_cache[current_date] = None
                return None
            
            # 取第一个信号
            signal_row = current_signals.iloc[0]
            signal = {
                '信号类型': signal_row.get('信号类型', '持仓'),
                '信号价格': signal_row.get('信号价格', self.data.close[0]),
                '信号强度': signal_row.get('信号强度', 1.0),
                '备注': signal_row.get('备注', '')
            }
            
            self.signal_cache[current_date] = signal
            return signal
            
        except Exception as e:
            self.logger.error(f"生成信号时发生错误: {e}")
            self.signal_cache[current_date] = None
            return None
    
    def _execute_trade(self, signal: Dict[str, Any]):
        """
        执行交易
        
        Args:
            signal (Dict[str, Any]): 交易信号
        """
        signal_type = signal.get('信号类型', '持仓')
        signal_price = signal.get('信号价格', self.data.close[0])
        
        if signal_type == '买入':
            if not self.position:
                # 计算买入数量（使用可用资金的95%）
                size = int((self.broker.getcash() * 0.95) / signal_price / 100) * 100  # A股最小交易单位100股
                if size > 0:
                    self.order = self.buy(size=size)
                    self.logger.info(f"买入信号: 价格={signal_price:.2f}, 数量={size}")
        
        elif signal_type == '卖出':
            if self.position:
                self.order = self.sell(size=self.position.size)
                self.logger.info(f"卖出信号: 价格={signal_price:.2f}, 数量={self.position.size}")
    
    def notify_order(self, order):
        """
        订单状态通知
        
        Args:
            order: 订单对象
        """
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                self.logger.info(f"买入执行: 价格={order.executed.price:.2f}, 数量={order.executed.size}, 手续费={order.executed.comm:.2f}")
            else:
                self.logger.info(f"卖出执行: 价格={order.executed.price:.2f}, 数量={order.executed.size}, 手续费={order.executed.comm:.2f}")
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.logger.warning(f"订单失败: {order.status}")
        
        # 记录订单
        self.orders.append({
            '日期': self.data.datetime.date(),
            '类型': 'BUY' if order.isbuy() else 'SELL',
            '状态': order.getstatusname(),
            '价格': order.executed.price if order.status == order.Completed else 0,
            '数量': order.executed.size if order.status == order.Completed else 0,
            '手续费': order.executed.comm if order.status == order.Completed else 0,
        })
        
        self.order = None
    
    def notify_trade(self, trade):
        """
        交易完成通知
        
        Args:
            trade: 交易对象
        """
        if not trade.isclosed:
            return
        
        self.logger.info(f"交易完成: 盈亏={trade.pnl:.2f}, 净盈亏={trade.pnlcomm:.2f}")
        
        # 记录交易
        self.trades.append({
            '开仓日期': trade.dtopen,
            '平仓日期': trade.dtclose,
            '开仓价格': trade.price,
            '平仓价格': trade.price,
            '数量': trade.size,
            '盈亏': trade.pnl,
            '净盈亏': trade.pnlcomm,
            '手续费': trade.commission,
        })


class BacktestEngine:
    """
    通用回测引擎
    
    提供完整的回测功能，包括数据加载、策略执行、结果分析等
    """
    
    def __init__(self, initial_cash: float = 100000.0):
        """
        初始化回测引擎
        
        Args:
            initial_cash (float): 初始资金
        """
        self.initial_cash = initial_cash
        self.cerebro = bt.Cerebro()
        self.db_manager = EnhancedPostgreSQLManager()
        self.strategy_manager = StrategyManager()
        
        # 获取日志记录器
        logger_manager = LoggerManager()
        self.logger = logger_manager.get_logger('backtest_engine')
        
        # 设置初始资金
        self.cerebro.broker.setcash(initial_cash)
        
        # 设置手续费（万分之三，双边收取）
        self.cerebro.broker.setcommission(commission=0.0003)
        
        self.logger.info(f"回测引擎初始化完成，初始资金: {initial_cash}")
    
    def add_data(self, stock_code: str, start_date: str, end_date: str, 
                 data_source: str = 'database') -> bool:
        """
        添加数据源
        
        Args:
            stock_code (str): 股票代码
            start_date (str): 开始日期
            end_date (str): 结束日期
            data_source (str): 数据源类型，'database' 或 'akshare'
            
        Returns:
            bool: 是否成功添加数据
        """
        try:
            if data_source == 'database':
                data = self._load_data_from_database(stock_code, start_date, end_date)
            else:
                data = self._load_data_from_akshare(stock_code, start_date, end_date)
            
            if data.empty:
                self.logger.error(f"未获取到数据: {stock_code}")
                return False
            
            # 创建数据源
            data_feed = AKShareDataFeed(dataname=data)
            self.cerebro.adddata(data_feed, name=stock_code)
            
            self.logger.info(f"数据添加成功: {stock_code}, 数据量: {len(data)}")
            return True
            
        except Exception as e:
            self.logger.error(f"添加数据时发生错误: {e}")
            return False
    
    def _load_data_from_database(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        从数据库加载数据
        
        Args:
            stock_code (str): 股票代码
            start_date (str): 开始日期
            end_date (str): 结束日期
            
        Returns:
            pd.DataFrame: 股票数据
        """
        data = self.db_manager.read_stock_quotes(stock_code, start_date, end_date, limit=None)
        
        if not data.empty:
            # 设置日期为索引
            data['日期'] = pd.to_datetime(data['日期'])
            data.set_index('日期', inplace=True)
            data.sort_index(inplace=True)
        
        return data
    
    def _load_data_from_akshare(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        从AKShare加载数据
        
        Args:
            stock_code (str): 股票代码
            start_date (str): 开始日期
            end_date (str): 结束日期
            
        Returns:
            pd.DataFrame: 股票数据
        """
        try:
            import akshare as ak
            
            # 获取股票历史数据
            data = ak.stock_zh_a_hist(symbol=stock_code, period="daily", 
                                    start_date=start_date.replace('-', ''), 
                                    end_date=end_date.replace('-', ''), 
                                    adjust="qfq")
            
            if not data.empty:
                # 重命名列
                data.rename(columns={
                    '日期': '日期',
                    '开盘': '开盘',
                    '收盘': '收盘',
                    '最高': '最高',
                    '最低': '最低',
                    '成交量': '成交量'
                }, inplace=True)
                
                # 设置日期为索引
                data['日期'] = pd.to_datetime(data['日期'])
                data.set_index('日期', inplace=True)
                data.sort_index(inplace=True)
            
            return data
            
        except Exception as e:
            self.logger.error(f"从AKShare获取数据失败: {e}")
            return pd.DataFrame()
    
    def add_strategy(self, strategy_name: str, stock_code: str, **kwargs) -> bool:
        """
        添加策略
        
        Args:
            strategy_name (str): 策略名称
            stock_code (str): 股票代码
            **kwargs: 策略参数
            
        Returns:
            bool: 是否成功添加策略
        """
        try:
            # 获取策略实例
            strategy_instance = self.strategy_manager.get_strategy(strategy_name)
            
            if strategy_instance is None:
                self.logger.error(f"策略不存在: {strategy_name}")
                return False
            
            # 添加策略到cerebro
            self.cerebro.addstrategy(
                StrategyAdapter,
                strategy_instance=strategy_instance,
                stock_code=stock_code,
                **kwargs
            )
            
            self.logger.info(f"策略添加成功: {strategy_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"添加策略时发生错误: {e}")
            return False
    
    def run(self) -> Dict[str, Any]:
        """
        运行回测
        
        Returns:
            Dict[str, Any]: 回测结果
        """
        try:
            self.logger.info("开始回测...")
            
            # 添加分析器
            self.cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
            self.cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
            self.cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
            self.cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
            
            # 运行回测
            results = self.cerebro.run()
            
            # 获取结果
            strategy_result = results[0]
            
            # 计算绩效指标
            final_value = self.cerebro.broker.getvalue()
            total_return = (final_value - self.initial_cash) / self.initial_cash * 100
            
            # 提取分析器结果
            sharpe_ratio = strategy_result.analyzers.sharpe.get_analysis().get('sharperatio', 0)
            drawdown = strategy_result.analyzers.drawdown.get_analysis()
            returns = strategy_result.analyzers.returns.get_analysis()
            trades = strategy_result.analyzers.trades.get_analysis()
            
            result = {
                'initial_cash': self.initial_cash,
                'final_value': final_value,
                'total_return': total_return,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': drawdown.get('max', {}).get('drawdown', 0),
                'annual_return': returns.get('rnorm100', 0),
                'total_trades': trades.get('total', {}).get('total', 0),
                'winning_trades': trades.get('won', {}).get('total', 0),
                'losing_trades': trades.get('lost', {}).get('total', 0),
                'win_rate': trades.get('won', {}).get('total', 0) / max(trades.get('total', {}).get('total', 1), 1) * 100,
                'orders': strategy_result.orders if hasattr(strategy_result, 'orders') else [],
                'trades_detail': strategy_result.trades if hasattr(strategy_result, 'trades') else [],
            }
            
            self.logger.info(f"回测完成，总收益率: {total_return:.2f}%")
            return result
            
        except Exception as e:
            self.logger.error(f"回测运行时发生错误: {e}")
            return {}
    
    def plot(self, **kwargs):
        """
        绘制回测结果
        
        Args:
            **kwargs: 绘图参数
        """
        try:
            self.cerebro.plot(**kwargs)
        except Exception as e:
            self.logger.error(f"绘图时发生错误: {e}")