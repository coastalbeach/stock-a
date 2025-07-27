# -*- coding: utf-8 -*-
"""
订单执行处理器

负责处理订单的执行、滑点、手续费计算等
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, date, time
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
import logging
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod

# 添加项目根目录到系统路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from utils.logger import LoggerManager
from core.backtest.portfolio_manager import Order, OrderType, OrderStatus


class ExecutionModel(Enum):
    """执行模型类型"""
    MARKET = "市价执行"
    LIMIT = "限价执行"
    VWAP = "VWAP执行"
    TWAP = "TWAP执行"


class SlippageModel(ABC):
    """滑点模型基类"""
    
    @abstractmethod
    def calculate_slippage(self, order: Order, market_data: Dict[str, Any]) -> float:
        """
        计算滑点
        
        Args:
            order (Order): 订单信息
            market_data (Dict[str, Any]): 市场数据
            
        Returns:
            float: 滑点金额
        """
        pass


class FixedSlippageModel(SlippageModel):
    """固定滑点模型"""
    
    def __init__(self, slippage_rate: float = 0.001):
        """
        初始化固定滑点模型
        
        Args:
            slippage_rate (float): 滑点率
        """
        self.slippage_rate = slippage_rate
    
    def calculate_slippage(self, order: Order, market_data: Dict[str, Any]) -> float:
        """
        计算固定滑点
        
        Args:
            order (Order): 订单信息
            market_data (Dict[str, Any]): 市场数据
            
        Returns:
            float: 滑点金额
        """
        return order.price * order.shares * self.slippage_rate


class VolumeBasedSlippageModel(SlippageModel):
    """基于成交量的滑点模型"""
    
    def __init__(self, base_slippage: float = 0.0005, volume_impact: float = 0.1):
        """
        初始化基于成交量的滑点模型
        
        Args:
            base_slippage (float): 基础滑点率
            volume_impact (float): 成交量影响系数
        """
        self.base_slippage = base_slippage
        self.volume_impact = volume_impact
    
    def calculate_slippage(self, order: Order, market_data: Dict[str, Any]) -> float:
        """
        计算基于成交量的滑点
        
        Args:
            order (Order): 订单信息
            market_data (Dict[str, Any]): 市场数据
            
        Returns:
            float: 滑点金额
        """
        volume = market_data.get('volume', 1000000)  # 默认成交量
        order_volume = order.shares
        
        # 计算订单占成交量的比例
        volume_ratio = order_volume / volume if volume > 0 else 0
        
        # 滑点率随成交量比例增加
        slippage_rate = self.base_slippage + self.volume_impact * volume_ratio
        
        return order.price * order.shares * slippage_rate


class BidAskSlippageModel(SlippageModel):
    """基于买卖价差的滑点模型"""
    
    def __init__(self, spread_factor: float = 0.5):
        """
        初始化基于买卖价差的滑点模型
        
        Args:
            spread_factor (float): 价差影响因子
        """
        self.spread_factor = spread_factor
    
    def calculate_slippage(self, order: Order, market_data: Dict[str, Any]) -> float:
        """
        计算基于买卖价差的滑点
        
        Args:
            order (Order): 订单信息
            market_data (Dict[str, Any]): 市场数据
            
        Returns:
            float: 滑点金额
        """
        bid_price = market_data.get('bid', order.price * 0.999)
        ask_price = market_data.get('ask', order.price * 1.001)
        
        spread = ask_price - bid_price
        slippage_per_share = spread * self.spread_factor
        
        # 买入时向上滑点，卖出时向下滑点
        if order.order_type == OrderType.BUY:
            return slippage_per_share * order.shares
        else:
            return slippage_per_share * order.shares


class CommissionModel(ABC):
    """手续费模型基类"""
    
    @abstractmethod
    def calculate_commission(self, order: Order) -> float:
        """
        计算手续费
        
        Args:
            order (Order): 订单信息
            
        Returns:
            float: 手续费金额
        """
        pass


class FixedCommissionModel(CommissionModel):
    """固定手续费模型"""
    
    def __init__(self, commission_rate: float = 0.0003, min_commission: float = 5.0):
        """
        初始化固定手续费模型
        
        Args:
            commission_rate (float): 手续费率
            min_commission (float): 最低手续费
        """
        self.commission_rate = commission_rate
        self.min_commission = min_commission
    
    def calculate_commission(self, order: Order) -> float:
        """
        计算固定手续费
        
        Args:
            order (Order): 订单信息
            
        Returns:
            float: 手续费金额
        """
        commission = order.price * order.shares * self.commission_rate
        return max(commission, self.min_commission)


class TieredCommissionModel(CommissionModel):
    """分层手续费模型"""
    
    def __init__(self, tiers: List[Tuple[float, float]], min_commission: float = 5.0):
        """
        初始化分层手续费模型
        
        Args:
            tiers (List[Tuple[float, float]]): 分层费率 [(交易额阈值, 费率), ...]
            min_commission (float): 最低手续费
        """
        self.tiers = sorted(tiers, key=lambda x: x[0])  # 按交易额排序
        self.min_commission = min_commission
    
    def calculate_commission(self, order: Order) -> float:
        """
        计算分层手续费
        
        Args:
            order (Order): 订单信息
            
        Returns:
            float: 手续费金额
        """
        trade_value = order.price * order.shares
        
        # 找到对应的费率
        commission_rate = self.tiers[-1][1]  # 默认最高层费率
        for threshold, rate in self.tiers:
            if trade_value <= threshold:
                commission_rate = rate
                break
        
        commission = trade_value * commission_rate
        return max(commission, self.min_commission)


class MarketImpactModel:
    """市场冲击模型"""
    
    def __init__(self, impact_factor: float = 0.1):
        """
        初始化市场冲击模型
        
        Args:
            impact_factor (float): 冲击因子
        """
        self.impact_factor = impact_factor
    
    def calculate_impact(self, order: Order, market_data: Dict[str, Any]) -> float:
        """
        计算市场冲击
        
        Args:
            order (Order): 订单信息
            market_data (Dict[str, Any]): 市场数据
            
        Returns:
            float: 市场冲击价格调整
        """
        volume = market_data.get('volume', 1000000)
        order_volume = order.shares
        
        # 计算订单占成交量的比例
        volume_ratio = order_volume / volume if volume > 0 else 0
        
        # 市场冲击导致的价格变化
        price_impact = order.price * self.impact_factor * np.sqrt(volume_ratio)
        
        # 买入时价格上涨，卖出时价格下跌
        if order.order_type == OrderType.BUY:
            return price_impact
        else:
            return -price_impact


class OrderExecutor:
    """订单执行器"""
    
    def __init__(self, 
                 slippage_model: Optional[SlippageModel] = None,
                 commission_model: Optional[CommissionModel] = None,
                 market_impact_model: Optional[MarketImpactModel] = None,
                 execution_delay: int = 0):
        """
        初始化订单执行器
        
        Args:
            slippage_model (SlippageModel, optional): 滑点模型
            commission_model (CommissionModel, optional): 手续费模型
            market_impact_model (MarketImpactModel, optional): 市场冲击模型
            execution_delay (int): 执行延迟（分钟）
        """
        self.slippage_model = slippage_model or FixedSlippageModel()
        self.commission_model = commission_model or FixedCommissionModel()
        self.market_impact_model = market_impact_model or MarketImpactModel()
        self.execution_delay = execution_delay
        
        # 执行统计
        self.execution_stats = {
            'total_orders': 0,
            'filled_orders': 0,
            'rejected_orders': 0,
            'total_slippage': 0.0,
            'total_commission': 0.0,
            'avg_execution_time': 0.0
        }
        
        # 获取日志记录器
        logger_manager = LoggerManager()
        self.logger = logger_manager.get_logger('order_executor')
        
        self.logger.info("订单执行器初始化完成")
    
    def execute_order(self, order: Order, market_data: Dict[str, Any], 
                     current_time: datetime) -> Tuple[bool, float, Dict[str, float]]:
        """
        执行订单
        
        Args:
            order (Order): 待执行的订单
            market_data (Dict[str, Any]): 市场数据
            current_time (datetime): 当前时间
            
        Returns:
            Tuple[bool, float, Dict[str, float]]: (是否成功, 执行价格, 费用明细)
        """
        try:
            self.execution_stats['total_orders'] += 1
            
            # 检查市场数据
            if not self._validate_market_data(market_data, order.stock_code):
                order.status = OrderStatus.REJECTED
                self.execution_stats['rejected_orders'] += 1
                self.logger.warning(f"订单被拒绝，市场数据无效: {order.order_id}")
                return False, 0.0, {}
            
            # 计算执行价格
            execution_price = self._calculate_execution_price(order, market_data)
            
            # 计算费用
            slippage = self.slippage_model.calculate_slippage(order, market_data)
            commission = self.commission_model.calculate_commission(order)
            market_impact = self.market_impact_model.calculate_impact(order, market_data)
            
            # 应用市场冲击到执行价格
            execution_price += market_impact
            
            # 检查价格合理性
            if not self._validate_execution_price(execution_price, market_data):
                order.status = OrderStatus.REJECTED
                self.execution_stats['rejected_orders'] += 1
                self.logger.warning(f"订单被拒绝，执行价格异常: {order.order_id}")
                return False, 0.0, {}
            
            # 更新订单信息
            order.commission = commission
            order.slippage = slippage
            order.status = OrderStatus.FILLED
            order.fill_time = current_time
            
            # 更新统计信息
            self.execution_stats['filled_orders'] += 1
            self.execution_stats['total_slippage'] += slippage
            self.execution_stats['total_commission'] += commission
            
            # 费用明细
            cost_breakdown = {
                'slippage': slippage,
                'commission': commission,
                'market_impact': abs(market_impact * order.shares),
                'total_cost': slippage + commission + abs(market_impact * order.shares)
            }
            
            self.logger.info(f"订单执行成功: {order.order_id} @{execution_price:.4f}")
            return True, execution_price, cost_breakdown
            
        except Exception as e:
            self.logger.error(f"执行订单失败: {order.order_id}, 错误: {e}")
            order.status = OrderStatus.REJECTED
            self.execution_stats['rejected_orders'] += 1
            return False, 0.0, {}
    
    def _validate_market_data(self, market_data: Dict[str, Any], stock_code: str) -> bool:
        """
        验证市场数据
        
        Args:
            market_data (Dict[str, Any]): 市场数据
            stock_code (str): 股票代码
            
        Returns:
            bool: 是否有效
        """
        required_fields = ['open', 'high', 'low', 'close', 'volume']
        
        for field in required_fields:
            if field not in market_data or market_data[field] is None:
                return False
            
            # 检查价格是否为正数
            if field != 'volume' and market_data[field] <= 0:
                return False
        
        # 检查价格逻辑关系
        high = market_data['high']
        low = market_data['low']
        open_price = market_data['open']
        close_price = market_data['close']
        
        if not (low <= open_price <= high and low <= close_price <= high):
            return False
        
        return True
    
    def _calculate_execution_price(self, order: Order, market_data: Dict[str, Any]) -> float:
        """
        计算执行价格
        
        Args:
            order (Order): 订单信息
            market_data (Dict[str, Any]): 市场数据
            
        Returns:
            float: 执行价格
        """
        # 根据订单类型和市场数据计算执行价格
        open_price = market_data['open']
        high_price = market_data['high']
        low_price = market_data['low']
        close_price = market_data['close']
        
        # 简化处理：使用开盘价作为执行价格
        # 在实际应用中，可以根据具体的执行模型来计算
        execution_price = open_price
        
        # 对于限价单，检查是否能够成交
        if hasattr(order, 'order_model') and order.order_model == ExecutionModel.LIMIT:
            if order.order_type == OrderType.BUY:
                # 买入限价单：只有当市场价格低于或等于限价时才能成交
                if low_price <= order.price:
                    execution_price = min(order.price, open_price)
                else:
                    # 无法成交
                    return -1
            else:
                # 卖出限价单：只有当市场价格高于或等于限价时才能成交
                if high_price >= order.price:
                    execution_price = max(order.price, open_price)
                else:
                    # 无法成交
                    return -1
        
        return execution_price
    
    def _validate_execution_price(self, execution_price: float, market_data: Dict[str, Any]) -> bool:
        """
        验证执行价格
        
        Args:
            execution_price (float): 执行价格
            market_data (Dict[str, Any]): 市场数据
            
        Returns:
            bool: 是否有效
        """
        if execution_price <= 0:
            return False
        
        # 检查执行价格是否在合理范围内
        high_price = market_data['high']
        low_price = market_data['low']
        
        # 允许一定的价格偏差（考虑滑点和市场冲击）
        price_tolerance = 0.1  # 10%的价格容忍度
        upper_bound = high_price * (1 + price_tolerance)
        lower_bound = low_price * (1 - price_tolerance)
        
        return lower_bound <= execution_price <= upper_bound
    
    def batch_execute_orders(self, orders: List[Order], market_data_dict: Dict[str, Dict[str, Any]], 
                           current_time: datetime) -> List[Tuple[Order, bool, float, Dict[str, float]]]:
        """
        批量执行订单
        
        Args:
            orders (List[Order]): 订单列表
            market_data_dict (Dict[str, Dict[str, Any]]): 市场数据字典
            current_time (datetime): 当前时间
            
        Returns:
            List[Tuple[Order, bool, float, Dict[str, float]]]: 执行结果列表
        """
        results = []
        
        for order in orders:
            if order.stock_code in market_data_dict:
                market_data = market_data_dict[order.stock_code]
                success, price, costs = self.execute_order(order, market_data, current_time)
                results.append((order, success, price, costs))
            else:
                # 没有市场数据，订单被拒绝
                order.status = OrderStatus.REJECTED
                self.execution_stats['rejected_orders'] += 1
                results.append((order, False, 0.0, {}))
                self.logger.warning(f"订单被拒绝，缺少市场数据: {order.order_id}")
        
        return results
    
    def get_execution_statistics(self) -> Dict[str, Any]:
        """
        获取执行统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        stats = self.execution_stats.copy()
        
        if stats['total_orders'] > 0:
            stats['fill_rate'] = stats['filled_orders'] / stats['total_orders']
            stats['rejection_rate'] = stats['rejected_orders'] / stats['total_orders']
        else:
            stats['fill_rate'] = 0.0
            stats['rejection_rate'] = 0.0
        
        if stats['filled_orders'] > 0:
            stats['avg_slippage'] = stats['total_slippage'] / stats['filled_orders']
            stats['avg_commission'] = stats['total_commission'] / stats['filled_orders']
        else:
            stats['avg_slippage'] = 0.0
            stats['avg_commission'] = 0.0
        
        return stats
    
    def reset_statistics(self):
        """
        重置统计信息
        """
        self.execution_stats = {
            'total_orders': 0,
            'filled_orders': 0,
            'rejected_orders': 0,
            'total_slippage': 0.0,
            'total_commission': 0.0,
            'avg_execution_time': 0.0
        }
        
        self.logger.info("执行统计信息已重置")


class AdvancedOrderExecutor(OrderExecutor):
    """高级订单执行器"""
    
    def __init__(self, 
                 slippage_model: Optional[SlippageModel] = None,
                 commission_model: Optional[CommissionModel] = None,
                 market_impact_model: Optional[MarketImpactModel] = None,
                 execution_delay: int = 0,
                 partial_fill_enabled: bool = True,
                 min_fill_ratio: float = 0.1):
        """
        初始化高级订单执行器
        
        Args:
            slippage_model (SlippageModel, optional): 滑点模型
            commission_model (CommissionModel, optional): 手续费模型
            market_impact_model (MarketImpactModel, optional): 市场冲击模型
            execution_delay (int): 执行延迟（分钟）
            partial_fill_enabled (bool): 是否允许部分成交
            min_fill_ratio (float): 最小成交比例
        """
        super().__init__(slippage_model, commission_model, market_impact_model, execution_delay)
        
        self.partial_fill_enabled = partial_fill_enabled
        self.min_fill_ratio = min_fill_ratio
        
        self.logger.info("高级订单执行器初始化完成")
    
    def execute_order_with_partial_fill(self, order: Order, market_data: Dict[str, Any], 
                                       current_time: datetime) -> Tuple[bool, float, int, Dict[str, float]]:
        """
        执行订单（支持部分成交）
        
        Args:
            order (Order): 待执行的订单
            market_data (Dict[str, Any]): 市场数据
            current_time (datetime): 当前时间
            
        Returns:
            Tuple[bool, float, int, Dict[str, float]]: (是否成功, 执行价格, 实际成交数量, 费用明细)
        """
        if not self.partial_fill_enabled:
            success, price, costs = self.execute_order(order, market_data, current_time)
            filled_shares = order.shares if success else 0
            return success, price, filled_shares, costs
        
        try:
            # 根据市场流动性计算可成交数量
            volume = market_data.get('volume', 1000000)
            max_fill_ratio = min(0.1, 1000000 / volume)  # 最多占成交量的10%
            max_fillable_shares = int(order.shares * max_fill_ratio)
            
            # 确保至少达到最小成交比例
            min_fillable_shares = int(order.shares * self.min_fill_ratio)
            fillable_shares = max(max_fillable_shares, min_fillable_shares)
            fillable_shares = min(fillable_shares, order.shares)
            
            if fillable_shares < min_fillable_shares:
                order.status = OrderStatus.REJECTED
                self.logger.warning(f"订单被拒绝，流动性不足: {order.order_id}")
                return False, 0.0, 0, {}
            
            # 创建部分订单
            partial_order = Order(
                order_id=f"{order.order_id}_PARTIAL",
                stock_code=order.stock_code,
                order_type=order.order_type,
                shares=fillable_shares,
                price=order.price,
                status=OrderStatus.PENDING,
                create_time=order.create_time
            )
            
            # 执行部分订单
            success, price, costs = self.execute_order(partial_order, market_data, current_time)
            
            if success:
                # 更新原订单
                order.shares -= fillable_shares
                if order.shares == 0:
                    order.status = OrderStatus.FILLED
                else:
                    order.status = OrderStatus.PENDING  # 部分成交，剩余部分继续等待
                
                self.logger.info(f"订单部分成交: {order.order_id}, 成交数量: {fillable_shares}")
            
            return success, price, fillable_shares if success else 0, costs
            
        except Exception as e:
            self.logger.error(f"部分成交执行失败: {order.order_id}, 错误: {e}")
            return False, 0.0, 0, {}