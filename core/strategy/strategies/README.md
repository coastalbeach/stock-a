# JSON策略框架使用指南

## 概述

本框架允许用户通过简单的JSON文件定义交易策略，无需编写Python代码。策略定义包括策略名称、描述、所需数据列、参数配置、买入条件和卖出条件。策略管理器会自动发现并加载这些JSON策略文件，使其与Python编写的策略一样可用。

## 目录结构

```
core/strategy/
  ├── strategies/         # 存放JSON策略文件的目录
  │   ├── ma_cross_strategy.json
  │   ├── macd_strategy.json
  │   ├── comprehensive_strategy.json
  │   └── ... (其他策略文件)
  ├── json_strategy_loader.py  # JSON策略加载器
  ├── strategy_base.py     # 策略基类
  └── strategy_manager.py  # 策略管理器
```

## JSON策略文件格式

一个完整的JSON策略文件应包含以下字段：

```json
{
  "name": "策略名称",
  "description": "策略描述",
  "required_data": ["日期", "股票代码", "开盘", "收盘", "最高", "最低", "成交量"],
  "parameters": {
    "参数1": {
      "type": "integer|number|boolean|string",
      "default": 默认值,
      "min": 最小值,
      "max": 最大值,
      "description": "参数描述"
    },
    "参数2": { ... }
  },
  "buy_conditions": [
    {
      "condition": "条件表达式",
      "description": "条件描述",
      "strength": 信号强度(0.0-1.0)
    }
  ],
  "sell_conditions": [
    {
      "condition": "条件表达式",
      "description": "条件描述",
      "strength": 信号强度(0.0-1.0)
    }
  ]
}
```

### 字段说明

- **name**: 策略名称，必须唯一
- **description**: 策略描述
- **required_data**: 策略所需的数据列名列表
- **parameters**: 策略参数定义，包括类型、默认值、取值范围和描述
- **buy_conditions**: 买入条件列表，每个条件包括表达式、描述和信号强度
- **sell_conditions**: 卖出条件列表，每个条件包括表达式、描述和信号强度

### 条件表达式

条件表达式使用Python语法，可以访问数据列和参数：

- 数据列直接使用列名，如 `收盘`、`开盘`、`最高`、`最低`、`成交量`
- 参数通过 `params['参数名']` 访问，如 `params['短期均线']`
- 支持常见技术指标函数：
  - `SMA(列名, 周期)`: 简单移动平均线
  - `EMA(列名, 周期)`: 指数移动平均线
  - `RSI(列名, 周期)`: 相对强弱指数
  - `MACD(列名, 快线周期, 慢线周期, 信号周期)`: MACD指标，返回[MACD线, 信号线, 柱状图]
  - `BOLL(列名, 周期, 标准差倍数)`: 布林带，返回[中轨, 上轨, 下轨]
  - `ATR(最高, 最低, 收盘, 周期)`: 真实波动幅度均值
  - `KDJ(最高, 最低, 收盘, 周期)`: KDJ指标，返回[K, D, J]

- 支持pandas常用函数，如 `shift()`、`rolling()`、`mean()`等

## 示例策略

### 均线交叉策略

```json
{
  "name": "均线交叉策略",
  "description": "当短期均线上穿长期均线时买入，下穿时卖出",
  "required_data": ["日期", "股票代码", "收盘"],
  "parameters": {
    "短期均线": {
      "type": "integer",
      "default": 5,
      "min": 1,
      "max": 30,
      "description": "短期均线周期"
    },
    "长期均线": {
      "type": "integer",
      "default": 20,
      "min": 10,
      "max": 60,
      "description": "长期均线周期"
    }
  },
  "buy_conditions": [
    {
      "condition": "SMA(收盘, params['短期均线']) > SMA(收盘, params['长期均线']) and SMA(收盘, params['短期均线']).shift(1) <= SMA(收盘, params['长期均线']).shift(1)",
      "description": "短期均线上穿长期均线",
      "strength": 1.0
    }
  ],
  "sell_conditions": [
    {
      "condition": "SMA(收盘, params['短期均线']) < SMA(收盘, params['长期均线']) and SMA(收盘, params['短期均线']).shift(1) >= SMA(收盘, params['长期均线']).shift(1)",
      "description": "短期均线下穿长期均线",
      "strength": 1.0
    }
  ]
}
```

## 使用方法

### 创建新策略

1. 在 `core/strategy/strategies/` 目录下创建新的JSON文件
2. 按照上述格式定义策略
3. 策略管理器会自动发现并加载新策略

### 在代码中使用

```python
from core.strategy import StrategyManager

# 创建策略管理器
manager = StrategyManager()

# 获取可用策略列表
available_strategies = manager.get_available_strategies()
print(f"可用策略: {available_strategies}")

# 加载数据
data = load_your_data()  # 确保包含策略所需的所有列

# 运行策略
signals = manager.run_strategy("均线交叉策略", data, 短期均线=5, 长期均线=20)

# 使用生成的信号
print(signals)
```

### 子文件夹组织

您可以使用子文件夹组织大量策略，策略管理器会递归搜索所有子文件夹：

```
core/strategy/strategies/
  ├── 均线策略/
  │   ├── ma_cross.json
  │   ├── triple_ma.json
  │   └── ...
  ├── 震荡指标/
  │   ├── rsi_strategy.json
  │   ├── kdj_strategy.json
  │   └── ...
  └── 趋势指标/
      ├── macd_strategy.json
      ├── adx_strategy.json
      └── ...
```

## 高级用法

### 组合条件

可以在一个策略中定义多个买入或卖出条件，每个条件都有自己的强度。当多个条件同时满足时，会生成更强的信号。

### 动态创建策略

除了从文件加载，还可以在代码中动态创建JSON策略：

```python
from core.strategy import JSONStrategyLoader

# 创建策略定义
strategy_def = {
    "name": "RSI策略",
    "description": "基于RSI指标的超买超卖策略",
    "required_data": ["日期", "股票代码", "收盘"],
    "parameters": {
        "RSI周期": {
            "type": "integer",
            "default": 14,
            "min": 2,
            "max": 30,
            "description": "RSI计算周期"
        },
        "超买阈值": {
            "type": "number",
            "default": 70,
            "min": 60,
            "max": 90,
            "description": "RSI超买阈值"
        },
        "超卖阈值": {
            "type": "number",
            "default": 30,
            "min": 10,
            "max": 40,
            "description": "RSI超卖阈值"
        }
    },
    "buy_conditions": [
        {
            "condition": "RSI(收盘, params['RSI周期']) < params['超卖阈值']",
            "description": "RSI低于超卖阈值",
            "strength": 1.0
        }
    ],
    "sell_conditions": [
        {
            "condition": "RSI(收盘, params['RSI周期']) > params['超买阈值']",
            "description": "RSI高于超买阈值",
            "strength": 1.0
        }
    ]
}

# 创建策略加载器
loader = JSONStrategyLoader()

# 创建策略实例
strategy = loader.create_strategy_from_dict(strategy_def)

# 保存策略到文件（可选）
file_path = strategy.save()
print(f"策略已保存到: {file_path}")
```

## 注意事项

1. 确保条件表达式语法正确，错误的表达式会导致策略无法执行
2. 策略名称必须唯一，重名策略会覆盖之前的策略
3. 确保提供策略所需的所有数据列
4. 参数类型必须是有效的JSON类型：integer、number、boolean或string
5. 条件表达式中可以使用pandas和numpy函数，但需要确保这些函数在策略执行环境中可用

## 多元数据访问

策略现在支持访问多种数据源，可以在条件表达式中使用以下方法获取各类数据：

### 可用的数据访问方法

- **get_stock_quotes(stock_code, start_date=None, end_date=None, limit=60)**
  获取股票行情数据
  ```json
  "condition": "get_stock_quotes('000001', start_date='2023-01-01', limit=30)['收盘'].mean() > 收盘"
  ```

- **get_technical_indicators(stock_code, indicators=None, start_date=None, end_date=None, limit=60)**
  获取技术指标数据
  ```json
  "condition": "get_technical_indicators('000001', indicators=['RSI14', 'MACD12_26_9'], limit=10)['RSI14'].iloc[-1] < 30"
  ```

- **get_financial_statement(statement_type, stock_code=None, report_date=None, limit=4)**
  获取财务报表数据
  ```json
  "condition": "get_financial_statement('利润表', 股票代码, limit=1)['净利润'].iloc[0] > 0"
  ```

- **get_financial_ratios(stock_code, report_date=None)**
  获取财务指标
  ```json
  "condition": "get_financial_ratios(股票代码)['ROE'] > 15"
  ```

- **get_stock_info(stock_code=None, stock_name=None, industry=None)**
  获取股票基本信息
  ```json
  "condition": "get_stock_info(股票代码)['所属行业'].iloc[0] == '计算机'"
  ```

- **get_industry_info(industry_code=None, industry_name=None)**
  获取行业信息
  ```json
  "condition": "get_industry_info(industry_name='计算机')['行业平均PE'].iloc[0] > 30"
  ```

- **get_concept_info(concept_code=None, concept_name=None)**
  获取概念信息
  ```json
  "condition": "get_concept_info(concept_name='人工智能')['概念股数量'].iloc[0] > 50"
  ```

- **get_index_quotes(index_code, start_date=None, end_date=None, limit=60)**
  获取指数行情数据
  ```json
  "condition": "get_index_quotes('000001', limit=5)['收盘'].pct_change().mean() > 0"
  ```

- **get_dragon_tiger_list(stock_code=None, trade_date=None, limit=50)**
  获取龙虎榜数据
  ```json
  "condition": "len(get_dragon_tiger_list(股票代码, limit=10)) > 0"
  ```

- **get_table_data(table_name, conditions=None, order_by=None, order_desc=False, limit=None, offset=None)**
  获取任意表数据
  ```json
  "condition": "get_table_data('股票池', {'类型': '白马股'}, limit=100)['股票代码'].isin([股票代码])"
  ```

### 使用示例

以下是一个结合基本面和技术面的策略示例：

```json
{
  "name": "基本面技术面结合策略",
  "description": "结合财务数据和技术指标的综合策略",
  "required_data": ["日期", "股票代码", "收盘"],
  "parameters": {
    "ROE阈值": {
      "type": "number",
      "default": 15.0,
      "min": 5.0,
      "max": 30.0,
      "description": "最低ROE要求"
    },
    "RSI周期": {
      "type": "integer",
      "default": 14,
      "min": 2,
      "max": 30,
      "description": "RSI计算周期"
    }
  },
  "buy_conditions": [
    {
      "condition": "get_financial_ratios(股票代码)['ROE'] > params['ROE阈值'] and RSI(收盘, params['RSI周期']) < 30",
      "description": "高ROE且RSI超卖",
      "strength": 0.8
    },
    {
      "condition": "get_index_quotes('000001', limit=5)['收盘'].pct_change().mean() > 0 and 收盘 > SMA(收盘, 20)",
      "description": "大盘上涨且股价站上20日均线",
      "strength": 0.7
    }
  ],
  "sell_conditions": [
    {
      "condition": "RSI(收盘, params['RSI周期']) > 70",
      "description": "RSI超买",
      "strength": 0.6
    }
  ]
}
```