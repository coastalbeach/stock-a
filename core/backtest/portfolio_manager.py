# -*- coding: utf-8 -*-
"""
投资组合管理器

负责管理回测过程中的资金、持仓、风险控制等
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, date
from typing import Dict, List, Any, Optional, Union, Tuple
import logging
from dataclasses import dataclass
from enum import Enum

# 添加项目根目录到系统路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from utils.logger import LoggerManager


class OrderType(Enum):
    """订单类型"""
    BUY = "买入"
    SELL = "卖出"


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "待成交"
    FILLED = "已成交"
    CANCELLED = "已取消"
    REJECTED = "已拒绝"


@dataclass
class Position:
    """持仓信息"""
    stock_code: str
    shares: int
    avg_price: float
    current_price: float
    market_value: float
    cost_basis: float
    unrealized_pnl: float
    realized_pnl: float


class PositionSizer:
    """
    仓位大小计算器
    
    根据不同的策略计算每次交易的仓位大小
    """
    
    def __init__(self, method: str = 'equal_weight', **kwargs):
        """
        初始化仓位计算器
        
        Args:
            method: 仓位计算方法
                - 'equal_weight': 等权重
                - 'fixed_amount': 固定金额
                - 'percent_risk': 风险百分比
                - 'volatility_target': 波动率目标
            **kwargs: 其他参数
        """
        self.method = method
        self.params = kwargs
        
        # 默认参数
        self.default_params = {
            'equal_weight': {'max_positions': 10},
            'fixed_amount': {'amount': 100000},
            'percent_risk': {'risk_percent': 0.02, 'stop_loss': 0.05},
            'volatility_target': {'target_vol': 0.15, 'lookback': 20}
        }
        
        # 合并默认参数
        if method in self.default_params:
            for key, value in self.default_params[method].items():
                if key not in self.params:
                    self.params[key] = value
    
    def calculate_position_size(
        self, 
        stock_code: str,
        current_price: float,
        available_capital: float,
        portfolio_value: float,
        historical_data: Optional[pd.DataFrame] = None,
        current_positions: int = 0
    ) -> int:
        """
        计算仓位大小
        
        Args:
            stock_code: 股票代码
            current_price: 当前价格
            available_capital: 可用资金
            portfolio_value: 投资组合总价值
            historical_data: 历史数据（用于波动率计算）
            current_positions: 当前持仓数量
            
        Returns:
            建议的股票数量
        """
        if self.method == 'equal_weight':
            return self._equal_weight_sizing(
                current_price, available_capital, portfolio_value, current_positions
            )
        elif self.method == 'fixed_amount':
            return self._fixed_amount_sizing(current_price)
        elif self.method == 'percent_risk':
            return self._percent_risk_sizing(
                current_price, portfolio_value, historical_data
            )
        elif self.method == 'volatility_target':
            return self._volatility_target_sizing(
                current_price, portfolio_value, historical_data
            )
        else:
            raise ValueError(f"未知的仓位计算方法: {self.method}")
    
    def _equal_weight_sizing(
        self, 
        current_price: float, 
        available_capital: float, 
        portfolio_value: float,
        current_positions: int
    ) -> int:
        """等权重仓位计算"""
        max_positions = self.params.get('max_positions', 10)
        target_weight = 1.0 / max_positions
        target_value = portfolio_value * target_weight
        
        # 确保不超过可用资金
        target_value = min(target_value, available_capital)
        
        if target_value <= 0 or current_price <= 0:
            return 0
        
        shares = int(target_value / current_price / 100) * 100  # 按手数计算
        return max(0, shares)
    
    def _fixed_amount_sizing(self, current_price: float) -> int:
        """固定金额仓位计算"""
        amount = self.params.get('amount', 100000)
        
        if current_price <= 0:
            return 0
        
        shares = int(amount / current_price / 100) * 100  # 按手数计算
        return max(0, shares)
    
    def _percent_risk_sizing(
        self, 
        current_price: float, 
        portfolio_value: float,
        historical_data: Optional[pd.DataFrame] = None
    ) -> int:
        """风险百分比仓位计算"""
        risk_percent = self.params.get('risk_percent', 0.02)
        stop_loss = self.params.get('stop_loss', 0.05)
        
        risk_amount = portfolio_value * risk_percent
        stop_loss_amount = current_price * stop_loss
        
        if stop_loss_amount <= 0:
            return 0
        
        shares = int(risk_amount / stop_loss_amount / 100) * 100
        return max(0, shares)
    
    def _volatility_target_sizing(
        self, 
        current_price: float, 
        portfolio_value: float,
        historical_data: Optional[pd.DataFrame] = None
    ) -> int:
        """波动率目标仓位计算"""
        target_vol = self.params.get('target_vol', 0.15)
        lookback = self.params.get('lookback', 20)
        
        if historical_data is None or len(historical_data) < lookback:
            # 如果没有足够的历史数据，使用等权重方法
            return self._equal_weight_sizing(current_price, portfolio_value, portfolio_value, 0)
        
        # 计算历史波动率
        if '收盘' in historical_data.columns:
            returns = historical_data['收盘'].pct_change().dropna()
            if len(returns) >= lookback:
                historical_vol = returns.tail(lookback).std() * np.sqrt(252)  # 年化波动率
                
                if historical_vol > 0:
                    vol_ratio = target_vol / historical_vol
                    target_weight = min(vol_ratio, 1.0)  # 最大权重不超过100%
                    target_value = portfolio_value * target_weight
                    
                    shares = int(target_value / current_price / 100) * 100
                    return max(0, shares)
        
        # 如果计算失败，使用等权重方法
        return self._equal_weight_sizing(current_price, portfolio_value, portfolio_value, 0)
    entry_date: date
    last_update: date


@dataclass
class Order:
    """订单信息"""
    order_id: str
    stock_code: str
    order_type: OrderType
    shares: int
    price: float
    status: OrderStatus
    create_time: datetime
    fill_time: Optional[datetime] = None
    commission: float = 0.0
    slippage: float = 0.0


@dataclass
class Trade:
    """交易记录"""
    trade_id: str
    stock_code: str
    entry_date: date
    exit_date: date
    entry_price: float
    exit_price: float
    shares: int
    pnl: float
    commission: float
    return_rate: float
    holding_days: int


class RiskManager:
    """风险管理器"""
    
    def __init__(self, max_position_size: float = 0.1, max_drawdown: float = 0.2,
                 stop_loss: float = 0.1, take_profit: float = 0.2):
        """
        初始化风险管理器
        
        Args:
            max_position_size (float): 单个股票最大仓位比例
            max_drawdown (float): 最大回撤限制
            stop_loss (float): 止损比例
            take_profit (float): 止盈比例
        """
        self.max_position_size = max_position_size
        self.max_drawdown = max_drawdown
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        
        # 获取日志记录器
        logger_manager = LoggerManager()
        self.logger = logger_manager.get_logger('risk_manager')
    
    def check_position_size(self, portfolio_value: float, order_value: float) -> bool:
        """
        检查仓位大小是否符合风险控制要求
        
        Args:
            portfolio_value (float): 组合总价值
            order_value (float): 订单价值
            
        Returns:
            bool: 是否通过检查
        """
        position_ratio = order_value / portfolio_value
        if position_ratio > self.max_position_size:
            self.logger.warning(f"仓位过大: {position_ratio:.2%} > {self.max_position_size:.2%}")
            return False
        return True
    
    def check_drawdown(self, current_value: float, peak_value: float) -> bool:
        """
        检查回撤是否超过限制
        
        Args:
            current_value (float): 当前价值
            peak_value (float): 历史最高价值
            
        Returns:
            bool: 是否通过检查
        """
        if peak_value <= 0:
            return True
        
        drawdown = (peak_value - current_value) / peak_value
        if drawdown > self.max_drawdown:
            self.logger.warning(f"回撤过大: {drawdown:.2%} > {self.max_drawdown:.2%}")
            return False
        return True
    
    def check_stop_loss(self, current_price: float, entry_price: float, order_type: OrderType) -> bool:
        """
        检查是否触发止损
        
        Args:
            current_price (float): 当前价格
            entry_price (float): 入场价格
            order_type (OrderType): 订单类型
            
        Returns:
            bool: 是否触发止损
        """
        if order_type == OrderType.BUY:
            # 多头止损
            loss_ratio = (entry_price - current_price) / entry_price
            return loss_ratio >= self.stop_loss
        else:
            # 空头止损
            loss_ratio = (current_price - entry_price) / entry_price
            return loss_ratio >= self.stop_loss
    
    def check_take_profit(self, current_price: float, entry_price: float, order_type: OrderType) -> bool:
        """
        检查是否触发止盈
        
        Args:
            current_price (float): 当前价格
            entry_price (float): 入场价格
            order_type (OrderType): 订单类型
            
        Returns:
            bool: 是否触发止盈
        """
        if order_type == OrderType.BUY:
            # 多头止盈
            profit_ratio = (current_price - entry_price) / entry_price
            return profit_ratio >= self.take_profit
        else:
            # 空头止盈
            profit_ratio = (entry_price - current_price) / entry_price
            return profit_ratio >= self.take_profit


class PortfolioManager:
    """投资组合管理器"""
    
    def __init__(self, initial_cash: float = 100000.0, commission_rate: float = 0.0003,
                 slippage_rate: float = 0.001, risk_manager: Optional[RiskManager] = None):
        """
        初始化投资组合管理器
        
        Args:
            initial_cash (float): 初始资金
            commission_rate (float): 手续费率
            slippage_rate (float): 滑点率
            risk_manager (RiskManager, optional): 风险管理器
        """
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate
        
        # 持仓管理
        self.positions: Dict[str, Position] = {}
        self.orders: List[Order] = []
        self.trades: List[Trade] = []
        
        # 风险管理
        self.risk_manager = risk_manager or RiskManager()
        
        # 绩效跟踪
        self.portfolio_values = []
        self.daily_returns = []
        self.peak_value = initial_cash
        self.max_drawdown = 0.0
        
        # 统计信息
        self.total_commission = 0.0
        self.total_slippage = 0.0
        self.order_counter = 0
        self.trade_counter = 0
        
        # 获取日志记录器
        logger_manager = LoggerManager()
        self.logger = logger_manager.get_logger('portfolio_manager')
        
        self.logger.info(f"投资组合管理器初始化完成，初始资金: {initial_cash}")
    
    def get_portfolio_value(self, current_prices: Dict[str, float]) -> float:
        """
        计算投资组合总价值
        
        Args:
            current_prices (Dict[str, float]): 当前价格字典
            
        Returns:
            float: 投资组合总价值
        """
        market_value = 0.0
        
        for stock_code, position in self.positions.items():
            if stock_code in current_prices:
                position.current_price = current_prices[stock_code]
                position.market_value = position.shares * position.current_price
                position.unrealized_pnl = position.market_value - position.cost_basis
                market_value += position.market_value
        
        return self.cash + market_value
    
    def create_order(self, stock_code: str, order_type: OrderType, shares: int, 
                    price: float, current_date: date) -> Optional[Order]:
        """
        创建订单
        
        Args:
            stock_code (str): 股票代码
            order_type (OrderType): 订单类型
            shares (int): 股票数量
            price (float): 价格
            current_date (date): 当前日期
            
        Returns:
            Optional[Order]: 创建的订单，如果失败则返回None
        """
        try:
            # 生成订单ID
            self.order_counter += 1
            order_id = f"ORDER_{self.order_counter:06d}"
            
            # 计算订单价值
            order_value = shares * price
            
            # 风险检查
            if order_type == OrderType.BUY:
                # 检查资金是否充足
                total_cost = order_value * (1 + self.commission_rate + self.slippage_rate)
                if total_cost > self.cash:
                    self.logger.warning(f"资金不足: 需要 {total_cost:.2f}, 可用 {self.cash:.2f}")
                    return None
                
                # 检查仓位大小
                portfolio_value = self.get_portfolio_value({stock_code: price})
                if not self.risk_manager.check_position_size(portfolio_value, order_value):
                    return None
            
            elif order_type == OrderType.SELL:
                # 检查持仓是否充足
                if stock_code not in self.positions or self.positions[stock_code].shares < shares:
                    available_shares = self.positions.get(stock_code, Position(
                        stock_code, 0, 0, 0, 0, 0, 0, 0, current_date, current_date
                    )).shares
                    self.logger.warning(f"持仓不足: 需要 {shares}, 可用 {available_shares}")
                    return None
            
            # 创建订单
            order = Order(
                order_id=order_id,
                stock_code=stock_code,
                order_type=order_type,
                shares=shares,
                price=price,
                status=OrderStatus.PENDING,
                create_time=datetime.combine(current_date, datetime.min.time())
            )
            
            self.orders.append(order)
            self.logger.info(f"订单创建成功: {order_id} {order_type.value} {stock_code} {shares}股 @{price:.2f}")
            
            return order
            
        except Exception as e:
            self.logger.error(f"创建订单失败: {e}")
            return None
    
    def execute_order(self, order: Order, execution_price: float, current_date: date) -> bool:
        """
        执行订单
        
        Args:
            order (Order): 待执行的订单
            execution_price (float): 执行价格
            current_date (date): 当前日期
            
        Returns:
            bool: 是否执行成功
        """
        try:
            # 计算滑点和手续费
            slippage = abs(execution_price - order.price) * order.shares
            commission = execution_price * order.shares * self.commission_rate
            
            order.commission = commission
            order.slippage = slippage
            
            if order.order_type == OrderType.BUY:
                # 买入操作
                total_cost = execution_price * order.shares + commission + slippage
                
                if total_cost > self.cash:
                    order.status = OrderStatus.REJECTED
                    self.logger.warning(f"订单被拒绝，资金不足: {order.order_id}")
                    return False
                
                # 更新现金
                self.cash -= total_cost
                
                # 更新持仓
                if order.stock_code in self.positions:
                    position = self.positions[order.stock_code]
                    total_shares = position.shares + order.shares
                    total_cost_basis = position.cost_basis + execution_price * order.shares
                    position.shares = total_shares
                    position.avg_price = total_cost_basis / total_shares
                    position.cost_basis = total_cost_basis
                    position.last_update = current_date
                else:
                    self.positions[order.stock_code] = Position(
                        stock_code=order.stock_code,
                        shares=order.shares,
                        avg_price=execution_price,
                        current_price=execution_price,
                        market_value=execution_price * order.shares,
                        cost_basis=execution_price * order.shares,
                        unrealized_pnl=0.0,
                        realized_pnl=0.0,
                        entry_date=current_date,
                        last_update=current_date
                    )
            
            elif order.order_type == OrderType.SELL:
                # 卖出操作
                if order.stock_code not in self.positions:
                    order.status = OrderStatus.REJECTED
                    self.logger.warning(f"订单被拒绝，无持仓: {order.order_id}")
                    return False
                
                position = self.positions[order.stock_code]
                if position.shares < order.shares:
                    order.status = OrderStatus.REJECTED
                    self.logger.warning(f"订单被拒绝，持仓不足: {order.order_id}")
                    return False
                
                # 计算收入
                gross_proceeds = execution_price * order.shares
                net_proceeds = gross_proceeds - commission - slippage
                
                # 更新现金
                self.cash += net_proceeds
                
                # 计算已实现盈亏
                cost_per_share = position.cost_basis / position.shares
                realized_pnl = (execution_price - cost_per_share) * order.shares - commission - slippage
                
                # 更新持仓
                position.shares -= order.shares
                position.cost_basis -= cost_per_share * order.shares
                position.realized_pnl += realized_pnl
                position.last_update = current_date
                
                # 如果持仓为0，创建交易记录
                if position.shares == 0:
                    self._create_trade_record(position, execution_price, current_date, realized_pnl, commission + slippage)
                    del self.positions[order.stock_code]
            
            # 更新订单状态
            order.status = OrderStatus.FILLED
            order.fill_time = datetime.combine(current_date, datetime.min.time())
            
            # 更新统计信息
            self.total_commission += commission
            self.total_slippage += slippage
            
            self.logger.info(f"订单执行成功: {order.order_id} @{execution_price:.2f}")
            return True
            
        except Exception as e:
            self.logger.error(f"执行订单失败: {e}")
            order.status = OrderStatus.REJECTED
            return False
    
    def _create_trade_record(self, position: Position, exit_price: float, exit_date: date, 
                           pnl: float, commission: float):
        """
        创建交易记录
        
        Args:
            position (Position): 持仓信息
            exit_price (float): 退出价格
            exit_date (date): 退出日期
            pnl (float): 盈亏
            commission (float): 手续费
        """
        self.trade_counter += 1
        trade_id = f"TRADE_{self.trade_counter:06d}"
        
        holding_days = (exit_date - position.entry_date).days
        return_rate = pnl / position.cost_basis if position.cost_basis > 0 else 0
        
        trade = Trade(
            trade_id=trade_id,
            stock_code=position.stock_code,
            entry_date=position.entry_date,
            exit_date=exit_date,
            entry_price=position.avg_price,
            exit_price=exit_price,
            shares=position.shares,
            pnl=pnl,
            commission=commission,
            return_rate=return_rate,
            holding_days=holding_days
        )
        
        self.trades.append(trade)
        self.logger.info(f"交易记录创建: {trade_id} {position.stock_code} 盈亏: {pnl:.2f}")
    
    def update_portfolio(self, current_prices: Dict[str, float], current_date: date):
        """
        更新投资组合状态
        
        Args:
            current_prices (Dict[str, float]): 当前价格
            current_date (date): 当前日期
        """
        # 计算投资组合价值
        portfolio_value = self.get_portfolio_value(current_prices)
        self.portfolio_values.append({
            '日期': current_date,
            '总价值': portfolio_value,
            '现金': self.cash,
            '市值': portfolio_value - self.cash
        })
        
        # 计算日收益率
        if len(self.portfolio_values) > 1:
            prev_value = self.portfolio_values[-2]['总价值']
            daily_return = (portfolio_value - prev_value) / prev_value
            self.daily_returns.append(daily_return)
        
        # 更新最大回撤
        if portfolio_value > self.peak_value:
            self.peak_value = portfolio_value
        
        current_drawdown = (self.peak_value - portfolio_value) / self.peak_value
        if current_drawdown > self.max_drawdown:
            self.max_drawdown = current_drawdown
        
        # 风险检查
        if not self.risk_manager.check_drawdown(portfolio_value, self.peak_value):
            self.logger.warning("触发最大回撤限制")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        获取绩效指标
        
        Returns:
            Dict[str, Any]: 绩效指标字典
        """
        if not self.portfolio_values:
            return {}
        
        current_value = self.portfolio_values[-1]['总价值']
        total_return = (current_value - self.initial_cash) / self.initial_cash
        
        # 计算年化收益率
        days = len(self.portfolio_values)
        annual_return = (1 + total_return) ** (252 / days) - 1 if days > 0 else 0
        
        # 计算夏普比率
        if self.daily_returns:
            returns_array = np.array(self.daily_returns)
            sharpe_ratio = np.mean(returns_array) / np.std(returns_array) * np.sqrt(252) if np.std(returns_array) > 0 else 0
        else:
            sharpe_ratio = 0
        
        # 交易统计
        winning_trades = [t for t in self.trades if t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl <= 0]
        
        return {
            'initial_cash': self.initial_cash,
            'final_value': current_value,
            'total_return': total_return,
            'annual_return': annual_return,
            'max_drawdown': self.max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'total_trades': len(self.trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': len(winning_trades) / len(self.trades) if self.trades else 0,
            'avg_win': np.mean([t.pnl for t in winning_trades]) if winning_trades else 0,
            'avg_loss': np.mean([t.pnl for t in losing_trades]) if losing_trades else 0,
            'total_commission': self.total_commission,
            'total_slippage': self.total_slippage,
        }
    
    def get_positions_summary(self) -> pd.DataFrame:
        """
        获取持仓汇总
        
        Returns:
            pd.DataFrame: 持仓汇总数据
        """
        if not self.positions:
            return pd.DataFrame()
        
        positions_data = []
        for position in self.positions.values():
            positions_data.append({
                '股票代码': position.stock_code,
                '持仓数量': position.shares,
                '平均成本': position.avg_price,
                '当前价格': position.current_price,
                '市值': position.market_value,
                '成本': position.cost_basis,
                '浮动盈亏': position.unrealized_pnl,
                '已实现盈亏': position.realized_pnl,
                '持仓天数': (date.today() - position.entry_date).days
            })
        
        return pd.DataFrame(positions_data)
    
    def get_trades_summary(self) -> pd.DataFrame:
        """
        获取交易汇总
        
        Returns:
            pd.DataFrame: 交易汇总数据
        """
        if not self.trades:
            return pd.DataFrame()
        
        trades_data = []
        for trade in self.trades:
            trades_data.append({
                '交易ID': trade.trade_id,
                '股票代码': trade.stock_code,
                '开仓日期': trade.entry_date,
                '平仓日期': trade.exit_date,
                '开仓价格': trade.entry_price,
                '平仓价格': trade.exit_price,
                '数量': trade.shares,
                '盈亏': trade.pnl,
                '手续费': trade.commission,
                '收益率': trade.return_rate,
                '持仓天数': trade.holding_days
            })
        
        return pd.DataFrame(trades_data)