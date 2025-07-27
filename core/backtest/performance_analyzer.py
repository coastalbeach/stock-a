# -*- coding: utf-8 -*-
"""
绩效分析器

负责计算回测的各种绩效指标和风险指标
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, date
from typing import Dict, List, Any, Optional, Union, Tuple
import logging
from dataclasses import dataclass
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# 添加项目根目录到系统路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from utils.logger import LoggerManager
from core.backtest.portfolio_manager import Trade


@dataclass
class PerformanceMetrics:
    """绩效指标数据类"""
    # 收益指标
    total_return: float
    annual_return: float
    cumulative_return: float
    
    # 风险指标
    volatility: float
    max_drawdown: float
    var_95: float
    cvar_95: float
    
    # 风险调整收益指标
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    information_ratio: float
    
    # 交易指标
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    
    # 其他指标
    beta: float
    alpha: float
    tracking_error: float
    r_squared: float


class PerformanceAnalyzer:
    """绩效分析器"""
    
    def __init__(self, benchmark_returns: Optional[pd.Series] = None, risk_free_rate: float = 0.03):
        """
        初始化绩效分析器
        
        Args:
            benchmark_returns (pd.Series, optional): 基准收益率序列
            risk_free_rate (float): 无风险利率（年化）
        """
        self.benchmark_returns = benchmark_returns
        self.risk_free_rate = risk_free_rate
        
        # 获取日志记录器
        logger_manager = LoggerManager()
        self.logger = logger_manager.get_logger('performance_analyzer')
        
        self.logger.info("绩效分析器初始化完成")
    
    def calculate_returns(self, portfolio_values: List[Dict[str, Any]]) -> pd.Series:
        """
        计算收益率序列
        
        Args:
            portfolio_values (List[Dict[str, Any]]): 投资组合价值序列
            
        Returns:
            pd.Series: 收益率序列
        """
        if len(portfolio_values) < 2:
            return pd.Series()
        
        df = pd.DataFrame(portfolio_values)
        df['日期'] = pd.to_datetime(df['日期'])
        df = df.set_index('日期').sort_index()
        
        # 计算日收益率
        returns = df['总价值'].pct_change().dropna()
        
        return returns
    
    def calculate_cumulative_returns(self, returns: pd.Series) -> pd.Series:
        """
        计算累计收益率
        
        Args:
            returns (pd.Series): 收益率序列
            
        Returns:
            pd.Series: 累计收益率序列
        """
        return (1 + returns).cumprod() - 1
    
    def calculate_drawdown(self, portfolio_values: List[Dict[str, Any]]) -> Tuple[pd.Series, float, date]:
        """
        计算回撤序列
        
        Args:
            portfolio_values (List[Dict[str, Any]]): 投资组合价值序列
            
        Returns:
            Tuple[pd.Series, float, date]: (回撤序列, 最大回撤, 最大回撤日期)
        """
        if len(portfolio_values) < 2:
            return pd.Series(), 0.0, None
        
        df = pd.DataFrame(portfolio_values)
        df['日期'] = pd.to_datetime(df['日期'])
        df = df.set_index('日期').sort_index()
        
        # 计算累计最高价值
        cumulative_max = df['总价值'].expanding().max()
        
        # 计算回撤
        drawdown = (df['总价值'] - cumulative_max) / cumulative_max
        
        # 找到最大回撤
        max_drawdown = drawdown.min()
        max_drawdown_date = drawdown.idxmin()
        
        return drawdown, abs(max_drawdown), max_drawdown_date
    
    def calculate_var_cvar(self, returns: pd.Series, confidence_level: float = 0.95) -> Tuple[float, float]:
        """
        计算VaR和CVaR
        
        Args:
            returns (pd.Series): 收益率序列
            confidence_level (float): 置信水平
            
        Returns:
            Tuple[float, float]: (VaR, CVaR)
        """
        if len(returns) == 0:
            return 0.0, 0.0
        
        # 计算VaR
        var = np.percentile(returns, (1 - confidence_level) * 100)
        
        # 计算CVaR（条件VaR）
        cvar = returns[returns <= var].mean()
        
        return abs(var), abs(cvar)
    
    def calculate_sharpe_ratio(self, returns: pd.Series, risk_free_rate: Optional[float] = None) -> float:
        """
        计算夏普比率
        
        Args:
            returns (pd.Series): 收益率序列
            risk_free_rate (float, optional): 无风险利率
            
        Returns:
            float: 夏普比率
        """
        if len(returns) == 0 or returns.std() == 0:
            return 0.0
        
        rf_rate = risk_free_rate or self.risk_free_rate
        daily_rf_rate = rf_rate / 252  # 转换为日无风险利率
        
        excess_returns = returns - daily_rf_rate
        sharpe = excess_returns.mean() / returns.std() * np.sqrt(252)
        
        return sharpe
    
    def calculate_sortino_ratio(self, returns: pd.Series, risk_free_rate: Optional[float] = None) -> float:
        """
        计算索提诺比率
        
        Args:
            returns (pd.Series): 收益率序列
            risk_free_rate (float, optional): 无风险利率
            
        Returns:
            float: 索提诺比率
        """
        if len(returns) == 0:
            return 0.0
        
        rf_rate = risk_free_rate or self.risk_free_rate
        daily_rf_rate = rf_rate / 252
        
        excess_returns = returns - daily_rf_rate
        downside_returns = returns[returns < daily_rf_rate]
        
        if len(downside_returns) == 0 or downside_returns.std() == 0:
            return 0.0
        
        sortino = excess_returns.mean() / downside_returns.std() * np.sqrt(252)
        
        return sortino
    
    def calculate_calmar_ratio(self, returns: pd.Series, max_drawdown: float) -> float:
        """
        计算卡玛比率
        
        Args:
            returns (pd.Series): 收益率序列
            max_drawdown (float): 最大回撤
            
        Returns:
            float: 卡玛比率
        """
        if len(returns) == 0 or max_drawdown == 0:
            return 0.0
        
        annual_return = (1 + returns.mean()) ** 252 - 1
        calmar = annual_return / max_drawdown
        
        return calmar
    
    def calculate_information_ratio(self, returns: pd.Series, benchmark_returns: Optional[pd.Series] = None) -> float:
        """
        计算信息比率
        
        Args:
            returns (pd.Series): 收益率序列
            benchmark_returns (pd.Series, optional): 基准收益率序列
            
        Returns:
            float: 信息比率
        """
        benchmark = benchmark_returns or self.benchmark_returns
        
        if benchmark is None or len(returns) == 0 or len(benchmark) == 0:
            return 0.0
        
        # 对齐时间序列
        aligned_returns, aligned_benchmark = returns.align(benchmark, join='inner')
        
        if len(aligned_returns) == 0:
            return 0.0
        
        # 计算超额收益
        excess_returns = aligned_returns - aligned_benchmark
        
        if excess_returns.std() == 0:
            return 0.0
        
        information_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(252)
        
        return information_ratio
    
    def calculate_beta_alpha(self, returns: pd.Series, benchmark_returns: Optional[pd.Series] = None) -> Tuple[float, float, float]:
        """
        计算Beta、Alpha和R²
        
        Args:
            returns (pd.Series): 收益率序列
            benchmark_returns (pd.Series, optional): 基准收益率序列
            
        Returns:
            Tuple[float, float, float]: (Beta, Alpha, R²)
        """
        benchmark = benchmark_returns or self.benchmark_returns
        
        if benchmark is None or len(returns) == 0 or len(benchmark) == 0:
            return 0.0, 0.0, 0.0
        
        # 对齐时间序列
        aligned_returns, aligned_benchmark = returns.align(benchmark, join='inner')
        
        if len(aligned_returns) < 2:
            return 0.0, 0.0, 0.0
        
        try:
            # 线性回归
            slope, intercept, r_value, p_value, std_err = stats.linregress(aligned_benchmark, aligned_returns)
            
            beta = slope
            alpha = intercept * 252  # 年化Alpha
            r_squared = r_value ** 2
            
            return beta, alpha, r_squared
            
        except Exception as e:
            self.logger.warning(f"计算Beta和Alpha失败: {e}")
            return 0.0, 0.0, 0.0
    
    def calculate_tracking_error(self, returns: pd.Series, benchmark_returns: Optional[pd.Series] = None) -> float:
        """
        计算跟踪误差
        
        Args:
            returns (pd.Series): 收益率序列
            benchmark_returns (pd.Series, optional): 基准收益率序列
            
        Returns:
            float: 跟踪误差（年化）
        """
        benchmark = benchmark_returns or self.benchmark_returns
        
        if benchmark is None or len(returns) == 0 or len(benchmark) == 0:
            return 0.0
        
        # 对齐时间序列
        aligned_returns, aligned_benchmark = returns.align(benchmark, join='inner')
        
        if len(aligned_returns) == 0:
            return 0.0
        
        # 计算超额收益的标准差
        excess_returns = aligned_returns - aligned_benchmark
        tracking_error = excess_returns.std() * np.sqrt(252)
        
        return tracking_error
    
    def analyze_trades(self, trades: List[Trade]) -> Dict[str, Any]:
        """
        分析交易记录
        
        Args:
            trades (List[Trade]): 交易记录列表
            
        Returns:
            Dict[str, Any]: 交易分析结果
        """
        if not trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'profit_factor': 0.0,
                'avg_holding_days': 0.0,
                'best_trade': 0.0,
                'worst_trade': 0.0,
                'total_pnl': 0.0
            }
        
        # 分类交易
        winning_trades = [t for t in trades if t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl <= 0]
        
        # 基本统计
        total_trades = len(trades)
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        win_rate = win_count / total_trades if total_trades > 0 else 0
        
        # 盈亏统计
        total_wins = sum(t.pnl for t in winning_trades)
        total_losses = abs(sum(t.pnl for t in losing_trades))
        avg_win = total_wins / win_count if win_count > 0 else 0
        avg_loss = total_losses / loss_count if loss_count > 0 else 0
        
        # 盈亏比
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        
        # 持仓天数
        avg_holding_days = np.mean([t.holding_days for t in trades])
        
        # 最佳和最差交易
        best_trade = max(t.pnl for t in trades)
        worst_trade = min(t.pnl for t in trades)
        
        # 总盈亏
        total_pnl = sum(t.pnl for t in trades)
        
        return {
            'total_trades': total_trades,
            'winning_trades': win_count,
            'losing_trades': loss_count,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'avg_holding_days': avg_holding_days,
            'best_trade': best_trade,
            'worst_trade': worst_trade,
            'total_pnl': total_pnl
        }
    
    def calculate_comprehensive_metrics(self, portfolio_values: List[Dict[str, Any]], 
                                      trades: List[Trade]) -> PerformanceMetrics:
        """
        计算综合绩效指标
        
        Args:
            portfolio_values (List[Dict[str, Any]]): 投资组合价值序列
            trades (List[Trade]): 交易记录列表
            
        Returns:
            PerformanceMetrics: 综合绩效指标
        """
        try:
            # 计算收益率
            returns = self.calculate_returns(portfolio_values)
            
            if len(returns) == 0:
                # 返回空指标
                return PerformanceMetrics(
                    total_return=0.0, annual_return=0.0, cumulative_return=0.0,
                    volatility=0.0, max_drawdown=0.0, var_95=0.0, cvar_95=0.0,
                    sharpe_ratio=0.0, sortino_ratio=0.0, calmar_ratio=0.0, information_ratio=0.0,
                    total_trades=0, winning_trades=0, losing_trades=0, win_rate=0.0,
                    avg_win=0.0, avg_loss=0.0, profit_factor=0.0,
                    beta=0.0, alpha=0.0, tracking_error=0.0, r_squared=0.0
                )
            
            # 收益指标
            total_return = (1 + returns).prod() - 1
            annual_return = (1 + returns.mean()) ** 252 - 1
            cumulative_return = total_return
            
            # 风险指标
            volatility = returns.std() * np.sqrt(252)
            drawdown_series, max_drawdown, max_dd_date = self.calculate_drawdown(portfolio_values)
            var_95, cvar_95 = self.calculate_var_cvar(returns)
            
            # 风险调整收益指标
            sharpe_ratio = self.calculate_sharpe_ratio(returns)
            sortino_ratio = self.calculate_sortino_ratio(returns)
            calmar_ratio = self.calculate_calmar_ratio(returns, max_drawdown)
            information_ratio = self.calculate_information_ratio(returns)
            
            # Beta、Alpha和相关指标
            beta, alpha, r_squared = self.calculate_beta_alpha(returns)
            tracking_error = self.calculate_tracking_error(returns)
            
            # 交易分析
            trade_analysis = self.analyze_trades(trades)
            
            return PerformanceMetrics(
                total_return=total_return,
                annual_return=annual_return,
                cumulative_return=cumulative_return,
                volatility=volatility,
                max_drawdown=max_drawdown,
                var_95=var_95,
                cvar_95=cvar_95,
                sharpe_ratio=sharpe_ratio,
                sortino_ratio=sortino_ratio,
                calmar_ratio=calmar_ratio,
                information_ratio=information_ratio,
                total_trades=trade_analysis['total_trades'],
                winning_trades=trade_analysis['winning_trades'],
                losing_trades=trade_analysis['losing_trades'],
                win_rate=trade_analysis['win_rate'],
                avg_win=trade_analysis['avg_win'],
                avg_loss=trade_analysis['avg_loss'],
                profit_factor=trade_analysis['profit_factor'],
                beta=beta,
                alpha=alpha,
                tracking_error=tracking_error,
                r_squared=r_squared
            )
            
        except Exception as e:
            self.logger.error(f"计算综合绩效指标失败: {e}")
            # 返回空指标
            return PerformanceMetrics(
                total_return=0.0, annual_return=0.0, cumulative_return=0.0,
                volatility=0.0, max_drawdown=0.0, var_95=0.0, cvar_95=0.0,
                sharpe_ratio=0.0, sortino_ratio=0.0, calmar_ratio=0.0, information_ratio=0.0,
                total_trades=0, winning_trades=0, losing_trades=0, win_rate=0.0,
                avg_win=0.0, avg_loss=0.0, profit_factor=0.0,
                beta=0.0, alpha=0.0, tracking_error=0.0, r_squared=0.0
            )
    
    def generate_performance_report(self, metrics: PerformanceMetrics) -> str:
        """
        生成绩效报告
        
        Args:
            metrics (PerformanceMetrics): 绩效指标
            
        Returns:
            str: 绩效报告文本
        """
        report = f"""
=== 回测绩效报告 ===

【收益指标】
总收益率: {metrics.total_return:.2%}
年化收益率: {metrics.annual_return:.2%}
累计收益率: {metrics.cumulative_return:.2%}

【风险指标】
年化波动率: {metrics.volatility:.2%}
最大回撤: {metrics.max_drawdown:.2%}
VaR (95%): {metrics.var_95:.2%}
CVaR (95%): {metrics.cvar_95:.2%}

【风险调整收益指标】
夏普比率: {metrics.sharpe_ratio:.4f}
索提诺比率: {metrics.sortino_ratio:.4f}
卡玛比率: {metrics.calmar_ratio:.4f}
信息比率: {metrics.information_ratio:.4f}

【交易指标】
总交易次数: {metrics.total_trades}
盈利交易: {metrics.winning_trades}
亏损交易: {metrics.losing_trades}
胜率: {metrics.win_rate:.2%}
平均盈利: {metrics.avg_win:.2f}
平均亏损: {metrics.avg_loss:.2f}
盈亏比: {metrics.profit_factor:.2f}

【市场相关指标】
Beta: {metrics.beta:.4f}
Alpha: {metrics.alpha:.2%}
跟踪误差: {metrics.tracking_error:.2%}
R²: {metrics.r_squared:.4f}
"""
        return report
    
    def export_metrics_to_dict(self, metrics: PerformanceMetrics) -> Dict[str, Any]:
        """
        将绩效指标导出为字典
        
        Args:
            metrics (PerformanceMetrics): 绩效指标
            
        Returns:
            Dict[str, Any]: 指标字典
        """
        return {
            '总收益率': metrics.total_return,
            '年化收益率': metrics.annual_return,
            '累计收益率': metrics.cumulative_return,
            '年化波动率': metrics.volatility,
            '最大回撤': metrics.max_drawdown,
            'VaR_95': metrics.var_95,
            'CVaR_95': metrics.cvar_95,
            '夏普比率': metrics.sharpe_ratio,
            '索提诺比率': metrics.sortino_ratio,
            '卡玛比率': metrics.calmar_ratio,
            '信息比率': metrics.information_ratio,
            '总交易次数': metrics.total_trades,
            '盈利交易': metrics.winning_trades,
            '亏损交易': metrics.losing_trades,
            '胜率': metrics.win_rate,
            '平均盈利': metrics.avg_win,
            '平均亏损': metrics.avg_loss,
            '盈亏比': metrics.profit_factor,
            'Beta': metrics.beta,
            'Alpha': metrics.alpha,
            '跟踪误差': metrics.tracking_error,
            'R平方': metrics.r_squared
        }