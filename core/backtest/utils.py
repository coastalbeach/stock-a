# -*- coding: utf-8 -*-
"""
回测工具函数

提供回测过程中需要的各种辅助函数
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
import logging
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# 添加项目根目录到系统路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from utils.logger import LoggerManager


class DateUtils:
    """日期工具类"""
    
    @staticmethod
    def is_trading_day(date_obj: Union[str, datetime, date]) -> bool:
        """
        判断是否为交易日（简化版本，仅排除周末）
        
        Args:
            date_obj (Union[str, datetime, date]): 日期对象
            
        Returns:
            bool: 是否为交易日
        """
        if isinstance(date_obj, str):
            date_obj = pd.to_datetime(date_obj).date()
        elif isinstance(date_obj, datetime):
            date_obj = date_obj.date()
        
        # 排除周末
        return date_obj.weekday() < 5
    
    @staticmethod
    def get_trading_days(start_date: Union[str, datetime, date], 
                        end_date: Union[str, datetime, date]) -> List[date]:
        """
        获取指定日期范围内的交易日列表
        
        Args:
            start_date (Union[str, datetime, date]): 开始日期
            end_date (Union[str, datetime, date]): 结束日期
            
        Returns:
            List[date]: 交易日列表
        """
        if isinstance(start_date, str):
            start_date = pd.to_datetime(start_date).date()
        elif isinstance(start_date, datetime):
            start_date = start_date.date()
            
        if isinstance(end_date, str):
            end_date = pd.to_datetime(end_date).date()
        elif isinstance(end_date, datetime):
            end_date = end_date.date()
        
        trading_days = []
        current_date = start_date
        
        while current_date <= end_date:
            if DateUtils.is_trading_day(current_date):
                trading_days.append(current_date)
            current_date += timedelta(days=1)
        
        return trading_days
    
    @staticmethod
    def get_next_trading_day(date_obj: Union[str, datetime, date]) -> date:
        """
        获取下一个交易日
        
        Args:
            date_obj (Union[str, datetime, date]): 当前日期
            
        Returns:
            date: 下一个交易日
        """
        if isinstance(date_obj, str):
            date_obj = pd.to_datetime(date_obj).date()
        elif isinstance(date_obj, datetime):
            date_obj = date_obj.date()
        
        next_date = date_obj + timedelta(days=1)
        while not DateUtils.is_trading_day(next_date):
            next_date += timedelta(days=1)
        
        return next_date
    
    @staticmethod
    def get_prev_trading_day(date_obj: Union[str, datetime, date]) -> date:
        """
        获取上一个交易日
        
        Args:
            date_obj (Union[str, datetime, date]): 当前日期
            
        Returns:
            date: 上一个交易日
        """
        if isinstance(date_obj, str):
            date_obj = pd.to_datetime(date_obj).date()
        elif isinstance(date_obj, datetime):
            date_obj = date_obj.date()
        
        prev_date = date_obj - timedelta(days=1)
        while not DateUtils.is_trading_day(prev_date):
            prev_date -= timedelta(days=1)
        
        return prev_date


class DataUtils:
    """数据处理工具类"""
    
    @staticmethod
    def validate_price_data(df: pd.DataFrame) -> bool:
        """
        验证价格数据的有效性
        
        Args:
            df (pd.DataFrame): 价格数据
            
        Returns:
            bool: 数据是否有效
        """
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        
        # 检查必需列
        if not all(col in df.columns for col in required_columns):
            return False
        
        # 检查数据类型
        for col in required_columns:
            if not pd.api.types.is_numeric_dtype(df[col]):
                return False
        
        # 检查价格逻辑
        invalid_rows = (
            (df['high'] < df['low']) |
            (df['high'] < df['open']) |
            (df['high'] < df['close']) |
            (df['low'] > df['open']) |
            (df['low'] > df['close']) |
            (df['volume'] < 0)
        )
        
        return not invalid_rows.any()
    
    @staticmethod
    def clean_price_data(df: pd.DataFrame) -> pd.DataFrame:
        """
        清理价格数据
        
        Args:
            df (pd.DataFrame): 原始价格数据
            
        Returns:
            pd.DataFrame: 清理后的价格数据
        """
        df_clean = df.copy()
        
        # 删除空值行
        df_clean = df_clean.dropna()
        
        # 修正价格逻辑错误
        # 如果high < low，交换它们
        swap_mask = df_clean['high'] < df_clean['low']
        df_clean.loc[swap_mask, ['high', 'low']] = df_clean.loc[swap_mask, ['low', 'high']].values
        
        # 确保high是最高价
        df_clean['high'] = df_clean[['high', 'open', 'close']].max(axis=1)
        
        # 确保low是最低价
        df_clean['low'] = df_clean[['low', 'open', 'close']].min(axis=1)
        
        # 删除成交量为负的行
        df_clean = df_clean[df_clean['volume'] >= 0]
        
        # 删除价格为0或负数的行
        price_cols = ['open', 'high', 'low', 'close']
        for col in price_cols:
            df_clean = df_clean[df_clean[col] > 0]
        
        return df_clean
    
    @staticmethod
    def resample_data(df: pd.DataFrame, freq: str) -> pd.DataFrame:
        """
        重采样数据到指定频率
        
        Args:
            df (pd.DataFrame): 原始数据
            freq (str): 目标频率 ('D', 'W', 'M'等)
            
        Returns:
            pd.DataFrame: 重采样后的数据
        """
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("数据索引必须是DatetimeIndex")
        
        # 定义聚合规则
        agg_rules = {
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }
        
        # 只对存在的列进行聚合
        available_rules = {k: v for k, v in agg_rules.items() if k in df.columns}
        
        return df.resample(freq).agg(available_rules).dropna()
    
    @staticmethod
    def calculate_returns(prices: pd.Series, method: str = 'simple') -> pd.Series:
        """
        计算收益率
        
        Args:
            prices (pd.Series): 价格序列
            method (str): 计算方法 ('simple' 或 'log')
            
        Returns:
            pd.Series: 收益率序列
        """
        if method == 'simple':
            return prices.pct_change()
        elif method == 'log':
            return np.log(prices / prices.shift(1))
        else:
            raise ValueError("method必须是'simple'或'log'")
    
    @staticmethod
    def align_data(*dataframes: pd.DataFrame) -> List[pd.DataFrame]:
        """
        对齐多个数据框的索引
        
        Args:
            *dataframes: 要对齐的数据框
            
        Returns:
            List[pd.DataFrame]: 对齐后的数据框列表
        """
        if len(dataframes) < 2:
            return list(dataframes)
        
        # 找到共同的索引
        common_index = dataframes[0].index
        for df in dataframes[1:]:
            common_index = common_index.intersection(df.index)
        
        # 对齐所有数据框
        aligned_dfs = []
        for df in dataframes:
            aligned_dfs.append(df.loc[common_index].sort_index())
        
        return aligned_dfs


class RiskUtils:
    """风险管理工具类"""
    
    @staticmethod
    def calculate_position_size(account_value: float, risk_per_trade: float, 
                              entry_price: float, stop_loss_price: float) -> int:
        """
        根据风险管理原则计算仓位大小
        
        Args:
            account_value (float): 账户总价值
            risk_per_trade (float): 每笔交易的风险比例
            entry_price (float): 入场价格
            stop_loss_price (float): 止损价格
            
        Returns:
            int: 建议的股票数量
        """
        if stop_loss_price <= 0 or entry_price <= 0:
            return 0
        
        # 计算每股风险
        risk_per_share = abs(entry_price - stop_loss_price)
        
        if risk_per_share == 0:
            return 0
        
        # 计算总风险金额
        total_risk = account_value * risk_per_trade
        
        # 计算股票数量
        shares = int(total_risk / risk_per_share)
        
        # 确保不超过账户价值
        max_shares = int(account_value / entry_price)
        
        return min(shares, max_shares)
    
    @staticmethod
    def calculate_kelly_criterion(win_rate: float, avg_win: float, avg_loss: float) -> float:
        """
        计算凯利公式建议的仓位比例
        
        Args:
            win_rate (float): 胜率
            avg_win (float): 平均盈利
            avg_loss (float): 平均亏损
            
        Returns:
            float: 建议的仓位比例
        """
        if avg_loss == 0 or win_rate <= 0 or win_rate >= 1:
            return 0.0
        
        # 凯利公式: f = (bp - q) / b
        # 其中 b = avg_win / avg_loss, p = win_rate, q = 1 - win_rate
        b = avg_win / abs(avg_loss)
        p = win_rate
        q = 1 - win_rate
        
        kelly_fraction = (b * p - q) / b
        
        # 限制在合理范围内
        return max(0.0, min(kelly_fraction, 0.25))  # 最大25%
    
    @staticmethod
    def calculate_var(returns: pd.Series, confidence_level: float = 0.95) -> float:
        """
        计算风险价值(VaR)
        
        Args:
            returns (pd.Series): 收益率序列
            confidence_level (float): 置信水平
            
        Returns:
            float: VaR值
        """
        if len(returns) == 0:
            return 0.0
        
        return np.percentile(returns.dropna(), (1 - confidence_level) * 100)
    
    @staticmethod
    def calculate_cvar(returns: pd.Series, confidence_level: float = 0.95) -> float:
        """
        计算条件风险价值(CVaR)
        
        Args:
            returns (pd.Series): 收益率序列
            confidence_level (float): 置信水平
            
        Returns:
            float: CVaR值
        """
        if len(returns) == 0:
            return 0.0
        
        var = RiskUtils.calculate_var(returns, confidence_level)
        return returns[returns <= var].mean()


class PerformanceUtils:
    """绩效计算工具类"""
    
    @staticmethod
    def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.03) -> float:
        """
        计算夏普比率
        
        Args:
            returns (pd.Series): 收益率序列
            risk_free_rate (float): 无风险利率
            
        Returns:
            float: 夏普比率
        """
        if len(returns) == 0 or returns.std() == 0:
            return 0.0
        
        excess_returns = returns - risk_free_rate / 252  # 日化无风险利率
        return excess_returns.mean() / returns.std() * np.sqrt(252)
    
    @staticmethod
    def calculate_sortino_ratio(returns: pd.Series, risk_free_rate: float = 0.03) -> float:
        """
        计算索提诺比率
        
        Args:
            returns (pd.Series): 收益率序列
            risk_free_rate (float): 无风险利率
            
        Returns:
            float: 索提诺比率
        """
        if len(returns) == 0:
            return 0.0
        
        excess_returns = returns - risk_free_rate / 252
        downside_returns = excess_returns[excess_returns < 0]
        
        if len(downside_returns) == 0 or downside_returns.std() == 0:
            return 0.0
        
        return excess_returns.mean() / downside_returns.std() * np.sqrt(252)
    
    @staticmethod
    def calculate_max_drawdown(cumulative_returns: pd.Series) -> Tuple[float, pd.Timestamp, pd.Timestamp]:
        """
        计算最大回撤
        
        Args:
            cumulative_returns (pd.Series): 累计收益率序列
            
        Returns:
            Tuple[float, pd.Timestamp, pd.Timestamp]: (最大回撤, 开始日期, 结束日期)
        """
        if len(cumulative_returns) == 0:
            return 0.0, None, None
        
        # 计算累计最大值
        cumulative_max = cumulative_returns.expanding().max()
        
        # 计算回撤
        drawdown = (cumulative_returns - cumulative_max) / cumulative_max
        
        # 找到最大回撤
        max_dd = drawdown.min()
        max_dd_end = drawdown.idxmin()
        
        # 找到最大回撤开始点
        max_dd_start = cumulative_returns.loc[:max_dd_end].idxmax()
        
        return max_dd, max_dd_start, max_dd_end
    
    @staticmethod
    def calculate_calmar_ratio(annual_return: float, max_drawdown: float) -> float:
        """
        计算卡玛比率
        
        Args:
            annual_return (float): 年化收益率
            max_drawdown (float): 最大回撤
            
        Returns:
            float: 卡玛比率
        """
        if max_drawdown == 0:
            return 0.0
        
        return annual_return / abs(max_drawdown)


class ValidationUtils:
    """数据验证工具类"""
    
    @staticmethod
    def validate_backtest_params(params: Dict[str, Any]) -> Tuple[bool, str]:
        """
        验证回测参数
        
        Args:
            params (Dict[str, Any]): 回测参数
            
        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        required_params = ['start_date', 'end_date', 'initial_capital']
        
        # 检查必需参数
        for param in required_params:
            if param not in params:
                return False, f"缺少必需参数: {param}"
        
        # 验证日期
        try:
            start_date = pd.to_datetime(params['start_date'])
            end_date = pd.to_datetime(params['end_date'])
            
            if start_date >= end_date:
                return False, "开始日期必须早于结束日期"
                
        except Exception as e:
            return False, f"日期格式错误: {e}"
        
        # 验证初始资金
        if params['initial_capital'] <= 0:
            return False, "初始资金必须大于0"
        
        # 验证可选参数
        if 'commission' in params and params['commission'] < 0:
            return False, "手续费不能为负数"
        
        if 'slippage' in params and params['slippage'] < 0:
            return False, "滑点不能为负数"
        
        return True, ""
    
    @staticmethod
    def validate_signal_data(signals: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        验证交易信号数据
        
        Args:
            signals (List[Dict[str, Any]]): 交易信号列表
            
        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        if not signals:
            return False, "交易信号列表为空"
        
        required_fields = ['date', 'stock_code', 'action', 'price']
        
        for i, signal in enumerate(signals):
            # 检查必需字段
            for field in required_fields:
                if field not in signal:
                    return False, f"信号{i}缺少必需字段: {field}"
            
            # 验证动作
            if signal['action'] not in ['buy', 'sell']:
                return False, f"信号{i}的动作必须是'buy'或'sell'"
            
            # 验证价格
            if signal['price'] <= 0:
                return False, f"信号{i}的价格必须大于0"
            
            # 验证日期
            try:
                pd.to_datetime(signal['date'])
            except Exception:
                return False, f"信号{i}的日期格式错误"
        
        return True, ""


class FileUtils:
    """文件处理工具类"""
    
    @staticmethod
    def ensure_dir(path: Union[str, Path]) -> Path:
        """
        确保目录存在
        
        Args:
            path (Union[str, Path]): 目录路径
            
        Returns:
            Path: 目录路径对象
        """
        path_obj = Path(path)
        path_obj.mkdir(parents=True, exist_ok=True)
        return path_obj
    
    @staticmethod
    def save_results(results: Dict[str, Any], filepath: Union[str, Path]) -> bool:
        """
        保存回测结果
        
        Args:
            results (Dict[str, Any]): 回测结果
            filepath (Union[str, Path]): 保存路径
            
        Returns:
            bool: 是否保存成功
        """
        try:
            filepath = Path(filepath)
            
            # 确保目录存在
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            # 根据文件扩展名选择保存格式
            if filepath.suffix.lower() == '.json':
                import json
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(results, f, ensure_ascii=False, indent=2, default=str)
            
            elif filepath.suffix.lower() == '.pkl':
                import pickle
                with open(filepath, 'wb') as f:
                    pickle.dump(results, f)
            
            else:
                # 默认使用JSON格式
                import json
                with open(filepath.with_suffix('.json'), 'w', encoding='utf-8') as f:
                    json.dump(results, f, ensure_ascii=False, indent=2, default=str)
            
            return True
            
        except Exception as e:
            logging.error(f"保存结果失败: {e}")
            return False
    
    @staticmethod
    def load_results(filepath: Union[str, Path]) -> Optional[Dict[str, Any]]:
        """
        加载回测结果
        
        Args:
            filepath (Union[str, Path]): 文件路径
            
        Returns:
            Optional[Dict[str, Any]]: 回测结果，失败时返回None
        """
        try:
            filepath = Path(filepath)
            
            if not filepath.exists():
                return None
            
            # 根据文件扩展名选择加载格式
            if filepath.suffix.lower() == '.json':
                import json
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            elif filepath.suffix.lower() == '.pkl':
                import pickle
                with open(filepath, 'rb') as f:
                    return pickle.load(f)
            
            else:
                return None
                
        except Exception as e:
            logging.error(f"加载结果失败: {e}")
            return None


class LogUtils:
    """日志工具类"""
    
    @staticmethod
    def setup_backtest_logger(name: str, log_file: Optional[str] = None) -> logging.Logger:
        """
        设置回测专用日志记录器
        
        Args:
            name (str): 日志记录器名称
            log_file (str, optional): 日志文件路径
            
        Returns:
            logging.Logger: 日志记录器
        """
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        
        # 避免重复添加处理器
        if logger.handlers:
            return logger
        
        # 创建格式器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # 文件处理器（如果指定了文件路径）
        if log_file:
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        return logger