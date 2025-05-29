#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
定义策略基类和接口
"""

from abc import ABC, abstractmethod
import pandas as pd

class StrategyBase(ABC):
    """策略基类"""

    def __init__(self, name: str):
        """
        初始化策略

        Args:
            name (str): 策略名称
        """
        self._name = name

    @property
    def name(self) -> str:
        """获取策略名称"""
        return self._name

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        生成交易信号

        Args:
            data (pd.DataFrame): 输入的行情数据，至少应包含 '日期', '股票代码', '开盘', '收盘', '最高', '最低', '成交量' 等列。
                                 具体需要的列取决于策略本身。

        Returns:
            pd.DataFrame: 包含交易信号的DataFrame。该DataFrame应至少包含以下列：
                          - '日期' (datetime): 信号产生的日期。
                          - '股票代码' (str): 信号对应的股票代码。
                          - '信号类型' (str): 交易信号的类型，例如 '买入', '卖出', '持仓'。
                          - '信号价格' (float, optional): 触发信号时的价格，例如买入价或卖出价。
                          - '信号强度' (float, optional): 信号的强度或置信度 (0到1之间)。
                          - '备注' (str, optional): 与信号相关的其他备注信息。
        """
        pass

    def __repr__(self):
        return f"Strategy(name='{self.name}')"

    def __str__(self):
        return self.name