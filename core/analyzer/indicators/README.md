# 基于文件的衍生指标系统

## 概述

这是一个全新的衍生指标系统，实现了指标定义与运行程序的完全分离。指标定义以JSON格式存储在配置文件中，包含数据源、计算逻辑、输出配置等完整信息。

## 系统特点

1. **完全配置化**: 指标定义完全基于JSON配置文件，无需修改代码
2. **灵活数据源**: 支持从数据库任意表获取数据，支持日、周、月频数据
3. **复杂计算逻辑**: 支持数学运算、条件判断、技术分析函数等
4. **高性能计算**: 支持并行计算和批量处理
5. **完整验证**: 包含参数验证、数据验证、性能评估等
6. **易于扩展**: 只需添加JSON文件即可新增指标

## 目录结构

```
indicators/
├── README.md                    # 本文档
├── common/                      # 通用指标定义
│   ├── golden_cross.json       # 金叉信号
│   ├── volume_price_divergence.json  # 量价背离
│   └── ...
├── stock/                       # 股票特有指标
│   └── ...
├── industry/                    # 行业特有指标
│   ├── industry_momentum.json  # 行业动量
│   └── ...
└── index/                       # 指数特有指标
    ├── market_breadth.json      # 市场宽度
    └── ...
```

## 指标定义格式

### 基本结构

```json
{
  "name": "指标名称",
  "description": "指标描述",
  "version": "1.0.0",
  "entity_type": "适用实体类型",
  "frequency": "数据频率",
  "data_sources": {
    "数据源名称": {
      "table": "表名",
      "columns": ["列名1", "列名2"],
      "conditions": {"条件列": "条件值"},
      "date_column": "日期列名",
      "entity_column": "实体ID列名",
      "lookback_days": 历史数据天数
    }
  },
  "calculation": {
    "steps": [
      {
        "name": "步骤名称",
        "operation": "操作类型",
        "params": {"参数": "值"}
      }
    ]
  },
  "output": {
    "table": "输出表名",
    "column": "输出列名",
    "data_type": "数据类型"
  }
}
```

### 数据源配置

#### 基本数据源
```json
"data_sources": {
  "stock_daily": {
    "table": "股票日线数据表",
    "columns": ["开盘价", "收盘价", "最高价", "最低价", "成交量"],
    "date_column": "日期",
    "entity_column": "股票代码",
    "lookback_days": 252
  }
}
```

#### 带条件的数据源
```json
"data_sources": {
  "active_stocks": {
    "table": "股票日线数据表",
    "columns": ["收盘价", "成交量"],
    "conditions": {
      "成交量": "> 0",
      "停牌标志": "= '正常交易'"
    },
    "date_column": "日期",
    "entity_column": "股票代码",
    "lookback_days": 60
  }
}
```

#### 多表关联数据源
```json
"data_sources": {
  "stock_with_industry": {
    "table": "股票日线数据表",
    "columns": ["收盘价", "成交量"],
    "joins": [
      {
        "table": "股票基本信息表",
        "on": "股票代码",
        "columns": ["行业代码", "市值"]
      }
    ],
    "date_column": "日期",
    "entity_column": "股票代码",
    "lookback_days": 120
  }
}
```

### 计算逻辑配置

#### 基本数学运算
```json
"calculation": {
  "steps": [
    {
      "name": "计算移动平均",
      "operation": "rolling_mean",
      "params": {
        "column": "收盘价",
        "window": 20
      },
      "output_name": "ma20"
    },
    {
      "name": "计算金叉信号",
      "operation": "cross_above",
      "params": {
        "series1": "ma5",
        "series2": "ma20"
      },
      "output_name": "golden_cross"
    }
  ]
}
```

#### 条件判断
```json
"calculation": {
  "steps": [
    {
      "name": "RSI超买判断",
      "operation": "condition",
      "params": {
        "condition": "rsi > 70",
        "true_value": 1,
        "false_value": 0
      },
      "output_name": "rsi_overbought"
    }
  ]
}
```

#### 自定义函数
```json
"calculation": {
  "custom_functions": {
    "volume_price_divergence": {
      "description": "计算量价背离",
      "code": "def volume_price_divergence(price, volume, window=20):\n    price_trend = price.rolling(window).apply(lambda x: 1 if x[-1] > x[0] else -1)\n    volume_trend = volume.rolling(window).apply(lambda x: 1 if x[-1] > x[0] else -1)\n    return (price_trend != volume_trend).astype(int)"
    }
  },
  "steps": [
    {
      "name": "计算量价背离",
      "operation": "custom_function",
      "params": {
        "function": "volume_price_divergence",
        "args": ["收盘价", "成交量"],
        "kwargs": {"window": 20}
      },
      "output_name": "divergence_signal"
    }
  ]
}
```

### 输出配置

```json
"output": {
  "table": "股票衍生指标表",
  "column": "金叉信号",
  "data_type": "INTEGER",
  "description": "1表示金叉，0表示无信号",
  "null_handling": "forward_fill"
}
```

### 验证规则

```json
"validation": {
  "data_quality": {
    "min_data_points": 100,
    "max_null_ratio": 0.1,
    "outlier_detection": true
  },
  "business_rules": [
    {
      "rule": "output >= 0",
      "description": "输出值不能为负"
    }
  ]
}
```

### 参数定义

```json
"parameters": {
  "short_window": {
    "type": "integer",
    "default": 5,
    "min": 1,
    "max": 50,
    "description": "短期移动平均窗口"
  },
  "long_window": {
    "type": "integer",
    "default": 20,
    "min": 10,
    "max": 200,
    "description": "长期移动平均窗口"
  }
}
```

## 使用方法

### 1. 创建指标定义文件

在相应的目录下创建JSON文件，例如 `indicators/stock/my_indicator.json`：

```json
{
  "name": "我的指标",
  "description": "这是一个示例指标",
  "version": "1.0.0",
  "entity_type": "stock",
  "frequency": "daily",
  "data_sources": {
    "stock_data": {
      "table": "股票日线数据表",
      "columns": ["收盘价"],
      "date_column": "日期",
      "entity_column": "股票代码",
      "lookback_days": 30
    }
  },
  "calculation": {
    "steps": [
      {
        "name": "计算移动平均",
        "operation": "rolling_mean",
        "params": {
          "column": "收盘价",
          "window": 20
        },
        "output_name": "ma20"
      }
    ]
  },
  "output": {
    "table": "股票衍生指标表",
    "column": "我的指标",
    "data_type": "DECIMAL(10,4)"
  }
}
```

### 2. 运行指标计算

使用新的文件指标运行器：

```bash
# 计算所有指标
python file_based_indicator_runner.py

# 计算特定类型的指标
python file_based_indicator_runner.py --entity-types stock industry

# 计算特定指标
python file_based_indicator_runner.py --indicators golden_cross volume_price_divergence

# 计算特定实体的指标
python file_based_indicator_runner.py --entity-ids 000001.SZ 000002.SZ

# 指定日期范围
python file_based_indicator_runner.py --start-date 2023-01-01 --end-date 2023-12-31

# 干运行模式（不实际存储数据）
python file_based_indicator_runner.py --dry-run

# 调整性能参数
python file_based_indicator_runner.py --max-workers 8 --batch-size 200
```

### 3. 验证指标定义

```python
from core.analyzer.file_indicator_loader import get_file_indicator_loader

# 获取指标加载器
loader = get_file_indicator_loader()

# 验证指标定义
validation = loader.validate_indicator('golden_cross')
if validation['valid']:
    print("指标定义有效")
else:
    print(f"验证失败: {validation['errors']}")
```

### 4. 计算单个指标

```python
from core.analyzer.file_indicator_loader import get_file_indicator_loader

# 获取指标加载器
loader = get_file_indicator_loader()

# 计算指标
result = loader.calculate_indicator(
    indicator_name='golden_cross',
    entity_id='000001.SZ',
    start_date='2023-01-01',
    end_date='2023-12-31'
)

print(result)
```

## 支持的操作类型

### 数学运算
- `rolling_mean`: 移动平均
- `rolling_std`: 移动标准差
- `rolling_sum`: 移动求和
- `rolling_max`: 移动最大值
- `rolling_min`: 移动最小值
- `pct_change`: 百分比变化
- `diff`: 差分
- `cumsum`: 累计求和
- `cumprod`: 累计乘积

### 技术分析
- `sma`: 简单移动平均
- `ema`: 指数移动平均
- `rsi`: 相对强弱指数
- `macd`: MACD指标
- `bollinger_bands`: 布林带
- `stochastic`: 随机指标

### 条件判断
- `condition`: 条件判断
- `cross_above`: 向上穿越
- `cross_below`: 向下穿越
- `greater_than`: 大于
- `less_than`: 小于
- `between`: 区间判断

### 聚合运算
- `group_mean`: 分组平均
- `group_sum`: 分组求和
- `group_count`: 分组计数
- `rank`: 排名
- `percentile`: 百分位数

### 自定义函数
- `custom_function`: 执行自定义Python函数
- `lambda_function`: 执行Lambda表达式

## 最佳实践

### 1. 指标命名
- 使用描述性的名称
- 遵循一致的命名规范
- 避免特殊字符和空格

### 2. 数据源优化
- 只获取必要的列
- 合理设置lookback_days
- 使用适当的条件过滤

### 3. 计算逻辑
- 将复杂计算分解为多个步骤
- 使用有意义的中间变量名
- 添加详细的注释和描述

### 4. 性能优化
- 避免不必要的数据加载
- 使用向量化操作
- 合理设置批处理大小

### 5. 错误处理
- 添加数据验证规则
- 处理缺失值和异常值
- 提供有意义的错误信息

## 故障排除

### 常见问题

1. **指标定义验证失败**
   - 检查JSON格式是否正确
   - 确认必需字段是否存在
   - 验证数据类型是否匹配

2. **数据加载失败**
   - 检查表名和列名是否正确
   - 确认数据库连接是否正常
   - 验证查询条件是否合理

3. **计算结果异常**
   - 检查输入数据质量
   - 验证计算逻辑是否正确
   - 确认参数设置是否合理

4. **性能问题**
   - 减少数据加载量
   - 优化计算逻辑
   - 调整并发参数

### 调试技巧

1. 使用干运行模式测试
2. 启用详细日志输出
3. 分步验证计算结果
4. 使用小数据集进行测试

## 扩展开发

### 添加新的操作类型

在 `file_indicator_loader.py` 中的 `IndicatorCalculationEngine` 类中添加新的操作方法：

```python
def _operation_my_custom_op(self, data, params):
    """自定义操作"""
    # 实现自定义逻辑
    return result
```

### 添加新的数据源类型

扩展数据源加载逻辑，支持更多的数据源类型和查询方式。

### 添加新的验证规则

在验证模块中添加新的业务规则和数据质量检查。

## 版本历史

- v1.0.0: 初始版本，支持基本的指标定义和计算
- 后续版本将添加更多功能和优化

## 联系方式

如有问题或建议，请联系开发团队。