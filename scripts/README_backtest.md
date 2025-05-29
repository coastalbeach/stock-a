# A股量化分析系统回测模块

## 概述

回测模块是A股量化分析系统的核心组件之一，提供了对交易策略进行历史数据回测、性能评估和结果可视化的功能。本模块基于Backtrader框架实现，支持与系统中已有的策略模块无缝集成，为量化交易策略的开发和优化提供有力支持。

## 功能特性

- **策略回测**：使用历史行情数据对交易策略进行回测，模拟策略在历史市场中的表现
- **性能评估**：计算关键绩效指标，如总收益率、年化收益率、最大回撤、Sharpe比率等
- **结果可视化**：生成回测结果图表，直观展示策略的交易信号和收益曲线
- **多策略比较**：支持对多个策略在相同条件下的回测结果进行比较分析
- **参数优化**：支持对策略参数进行优化，寻找最优参数组合
- **数据适配**：自动适配AKShare数据源，支持A股市场数据的回测

## 安装依赖

回测模块依赖以下Python包：

```bash
# 安装依赖包
pip install backtrader pandas numpy matplotlib akshare pyyaml
```

或者直接使用项目根目录下的requirements.txt安装所有依赖：

```bash
pip install -r requirements.txt
```

## 使用方法

### 命令行使用

回测模块提供了命令行接口，可以直接通过命令行参数运行回测：

```bash
python scripts/backtest.py --strategy '均线交叉策略' --stock '000001' --start-date '2020-01-01' --end-date '2020-12-31' --capital 100000 --plot
```

参数说明：
- `--strategy`：策略名称，必须是系统中已注册的策略
- `--stock`：股票代码
- `--start-date`：回测开始日期，格式为YYYY-MM-DD
- `--end-date`：回测结束日期，格式为YYYY-MM-DD
- `--capital`：初始资金，默认为100000
- `--params`：策略参数文件路径，可选，用于加载自定义参数
- `--output`：输出结果文件名前缀，可选
- `--plot`：是否绘制回测结果图表，可选
- `--list`：列出所有可用的策略，可选

### 代码中使用

也可以在Python代码中使用回测模块：

```python
from scripts.backtest import BacktestEngine, load_stock_data

# 创建回测引擎
engine = BacktestEngine()

# 加载股票数据
data = load_stock_data('000001', '2020-01-01', '2020-12-31')

# 添加数据源
engine.add_data(data, name='000001')

# 准备策略参数
strategy_params = {
    '股票代码': '000001',
    '开始日期': '2020-01-01',
    '结束日期': '2020-12-31',
    '初始资金': 100000.0,
    '短期均线': 5,
    '长期均线': 20
}

# 添加策略
engine.add_strategy('均线交叉策略', strategy_params)

# 添加分析器
engine.add_analyzer()

# 运行回测
results = engine.run()

# 分析结果
analysis = engine.analyze_results(results)

# 打印分析结果
engine.print_analysis(analysis)

# 绘制结果
engine.plot(results, filename='backtest_result.png')
```

### 示例脚本

项目提供了示例脚本`backtest_example.py`，展示了如何使用回测模块进行策略回测和比较：

```bash
python scripts/backtest_example.py
```

该脚本包含以下示例：
- 运行均线交叉策略回测
- 运行MACD策略回测
- 比较不同策略的回测结果

## 回测结果分析

回测完成后，系统会生成以下分析结果：

1. **控制台输出**：显示关键绩效指标和部分交易记录
2. **YAML文件**：保存完整的分析结果，包括各项绩效指标
3. **CSV文件**：保存完整的交易记录
4. **图表文件**：保存回测结果图表，包括价格走势、交易信号和资金曲线

## 扩展自定义策略

要添加自定义策略，需要继承`core.strategy.strategy_base.StrategyBase`类，并实现必要的方法：

```python
from core.strategy.strategy_base import StrategyBase

@StrategyBase.register_strategy("我的自定义策略")
class MyCustomStrategy(StrategyBase):
    def _init_strategy_params(self):
        # 初始化策略特定参数
        self.param1 = self.params.get('参数1', 默认值)
        self.param2 = self.params.get('参数2', 默认值)
    
    def generate_signals(self, data):
        # 生成交易信号
        df = data.copy()
        
        # 计算指标和信号
        # ...
        
        # 设置信号：1(买入)、-1(卖出)、0(不操作)
        df['信号'] = 0
        
        return df
    
    def get_param_schema(self):
        # 获取策略参数的模式定义
        schema = super().get_param_schema()
        
        # 添加策略特定参数
        schema.update({
            '参数1': {
                'type': 'integer',
                'default': 默认值,
                'min': 最小值,
                'max': 最大值,
                'description': '参数1描述'
            },
            '参数2': {
                'type': 'float',
                'default': 默认值,
                'min': 最小值,
                'max': 最大值,
                'description': '参数2描述'
            }
        })
        
        return schema
```

注册策略后，可以通过回测模块使用该策略进行回测。

## 注意事项

1. 回测结果仅供参考，实际交易中可能存在滑点、手续费等因素影响
2. 回测使用的是历史数据，不能保证策略在未来市场中的表现
3. 建议在实盘交易前，先进行充分的回测和模拟交易
4. 数据质量对回测结果有重要影响，请确保使用可靠的数据源
5. 回测参数设置应尽量接近实际交易环境

## 常见问题

**Q: 如何查看所有可用的策略？**

A: 运行`python scripts/backtest.py --list`命令可以列出所有已注册的策略。

**Q: 如何设置策略参数？**

A: 可以通过命令行参数`--params`指定参数文件路径，或者在代码中直接设置策略参数字典。

**Q: 如何获取更多历史数据？**

A: 系统默认使用AKShare获取A股历史数据，如需更多数据，可以修改`load_stock_data`函数，添加其他数据源。

**Q: 如何进行参数优化？**

A: 可以编写循环脚本，对不同参数组合进行回测，比较结果找出最优参数。未来版本将添加内置的参数优化功能。