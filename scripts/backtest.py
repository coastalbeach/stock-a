# -*- coding: utf-8 -*-
"""
回测脚本

提供基于Backtrader的回测功能，支持对策略进行历史数据回测、性能评估和结果可视化
"""

import os
import sys
import pandas as pd
import numpy as np
import datetime
import logging
import matplotlib.pyplot as plt
import backtrader as bt
import yaml
import argparse
from typing import Dict, List, Any, Optional, Union, Tuple

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入策略模块
from core.strategy.strategy_factory import strategy_factory
from utils.logger import LoggerManager
from utils.config_loader import load_config

# 获取日志记录器
logger_manager = LoggerManager()
logger = logger_manager.get_logger('backtest')


class AKShareData(bt.feeds.PandasData):
    """
    AKShare数据源适配器
    
    将从AKShare获取的数据转换为Backtrader可用的格式
    """
    # 列名映射，将中文列名映射到Backtrader需要的英文列名
    # 注意：保持中文列名不变，只在内部做映射
    params = (
        ('datetime', None),  # 使用索引作为日期
        ('open', '开盘价'),
        ('high', '最高价'),
        ('low', '最低价'),
        ('close', '收盘价'),
        ('volume', '成交量'),
        ('openinterest', None),  # A股没有未平仓量
    )


class StrategyAdapter(bt.Strategy):
    """
    策略适配器
    
    将项目中的策略适配到Backtrader框架
    """
    params = (
        ('strategy_name', ''),  # 策略名称
        ('strategy_params', {}),  # 策略参数
    )
    
    def __init__(self):
        """
        初始化策略适配器
        """
        self.logger = logging.getLogger(f"backtest.{self.p.strategy_name}")
        self.logger.info(f"初始化策略: {self.p.strategy_name}, 参数: {self.p.strategy_params}")
        
        # 创建原始策略实例
        self.strategy = strategy_factory.create_strategy(
            self.p.strategy_name, 
            self.p.strategy_params
        )
        
        # 保存数据，用于生成信号
        self.data_dict = {}
        
        # 交易记录
        self.trades = []
        
        # 订单状态跟踪
        self.order = None
    
    def next(self):
        """
        策略核心逻辑，每个bar执行一次
        """
        # 如果有未完成的订单，不执行新的交易
        if self.order:
            return
        
        # 准备数据
        self._prepare_data()
        
        # 生成信号
        signals = self.strategy.generate_signals(pd.DataFrame(self.data_dict))
        
        # 获取当前日期的信号
        current_date = self.data.datetime.date()
        current_signal = signals.iloc[-1]['信号'] if '信号' in signals.columns else 0
        
        # 根据信号执行交易
        if current_signal > 0:  # 买入信号
            self.logger.info(f"{current_date}: 买入信号")
            # 计算买入数量（按资金比例）
            size = self.broker.getcash() * 0.95 / self.data.close[0]  # 使用95%的可用资金
            size = int(size / 100) * 100  # 取整百
            
            if size > 0:
                self.logger.info(f"买入 {size} 股，价格 {self.data.close[0]}")
                self.order = self.buy(size=size)
                
                # 记录交易
                self.trades.append({
                    '日期': current_date.strftime('%Y-%m-%d'),
                    '操作': '买入',
                    '价格': self.data.close[0],
                    '数量': size,
                    '资金': self.broker.getcash(),
                    '总资产': self.broker.getvalue()
                })
        
        elif current_signal < 0:  # 卖出信号
            self.logger.info(f"{current_date}: 卖出信号")
            # 如果有持仓，全部卖出
            if self.position.size > 0:
                self.logger.info(f"卖出 {self.position.size} 股，价格 {self.data.close[0]}")
                self.order = self.sell(size=self.position.size)
                
                # 记录交易
                self.trades.append({
                    '日期': current_date.strftime('%Y-%m-%d'),
                    '操作': '卖出',
                    '价格': self.data.close[0],
                    '数量': self.position.size,
                    '资金': self.broker.getcash(),
                    '总资产': self.broker.getvalue()
                })
    
    def _prepare_data(self):
        """
        准备策略所需的数据
        """
        # 收集当前数据点的所有数据
        for i in range(len(self.data)):
            if i not in self.data_dict:
                self.data_dict[i] = {}
            
            # 添加OHLCV数据
            self.data_dict[i]['日期'] = self.data.datetime.date(i)
            self.data_dict[i]['开盘价'] = self.data.open[i]
            self.data_dict[i]['最高价'] = self.data.high[i]
            self.data_dict[i]['最低价'] = self.data.low[i]
            self.data_dict[i]['收盘价'] = self.data.close[i]
            self.data_dict[i]['成交量'] = self.data.volume[i]
    
    def notify_order(self, order):
        """
        订单状态更新通知
        """
        if order.status in [order.Submitted, order.Accepted]:
            # 订单已提交或已接受，等待执行
            return
        
        # 检查订单是否已完成
        if order.status in [order.Completed]:
            if order.isbuy():
                self.logger.info(f"买入执行: 价格 {order.executed.price}, 数量 {order.executed.size}, 成本 {order.executed.value}, 手续费 {order.executed.comm}")
            else:
                self.logger.info(f"卖出执行: 价格 {order.executed.price}, 数量 {order.executed.size}, 成本 {order.executed.value}, 手续费 {order.executed.comm}")
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.logger.warning(f"订单未完成: {order.status}")
        
        # 重置订单
        self.order = None


class BacktestEngine:
    """
    回测引擎
    
    提供回测功能，包括数据准备、回测执行、结果分析和可视化
    """
    
    def __init__(self, config_path=None):
        """
        初始化回测引擎
        
        Args:
            config_path: 配置文件路径，默认为None，使用默认配置
        """
        self.logger = logging.getLogger("backtest.engine")
        
        # 加载配置
        self.config = {}
        if config_path:
            self.config = load_config(config_path)
        
        # 初始化Backtrader引擎
        self.cerebro = bt.Cerebro()
        
        # 设置初始资金
        self.cerebro.broker.setcash(self.config.get('初始资金', 100000.0))
        
        # 设置手续费
        self.cerebro.broker.setcommission(commission=self.config.get('手续费', 0.0003))
        
        # 设置滑点
        self.cerebro.broker.set_slippage_perc(self.config.get('滑点', 0.0))
    
    def add_data(self, data, name=None):
        """
        添加数据源
        
        Args:
            data: 数据源，可以是pandas.DataFrame或bt.feeds.DataBase对象
            name: 数据名称，默认为None
        """
        if isinstance(data, pd.DataFrame):
            # 确保索引是日期类型
            if not isinstance(data.index, pd.DatetimeIndex):
                if '日期' in data.columns:
                    data = data.set_index('日期')
                    data.index = pd.to_datetime(data.index)
                else:
                    raise ValueError("数据必须包含'日期'列或已设置日期索引")
            
            # 创建AKShareData数据源
            data_feed = AKShareData(
                dataname=data,
                name=name,
                fromdate=pd.to_datetime(self.config.get('开始日期')),
                todate=pd.to_datetime(self.config.get('结束日期'))
            )
            
            self.cerebro.adddata(data_feed, name=name)
            self.logger.info(f"添加数据源: {name}, 数据范围: {data.index.min()} - {data.index.max()}")
        elif isinstance(data, bt.feeds.DataBase):
            self.cerebro.adddata(data, name=name)
            self.logger.info(f"添加数据源: {name}")
        else:
            raise TypeError("数据必须是pandas.DataFrame或bt.feeds.DataBase对象")
    
    def add_strategy(self, strategy_name, strategy_params=None):
        """
        添加策略
        
        Args:
            strategy_name: 策略名称
            strategy_params: 策略参数，默认为None
        """
        if strategy_params is None:
            strategy_params = {}
        
        # 添加策略适配器
        self.cerebro.addstrategy(
            StrategyAdapter,
            strategy_name=strategy_name,
            strategy_params=strategy_params
        )
        
        self.logger.info(f"添加策略: {strategy_name}, 参数: {strategy_params}")
    
    def add_analyzer(self):
        """
        添加分析器
        """
        # 添加常用分析器
        self.cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        self.cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        self.cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        self.cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        
        self.logger.info("添加分析器: SharpeRatio, DrawDown, Returns, TradeAnalyzer")
    
    def run(self):
        """
        运行回测
        
        Returns:
            回测结果
        """
        self.logger.info("开始回测...")
        results = self.cerebro.run()
        self.logger.info("回测完成")
        
        return results
    
    def plot(self, results, filename=None):
        """
        绘制回测结果
        
        Args:
            results: 回测结果
            filename: 保存文件名，默认为None，不保存
        """
        self.logger.info("绘制回测结果...")
        
        # 设置绘图样式
        plt.style.use('seaborn-darkgrid')
        
        # 绘制回测结果
        fig = self.cerebro.plot(
            results[0],
            style='candle',
            barup='red',  # 阳线为红色
            bardown='green',  # 阴线为绿色
            volup='red',
            voldown='green',
            grid=True,
            returnfig=True
        )
        
        # 保存图表
        if filename:
            fig[0][0].savefig(filename)
            self.logger.info(f"回测结果图表已保存到: {filename}")
        
        return fig
    
    def analyze_results(self, results):
        """
        分析回测结果
        
        Args:
            results: 回测结果
            
        Returns:
            分析结果字典
        """
        self.logger.info("分析回测结果...")
        
        # 获取第一个策略的结果
        strat = results[0]
        
        # 获取分析器结果
        sharpe_ratio = strat.analyzers.sharpe.get_analysis()['sharperatio']
        drawdown = strat.analyzers.drawdown.get_analysis()
        returns = strat.analyzers.returns.get_analysis()
        trades = strat.analyzers.trades.get_analysis()
        
        # 计算交易胜率
        if trades.get('total', 0) > 0:
            win_rate = trades.get('won', 0) / trades.get('total', 0)
        else:
            win_rate = 0.0
        
        # 整理分析结果
        analysis = {
            '初始资金': self.cerebro.broker.startingcash,
            '最终资金': self.cerebro.broker.getvalue(),
            '总收益率': (self.cerebro.broker.getvalue() / self.cerebro.broker.startingcash) - 1.0,
            '年化收益率': returns.get('ravg', 0.0) * 252,  # 假设一年252个交易日
            '最大回撤': drawdown.get('max', {}).get('drawdown', 0.0),
            'Sharpe比率': sharpe_ratio,
            '交易次数': trades.get('total', 0),
            '胜率': win_rate,
            '交易记录': strat.trades if hasattr(strat, 'trades') else []
        }
        
        return analysis
    
    def print_analysis(self, analysis):
        """
        打印分析结果
        
        Args:
            analysis: 分析结果字典
        """
        print("\n回测结果分析:")
        print(f"初始资金: {analysis['初始资金']:.2f}")
        print(f"最终资金: {analysis['最终资金']:.2f}")
        print(f"总收益率: {analysis['总收益率']*100:.2f}%")
        print(f"年化收益率: {analysis['年化收益率']*100:.2f}%")
        print(f"最大回撤: {analysis['最大回撤']*100:.2f}%")
        print(f"Sharpe比率: {analysis['Sharpe比率']:.2f}")
        print(f"交易次数: {analysis['交易次数']}")
        print(f"胜率: {analysis['胜率']*100:.2f}%")
        
        # 显示交易记录
        if analysis['交易记录']:
            print("\n交易记录:")
            for i, trade in enumerate(analysis['交易记录'][:5], 1):  # 只显示前5条
                print(f"{i}. 日期: {trade['日期']}, 操作: {trade['操作']}, "
                      f"价格: {trade['价格']:.2f}, 数量: {trade['数量']}")
            if len(analysis['交易记录']) > 5:
                print(f"... 共{len(analysis['交易记录'])}条交易记录")
    
    def save_results(self, analysis, filename):
        """
        保存分析结果
        
        Args:
            analysis: 分析结果字典
            filename: 保存文件名
        """
        # 转换交易记录为DataFrame
        if analysis['交易记录']:
            trades_df = pd.DataFrame(analysis['交易记录'])
            trades_df.to_csv(f"{filename}_trades.csv", index=False, encoding='utf-8-sig')
        
        # 保存分析结果
        with open(f"{filename}_analysis.yaml", 'w', encoding='utf-8') as f:
            # 移除不可序列化的对象
            analysis_copy = analysis.copy()
            analysis_copy.pop('交易记录', None)
            yaml.dump(analysis_copy, f, allow_unicode=True)
        
        self.logger.info(f"分析结果已保存到: {filename}_analysis.yaml")
        if analysis['交易记录']:
            self.logger.info(f"交易记录已保存到: {filename}_trades.csv")


def load_stock_data(stock_code, start_date, end_date):
    """
    加载股票数据
    
    首先尝试从数据库加载，如果数据库中没有，则从AKShare获取
    
    Args:
        stock_code: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        
    Returns:
        股票数据DataFrame
    """
    logger = logging.getLogger("backtest.data")
    logger.info(f"加载股票数据: {stock_code}, {start_date} - {end_date}")
    
    try:
        # 尝试从PostgreSQL数据库加载数据
        import psycopg2
        import redis
        from psycopg2 import pool
        import pandas as pd
        
        # 创建数据库连接池
        pg_pool = psycopg2.pool.SimpleConnectionPool(
            1, 10,
            host="localhost",
            database="stock_a",
            user="postgres",
            password="postgres",
            port="5432"
        )
        
        # 获取连接
        conn = pg_pool.getconn()
        cursor = conn.cursor()
        
        # 查询是否有该股票的历史数据表
        cursor.execute("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = %s)", 
                      (f"股票日线_{stock_code}",))
        table_exists = cursor.fetchone()[0]
        
        if table_exists:
            # 从数据库加载数据
            query = f"""SELECT * FROM \"股票日线_{stock_code}\" 
                     WHERE \"日期\" BETWEEN %s AND %s
                     ORDER BY \"日期\" ASC"""
            cursor.execute(query, (start_date, end_date))
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()
            
            # 释放连接回连接池
            pg_pool.putconn(conn)
            
            if data:
                # 创建DataFrame
                df = pd.DataFrame(data, columns=columns)
                logger.info(f"从数据库加载了 {len(df)} 条记录")
                return df
        
        # 如果数据库中没有数据，则从AKShare获取
        import akshare as ak
        
        # 处理股票代码格式
        if stock_code.startswith('6'):
            full_code = f"{stock_code}.SH"
        else:
            full_code = f"{stock_code}.SZ"
        
        # 获取日线数据
        df = ak.stock_zh_a_hist(symbol=full_code, start_date=start_date.replace('-', ''), end_date=end_date.replace('-', ''), adjust="qfq")
        
        # 重命名列，保持中文列名
        df = df.rename(columns={
            '日期': '日期',
            '开盘': '开盘价',
            '最高': '最高价',
            '最低': '最低价',
            '收盘': '收盘价',
            '成交量': '成交量',
            '成交额': '成交额',
            '振幅': '振幅',
            '涨跌幅': '涨跌幅',
            '涨跌额': '涨跌额',
            '换手率': '换手率'
        })
        
        # 设置日期为索引
        df['日期'] = pd.to_datetime(df['日期'])
        df = df.set_index('日期')
        
        logger.info(f"成功加载股票数据: {stock_code}, 数据条数: {len(df)}")
        return df
    
    except Exception as e:
        logger.error(f"加载股票数据失败: {e}")
        return pd.DataFrame()


def run_backtest(args):
    """
    运行回测
    
    Args:
        args: 命令行参数
    """
    # 设置日志
    setup_logger()
    logger = logging.getLogger("backtest")
    
    # 创建回测引擎
    engine = BacktestEngine()
    
    # 设置回测参数
    strategy_name = args.strategy
    stock_code = args.stock
    start_date = args.start_date
    end_date = args.end_date
    initial_capital = args.capital
    
    # 准备策略参数
    strategy_params = {
        '股票代码': stock_code,
        '开始日期': start_date,
        '结束日期': end_date,
        '初始资金': initial_capital
    }
    
    # 如果提供了参数文件，加载参数
    if args.params:
        with open(args.params, 'r', encoding='utf-8') as f:
            params = yaml.safe_load(f)
            strategy_params.update(params)
    
    # 加载股票数据
    data = load_stock_data(stock_code, start_date, end_date)
    if data.empty:
        logger.error(f"无法获取股票数据: {stock_code}")
        return
    
    # 添加数据源
    engine.add_data(data, name=stock_code)
    
    # 添加策略
    engine.add_strategy(strategy_name, strategy_params)
    
    # 添加分析器
    engine.add_analyzer()
    
    # 设置初始资金
    engine.cerebro.broker.setcash(initial_capital)
    
    # 运行回测
    results = engine.run()
    
    # 分析结果
    analysis = engine.analyze_results(results)
    
    # 打印分析结果
    engine.print_analysis(analysis)
    
    # 保存结果
    if args.output:
        engine.save_results(analysis, args.output)
    
    # 绘制结果
    if args.plot:
        engine.plot(results, filename=f"{args.output}_plot.png" if args.output else None)


def list_strategies():
    """
    列出所有可用的策略
    """
    strategies = strategy_factory.get_all_strategies()
    print("\n可用策略列表:")
    for i, strategy in enumerate(strategies, 1):
        print(f"{i}. {strategy}")
    return strategies


def main():
    """
    主函数
    """
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="A股量化分析系统回测脚本")
    parser.add_argument('--list', action='store_true', help="列出所有可用的策略")
    parser.add_argument('--strategy', type=str, help="策略名称")
    parser.add_argument('--stock', type=str, help="股票代码")
    parser.add_argument('--start-date', type=str, help="开始日期，格式：YYYY-MM-DD")
    parser.add_argument('--end-date', type=str, help="结束日期，格式：YYYY-MM-DD")
    parser.add_argument('--capital', type=float, default=100000.0, help="初始资金")
    parser.add_argument('--params', type=str, help="策略参数文件路径")
    parser.add_argument('--output', type=str, help="输出结果文件名前缀")
    parser.add_argument('--plot', action='store_true', help="绘制回测结果图表")
    
    args = parser.parse_args()
    
    # 列出所有可用的策略
    if args.list:
        list_strategies()
        return
    
    # 检查必要参数
    if not args.strategy or not args.stock or not args.start_date or not args.end_date:
        print("错误: 必须提供策略名称、股票代码、开始日期和结束日期")
        parser.print_help()
        return
    
    # 运行回测
    run_backtest(args)


if __name__ == "__main__":
    main()