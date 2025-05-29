# 触发器测试修复说明

## 问题描述

在运行触发器测试脚本时，遇到了以下错误：

```
执行SQL文件 adjustment_factor_triggers.sql 失败: relation "public.股票历史行情_不复权" does not exist
错误详情: 42P01 - ERROR: relation "public.股票历史行情_不复权" does not exist
```

这个错误表明在测试数据库中缺少`股票历史行情_不复权`表，导致触发器创建失败。

## 问题原因

通过分析代码，我们发现：

1. 触发器`trg_calculate_hfq_price_on_daily_data_change`依赖于`股票历史行情_不复权`表
2. 在测试环境中，SQL执行顺序中没有包含创建`股票历史行情_不复权`表的SQL文件
3. 原有的`market_data_tables.sql`只包含了周频和月频的表定义，没有包含日频的`股票历史行情_不复权`表

## 解决方案

我们采取了以下步骤来解决这个问题：

1. 创建了新的SQL文件`stock_history_tables.sql`，包含`股票历史行情_不复权`和`股票历史行情_后复权`表的定义
2. 修改了`apply_triggers.py`中的`SQL_EXECUTION_ORDER`，将新创建的SQL文件添加到执行顺序中
3. 简化了表定义，移除了分区相关的代码，以便于测试环境使用

## 如何使用

现在，您可以按照以下步骤测试触发器：

1. 运行基本测试：
   ```bash
   python trigger/test_triggers.py --test-all
   ```

2. 运行增强测试（基于配置文件）：
   ```bash
   python trigger/test_triggers_enhanced.py --test-all
   ```

3. 如果需要保留测试数据库以进行调试，可以添加`--keep-db`参数：
   ```bash
   python trigger/test_triggers.py --test-all --keep-db
   ```

## 注意事项

1. 测试环境中的表结构与生产环境可能有所不同，特别是我们移除了分区相关的代码
2. 如果在生产环境中应用这些触发器，请确保使用完整的表定义，包括分区设置
3. 测试成功后，建议在非生产环境中先进行验证，然后再应用到生产环境