# 回测模块 (Backtest Module)

## 概述

本模块提供了一个通用的股票策略回测框架，支持多种策略类型、数据源和分析功能。该框架基于现有的策略管理系统，扩展了 `backtrader` 库的功能，提供了更灵活和强大的回测能力。

## 主要特性

### 🚀 核心功能
- **通用策略支持**: 兼容现有的策略框架，支持Python策略和JSON策略
- **多数据源**: 支持数据库数据和AKShare实时数据
- **灵活配置**: 可配置的手续费、滑点、风险管理参数
- **实时监控**: 回测过程中的实时状态监控和日志记录

### 📊 分析功能
- **绩效指标**: 50+种绩效和风险指标计算
- **风险管理**: VaR、CVaR、最大回撤等风险度量
- **交易分析**: 详细的交易记录和统计分析
- **基准比较**: 与市场基准的对比分析

### 📈 可视化
- **图表生成**: 自动生成多种分析图表
- **HTML报告**: 生成美观的综合分析报告
- **交互式图表**: 支持交互式数据探索

## 模块结构

```
core/backtest/
├── __init__.py              # 模块初始化和公共接口
├── README.md               # 本文档
├── backtest_engine.py      # 核心回测引擎
├── data_processor.py       # 数据处理器
├── portfolio_manager.py    # 投资组合管理器
├── order_executor.py       # 订单执行器
├── performance_analyzer.py # 绩效分析器
├── visualizer.py          # 结果可视化器
├── utils.py               # 工具函数集合
└── examples/              # 示例代码
```

## 核心组件

### 1. BacktestEngine (回测引擎)

核心回测引擎，负责协调各个组件完成回测流程。

**主要功能:**
- 策略执行和信号处理
- 数据管理和同步
- 回测流程控制
- 结果收集和分析

### 2. DataProcessor (数据处理器)

负责处理回测所需的各种数据源。

**支持的数据类型:**
- 股票行情数据 (OHLCV)
- 技术指标数据
- 财务数据
- 基准指数数据

**数据源:**
- 本地数据库
- AKShare API
- 缓存机制

### 3. PortfolioManager (投资组合管理器)

管理回测过程中的资金、持仓和风险控制。

**功能特性:**
- 资金管理
- 持仓跟踪
- 风险控制
- 仓位管理

### 4. OrderExecutor (订单执行器)

处理交易订单的执行，包括滑点和手续费计算。

**执行模型:**
- 市价执行
- 限价执行
- 收盘价执行

**成本模型:**
- 固定滑点/手续费
- 基于成交量的动态模型
- 买卖价差模型

### 5. PerformanceAnalyzer (绩效分析器)

计算各种绩效和风险指标。

**指标类别:**
- 收益指标: 总收益率、年化收益率、超额收益等
- 风险指标: 波动率、VaR、CVaR、最大回撤等
- 风险调整收益: 夏普比率、索提诺比率、卡玛比率等
- 交易指标: 胜率、盈亏比、交易频率等

### 6. BacktestVisualizer (可视化器)

生成各种图表和报告。

**图表类型:**
- 投资组合价值曲线
- 收益率分布
- 回撤曲线
- 交易分析图
- 月度收益热力图
- 风险指标雷达图

## 快速开始

### 基本使用

```python
from core.backtest import create_backtest_engine, create_visualizer
from core.strategy.strategy_manager import StrategyManager

# 1. 创建回测引擎
engine = create_backtest_engine({
    'initial_capital': 1000000,  # 初始资金
    'commission': 0.0003,        # 手续费
    'slippage': 0.001           # 滑点
})

# 2. 加载策略
strategy_manager = StrategyManager()
strategy = strategy_manager.get_strategy('ma_crossover')  # 示例策略

# 3. 运行回测
results = engine.run_backtest(
    strategy=strategy,
    start_date='2023-01-01',
    end_date='2023-12-31',
    stock_codes=['000001.SZ', '000002.SZ']
)

# 4. 生成报告
visualizer = create_visualizer()
report_path = visualizer.create_comprehensive_report(
    portfolio_values=results['portfolio_values'],
    trades=results['trades'],
    metrics=results['metrics']
)

print(f"回测报告已生成: {report_path}")
```

### 高级配置

```python
from core.backtest import (
    BacktestEngine, PortfolioManager, OrderExecutor,
    FixedCommissionModel, VolumeBasedSlippageModel
)

# 自定义配置
config = {
    'initial_capital': 5000000,
    'max_position_size': 0.05,  # 单股最大仓位5%
    'max_positions': 20,        # 最大持仓数量
    'risk_free_rate': 0.025     # 无风险利率2.5%
}

# 创建自定义组件
portfolio_manager = PortfolioManager(
    initial_capital=config['initial_capital'],
    max_position_size=config['max_position_size'],
    max_positions=config['max_positions']
)

order_executor = OrderExecutor(
    commission_model=FixedCommissionModel(0.0003),
    slippage_model=VolumeBasedSlippageModel(0.001, 0.1)
)

# 创建引擎
engine = BacktestEngine(
    portfolio_manager=portfolio_manager,
    order_executor=order_executor
)
```

## 策略集成

### 使用现有策略

```python
from core.strategy.strategy_manager import StrategyManager

# 加载策略管理器
strategy_manager = StrategyManager()

# 获取可用策略列表
available_strategies = strategy_manager.list_strategies()
print("可用策略:", available_strategies)

# 加载特定策略
strategy = strategy_manager.get_strategy('your_strategy_name')

# 运行回测
results = engine.run_backtest(
    strategy=strategy,
    start_date='2023-01-01',
    end_date='2023-12-31'
)
```

### 自定义策略适配

```python
from core.backtest import StrategyAdapter
from core.strategy.strategy_base import StrategyBase

class CustomStrategy(StrategyBase):
    def generate_signals(self, data):
        # 自定义信号生成逻辑
        signals = []
        # ... 策略逻辑 ...
        return signals

# 创建策略适配器
strategy = CustomStrategy()
adapter = StrategyAdapter(strategy)

# 在backtrader中使用
engine.cerebro.addstrategy(adapter)
```

## 数据管理

### 数据源配置

```python
from core.backtest import DataProcessor

# 创建数据处理器
data_processor = DataProcessor()

# 配置数据源优先级
data_processor.set_data_source_priority([
    'database',  # 优先使用数据库
    'akshare'    # 备用AKShare
])

# 预加载数据
data_processor.preload_data(
    stock_codes=['000001.SZ', '000002.SZ'],
    start_date='2023-01-01',
    end_date='2023-12-31'
)
```

### 自定义数据源

```python
from core.backtest import AKShareDataFeed
import backtrader as bt

# 创建数据源
data_feed = AKShareDataFeed(
    stock_code='000001.SZ',
    start_date='2023-01-01',
    end_date='2023-12-31'
)

# 添加到回测引擎
engine.cerebro.adddata(data_feed)
```

## 绩效分析

### 基本指标计算

```python
from core.backtest import PerformanceAnalyzer

# 创建分析器
analyzer = PerformanceAnalyzer()

# 计算绩效指标
metrics = analyzer.calculate_metrics(
    portfolio_values=results['portfolio_values'],
    trades=results['trades'],
    benchmark_values=results.get('benchmark_values')
)

# 打印关键指标
print(f"总收益率: {metrics.total_return:.2%}")
print(f"年化收益率: {metrics.annual_return:.2%}")
print(f"最大回撤: {metrics.max_drawdown:.2%}")
print(f"夏普比率: {metrics.sharpe_ratio:.4f}")
print(f"胜率: {metrics.win_rate:.2%}")
```

### 风险分析

```python
# 计算风险指标
risk_metrics = {
    'VaR_95': metrics.var_95,
    'CVaR_95': metrics.cvar_95,
    '波动率': metrics.volatility,
    '下行波动率': metrics.downside_volatility
}

for metric, value in risk_metrics.items():
    print(f"{metric}: {value:.4f}")
```

## 结果可视化

### 生成图表

```python
from core.backtest import BacktestVisualizer

# 创建可视化器
visualizer = BacktestVisualizer(output_dir='my_backtest_results')

# 生成单个图表
visualizer.plot_portfolio_value(results['portfolio_values'])
visualizer.plot_returns(results['portfolio_values'])
visualizer.plot_drawdown(results['portfolio_values'])
visualizer.plot_trade_analysis(results['trades'])

# 生成综合报告
report_path = visualizer.create_comprehensive_report(
    portfolio_values=results['portfolio_values'],
    trades=results['trades'],
    metrics=results['metrics']
)
```

### 自定义图表

```python
import matplotlib.pyplot as plt

# 自定义绘图
fig, ax = plt.subplots(figsize=(12, 8))

# 绘制自定义内容
# ... 绘图代码 ...

# 保存图表
visualizer.output_dir.mkdir(exist_ok=True)
fig.savefig(visualizer.output_dir / 'custom_chart.png', dpi=300)
```

## 配置参数

### 默认配置

```python
DEFAULT_CONFIG = {
    'initial_capital': 1000000,  # 初始资金
    'commission': 0.0003,        # 手续费率
    'slippage': 0.001,          # 滑点率
    'risk_free_rate': 0.03,     # 无风险利率
    'benchmark': '000300.SH',   # 基准指数
    'max_position_size': 0.1,   # 单股最大仓位
    'max_positions': 10,        # 最大持仓数量
}
```

### 风险管理参数

```python
risk_config = {
    'max_drawdown_limit': 0.2,    # 最大回撤限制
    'position_size_method': 'fixed',  # 仓位计算方法
    'stop_loss_pct': 0.1,         # 止损比例
    'take_profit_pct': 0.2,       # 止盈比例
    'max_holding_days': 30        # 最大持仓天数
}
```

## 性能优化

### 数据缓存

```python
# 启用数据缓存
data_processor = DataProcessor(cache_enabled=True)

# 预加载常用数据
data_processor.preload_data(
    stock_codes=['000001.SZ', '000002.SZ'],
    start_date='2020-01-01',
    end_date='2023-12-31'
)
```

### 并行处理

```python
# 多股票并行回测
from concurrent.futures import ProcessPoolExecutor

def run_single_stock_backtest(stock_code):
    # 单股票回测逻辑
    return results

# 并行执行
stock_codes = ['000001.SZ', '000002.SZ', '000858.SZ']
with ProcessPoolExecutor() as executor:
    results = list(executor.map(run_single_stock_backtest, stock_codes))
```

## 常见问题

### Q: 如何处理停牌股票？
A: 系统会自动跳过停牌期间的交易信号，持仓保持不变。

### Q: 如何设置复权处理？
A: 在数据处理器中设置 `adjust='qfq'` 进行前复权处理。

### Q: 如何添加自定义指标？
A: 继承 `PerformanceAnalyzer` 类并重写相关方法。

### Q: 如何处理分红派息？
A: 使用前复权数据可以自动处理分红派息的影响。

## 扩展开发

### 自定义滑点模型

```python
from core.backtest.order_executor import SlippageModel

class CustomSlippageModel(SlippageModel):
    def calculate_slippage(self, order_info):
        # 自定义滑点计算逻辑
        return slippage_amount
```

### 自定义绩效指标

```python
from core.backtest.performance_analyzer import PerformanceAnalyzer

class CustomPerformanceAnalyzer(PerformanceAnalyzer):
    def calculate_custom_metric(self, data):
        # 自定义指标计算
        return metric_value
```

## 版本历史

- **v1.0.0** (2024-01-01)
  - 初始版本发布
  - 基础回测功能
  - 策略集成支持
  - 绩效分析和可视化

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 许可证

本项目采用 MIT 许可证。详见 LICENSE 文件。

## 联系方式

如有问题或建议，请通过以下方式联系：
- 项目Issues: [GitHub Issues]()
- 邮箱: [team@example.com]()

---

**注意**: 本回测框架仅用于研究和教育目的，不构成投资建议。实际投资请谨慎决策。