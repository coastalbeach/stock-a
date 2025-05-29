# PostgreSQL高级功能增强

## 概述

本项目对A股量化分析系统进行了PostgreSQL高级功能增强，充分利用PostgreSQL的触发器、存储过程、函数和物化视图等特性，减轻Python端的计算压力，提高系统性能，并增强数据处理能力。

## 主要功能增强

### 1. 数据库端计算与处理

- **财务指标自动计算**：通过触发器和存储过程，在数据库端自动计算财务指标（如资产负债率、净资产收益率等），无需Python代码重复计算
- **行业平均指标计算**：提供行业平均财务指标计算功能，便于横向比较分析
- **物化视图预计算**：预计算并缓存常用查询结果，显著提高查询性能

### 2. 数据一致性与完整性保障

- **数据一致性校验触发器**：自动验证财务数据的一致性（如资产=负债+所有者权益）
- **自动更新时间戳**：自动维护数据的更新时间，便于追踪数据鲜度
- **数据版本管理**：记录所有数据变更历史，支持数据追溯和审计

### 3. 实时通知与事件驱动

- **数据变更通知**：当关键数据发生变化时，自动发送通知
- **通知监听机制**：Python端可以监听数据库通知，实现事件驱动架构

### 4. 性能优化

- **物化视图**：提高复杂查询性能，减少计算开销
- **自动统计信息收集**：优化查询计划，提高SQL执行效率
- **数据库维护自动化**：提供自动化的数据库维护功能

## 文件说明

- **`scripts/db_enhancements.sql`**：包含所有PostgreSQL高级功能的SQL定义
- **`scripts/apply_db_enhancements.py`**：应用数据库增强功能的Python脚本
- **`data/storage/enhanced_postgresql_manager.py`**：增强版PostgreSQL管理器类
- **`docs/postgresql_advanced_features.md`**：详细的功能文档
- **`examples/postgresql_features_demo.py`**：功能演示示例

## 使用方法

### 1. 安装数据库增强功能

```bash
python scripts/apply_db_enhancements.py --apply
```

### 2. 检查安装状态

```bash
python scripts/apply_db_enhancements.py --check
```

### 3. 在代码中使用增强功能

```python
from data.storage.enhanced_postgresql_manager import EnhancedPostgreSQLManager

# 创建增强版PostgreSQL管理器实例
db = EnhancedPostgreSQLManager()

# 获取财务指标
ratios = db.get_financial_ratios("000001")
print(f"财务指标: {ratios}")

# 获取行业平均指标
industry_avg = db.get_industry_average("银行", "2023-12-31")
print(f"行业平均指标: {industry_avg}")

# 关闭数据库连接
db.close()
```

### 4. 运行演示示例

```bash
python examples/postgresql_features_demo.py
```

## 性能优势

1. **减少网络传输**：数据计算在数据库端完成，减少网络传输开销
2. **减轻Python计算负担**：复杂计算由数据库执行，释放Python资源
3. **提高查询性能**：物化视图预计算提高查询速度，特别是对于复杂聚合查询
4. **实时响应**：通过数据库通知机制，实现对数据变化的实时响应
5. **数据一致性保障**：触发器确保数据一致性，减少应用层验证逻辑

## 注意事项

1. 数据库增强功能需要PostgreSQL 12+版本支持
2. 首次应用增强功能可能需要较长时间，特别是对于大型数据库
3. 物化视图会占用额外的存储空间，但可以显著提高查询性能
4. 触发器会增加数据写入的开销，但可以确保数据一致性和完整性

## 后续优化方向

1. **分区表**：对大型历史数据表实施分区策略，提高查询性能
2. **并行查询优化**：利用PostgreSQL的并行查询能力，进一步提高性能
3. **定制索引**：根据查询模式优化索引策略
4. **数据压缩**：对历史数据实施压缩策略，减少存储开销
5. **更多存储过程**：将更多复杂计算逻辑迁移到数据库端