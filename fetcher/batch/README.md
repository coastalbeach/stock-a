# 批量股票历史数据获取工具

本模块提供了基于 `akshare` 库的 `stock_zh_a_hist` 函数的批量股票历史数据获取和增量更新功能。

## 功能特性

### 基础版批量获取器 (`batch_historical_fetcher.py`)
- ✅ 多线程并发处理
- ✅ 断点续传功能
- ✅ 错误重试机制
- ✅ 进度监控
- ✅ 增量更新（只获取缺失的数据）
- ✅ 支持不复权和后复权数据
- ✅ Redis缓存优化
- ✅ 详细日志记录

### 增强版批量获取器 (`enhanced_batch_fetcher.py`)
在基础版功能基础上，新增：
- 🚀 配置文件支持
- 🚀 数据验证和质量检查
- 🚀 智能错误恢复
- 🚀 性能监控和统计
- 🚀 灵活的过滤条件
- 🚀 批量数据处理优化
- 🚀 详细的错误日志
- 🚀 调度和通知功能

## 文件结构

```
fetcher/batch/
├── batch_historical_fetcher.py    # 基础版批量获取器
├── enhanced_batch_fetcher.py      # 增强版批量获取器
├── batch_config.yaml              # 配置文件
├── run_batch_update.py            # 运行脚本
└── README.md                      # 说明文档
```

## 快速开始

### 1. 使用运行脚本（推荐）

```bash
# 使用增强版批量获取器（默认）
python fetcher/batch/run_batch_update.py

# 使用基础版批量获取器
python fetcher/batch/run_batch_update.py --mode basic

# 指定股票代码
python fetcher/batch/run_batch_update.py --stocks 000001,000002,600000

# 自定义线程数和批处理大小
python fetcher/batch/run_batch_update.py --workers 16 --batch-size 100

# 试运行模式（不实际执行）
python fetcher/batch/run_batch_update.py --dry-run

# 禁用断点续传
python fetcher/batch/run_batch_update.py --no-checkpoint

# 保存执行报告
python fetcher/batch/run_batch_update.py --output-report logs/batch_report.json
```

### 2. 直接使用Python代码

#### 基础版使用示例

```python
from fetcher.batch.batch_historical_fetcher import BatchHistoricalFetcher

# 创建批量获取器
fetcher = BatchHistoricalFetcher(
    max_workers=8,
    batch_size=50,
    start_date="20050104"
)

# 运行批量更新
result = fetcher.run_batch_update(use_checkpoint=True)

# 查看结果
print(f"成功更新 {result['completed_stocks']} 只股票")
print(f"失败 {result['failed_stocks']} 只股票")
print(f"成功率: {result['success_rate']:.2f}%")

# 清理资源
fetcher.cleanup()
```

#### 增强版使用示例

```python
from fetcher.batch.enhanced_batch_fetcher import EnhancedBatchFetcher

# 创建增强版批量获取器
fetcher = EnhancedBatchFetcher(config_file="fetcher/batch/batch_config.yaml")

# 运行批量更新
result = fetcher.run_enhanced_batch_update(use_checkpoint=True)

# 查看详细结果
print(f"总股票数: {result['total_stocks']}")
print(f"成功更新: {result['completed_stocks']}")
print(f"失败数量: {result['failed_stocks']}")
print(f"成功率: {result['success_rate']:.2f}%")
print(f"平均每只股票耗时: {result['average_time_per_stock']:.2f}秒")
print(f"总耗时: {result['duration_seconds']:.2f}秒")

# 清理资源
fetcher.cleanup()
```

## 配置说明

### 配置文件 (`batch_config.yaml`)

配置文件包含以下主要部分：

```yaml
# 基本配置
basic:
  start_date: "20050104"          # 数据获取起始日期
  enable_checkpoint: true         # 启用断点续传
  log_level: "INFO"              # 日志级别

# 并发配置
concurrency:
  max_workers: 8                 # 最大线程数
  batch_size: 50                 # 批处理大小
  request_interval: 0.1          # 请求间隔（秒）

# 重试策略
retry:
  max_attempts: 3                # 最大重试次数
  base_interval: 2               # 基础重试间隔
  backoff_factor: 2              # 退避因子

# 数据过滤
filtering:
  skip_st_stocks: false          # 跳过ST股票
  skip_delisted_stocks: false    # 跳过退市股票
  stock_code_prefixes: []        # 股票代码前缀过滤

# 性能优化
performance:
  enable_redis_cache: true       # 启用Redis缓存
  enable_db_pool: true           # 启用数据库连接池
  bulk_insert_size: 1000         # 批量插入大小

# 数据验证
validation:
  enable_data_validation: true   # 启用数据验证
  check_duplicates: true         # 检查重复数据
  max_missing_data_rate: 10.0    # 最大数据缺失率
```

### 环境变量配置

可以通过环境变量覆盖部分配置：

```bash
export BATCH_MAX_WORKERS=16
export BATCH_BATCH_SIZE=100
export BATCH_LOG_LEVEL=DEBUG
export BATCH_ENABLE_CACHE=true
```

## 数据表结构

工具会将数据保存到以下两个表：

1. **股票历史行情_不复权** - 存储不复权的历史行情数据
2. **股票历史行情_后复权** - 存储后复权的历史行情数据

表结构包含以下字段：
- 日期 (DATE)
- 股票代码 (VARCHAR)
- 开盘 (DECIMAL)
- 收盘 (DECIMAL)
- 最高 (DECIMAL)
- 最低 (DECIMAL)
- 成交量 (BIGINT)
- 成交额 (DECIMAL)
- 振幅 (DECIMAL)
- 涨跌幅 (DECIMAL)
- 涨跌额 (DECIMAL)
- 换手率 (DECIMAL)

## 断点续传

工具支持断点续传功能，在程序意外中断后可以从上次停止的地方继续：

1. **自动保存进度**：每处理一定数量的股票后自动保存进度
2. **智能恢复**：重新启动时自动检测并跳过已完成的股票
3. **进度文件**：进度信息保存在 `data/batch_checkpoint.json`

## 错误处理

### 重试机制
- 支持指数退避重试
- 可配置最大重试次数
- 智能错误分类和处理

### 错误日志
- 详细的错误信息记录
- 失败股票列表保存
- 错误统计和分析

### 容错处理
- 单只股票失败不影响整体进程
- 连续失败达到阈值时自动停止
- 支持手动干预和恢复

## 性能优化

### 并发处理
- 多线程并发获取数据
- 可配置线程池大小
- 智能负载均衡

### 缓存优化
- Redis缓存热点数据
- 减少重复数据库查询
- 智能缓存失效策略

### 数据库优化
- 连接池管理
- 批量数据插入
- 事务优化

### 内存管理
- 分批处理大数据集
- 及时释放内存
- 垃圾回收优化

## 监控和统计

### 实时监控
- 进度条显示
- 实时成功率统计
- 处理速度监控

### 执行报告
- 详细的执行统计
- 性能指标分析
- 错误分布统计

### 日志记录
- 分级日志输出
- 结构化日志格式
- 日志文件轮转

## 常见问题

### Q: 如何处理网络超时？
A: 工具内置了重试机制，会自动重试失败的请求。可以通过配置文件调整重试参数。

### Q: 数据获取速度慢怎么办？
A: 可以适当增加线程数，但要注意不要过度并发导致被限流。建议先从8个线程开始测试。

### Q: 如何只更新特定股票？
A: 使用 `--stocks` 参数指定股票代码列表，或者在代码中传入 `stock_list` 参数。

### Q: 断点续传文件在哪里？
A: 默认保存在 `data/batch_checkpoint.json`，可以通过配置文件修改路径。

### Q: 如何查看详细的错误信息？
A: 设置日志级别为 DEBUG，或者查看错误日志文件 `logs/batch_errors.log`。

### Q: 数据验证失败怎么办？
A: 检查数据源是否正常，可以临时禁用数据验证功能，或者调整验证参数。

## 注意事项

1. **API限流**：akshare可能有访问频率限制，建议设置适当的请求间隔
2. **数据库连接**：确保PostgreSQL数据库连接正常，表结构已创建
3. **Redis连接**：如果启用缓存功能，确保Redis服务正常运行
4. **磁盘空间**：历史数据量较大，确保有足够的存储空间
5. **网络稳定**：数据获取依赖网络，建议在网络稳定的环境下运行

## 更新日志

### v1.0.0 (2024-01-XX)
- 初始版本发布
- 基础批量获取功能
- 断点续传支持
- 多线程并发处理

### v1.1.0 (2024-01-XX)
- 新增增强版批量获取器
- 配置文件支持
- 数据验证功能
- 性能监控和统计
- 错误处理优化

## 许可证

本项目遵循项目主许可证。

## 贡献

欢迎提交Issue和Pull Request来改进这个工具。

## 联系方式

如有问题或建议，请通过项目Issue页面联系。