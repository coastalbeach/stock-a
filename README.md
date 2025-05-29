# A股量化分析系统

## 项目概述

本项目是一个针对中国A股市场的量化分析系统，提供基本数据获取、指标计算、策略选股等功能，具有良好的拓展性。项目使用AKShare接口获取数据，PostgreSQL和Redis进行数据管理，Python作为主要开发语言。

## 项目结构

```
stock-a/
├── config/                 # 配置文件目录
│   ├── tables.yaml         # 数据库表结构定义
│   ├── connection.yaml     # 数据库连接配置
│   ├── redis.yaml          # Redis配置
│   ├── app.yaml            # 应用程序配置
│   └── derived_indicators.yaml # 派生指标配置
├── akshare/                # AKShare相关文档和图片
│   ├── M2S.py
│   ├── index.md
│   ├── index.svg
│   ├── stock.md
│   ├── stock.svg
│   └── tutorial.md
├── batch/                  # 批处理脚本目录
│   ├── data_fetcher/
│   │   ├── daily_data_fetcher.bat
│   │   ├── monthly_data_fetcher.bat
│   │   └── quarterly_data_fetcher.bat
│   ├── periodic_tasks/
│   │   └── daily_monthly_quarterly_tasks.bat
│   ├── scheduler/
│   │   └── periodic_tasks_scheduler.bat
│   └── 日常工作批处理程序说明.md
├── core/                   # 核心业务逻辑
│   ├── analyzer/           # 分析引擎
│   │   ├── __init__.py
│   │   ├── derived_indicator_loader.py # 派生指标加载器
│   │   ├── derived_indicators.py   # 派生指标计算
│   │   └── technical_indicators.py # 技术指标计算
│   └── strategy/           # 策略模块
│       ├── __init__.py
│       ├── json_strategy_loader.py # JSON策略加载器
│       ├── strategies/             # 策略定义目录
│       ├── strategy_base.py        # 策略基类
│       └── strategy_manager.py     # 策略管理器
├── db/                     # 数据库管理模块
│   ├── __init__.py
│   ├── enhanced_postgresql_manager.py # 增强型PostgreSQL管理器
│   ├── postgresql_manager.py # PostgreSQL管理器
│   ├── redis_manager.py      # Redis管理器
│   ├── table_data_reader.py  # 表数据读取器
│   ├── table_structure_manager.py # 表结构管理器
│   └── test_table_structure_manager.py # 表结构管理器测试
├── docs/                   # 文档目录
│   ├── README_postgresql_enhancements.md
│   ├── association_rule_mining.md
│   ├── postgresql_advanced_features.md
│   └── tables.sql
├── fetcher/                # 数据获取模块
│   ├── index/
│   │   ├── index_quote.py
│   │   └── index_realtime.py
│   ├── market/
│   │   ├── board_realtime.py
│   │   └── sector_data.py
│   ├── special/
│   │   ├── block_trade.py
│   │   └── stock_comment.py
│   ├── stock/
│   │   ├── basic_info.py
│   │   ├── financial_data.py
│   │   ├── financial_signal.py
│   │   ├── historical_data.py
│   │   └── stock_comment_integrated.py
│   └── trader/
│       ├── broker_ranking.py
│       ├── institutional.py
│       ├── lhb_data.py
│       └── stockholder.py
├── initialize/             # 初始化脚本
│   ├── db_initializer.py
│   └── tables.sql
├── scripts/                # 脚本文件
│   ├── backtest.py
│   ├── backtest_example.py
│   ├── run_derived_indicators.py
│   ├── strategy_example.py
│   └── test_derived_indicators_runner.py
├── tests/                  # 测试目录
│   ├── test_derived_indicators.py
│   └── test_strategy.py
├── trigger/                # 触发器相关文件
│   ├── README.md
│   ├── README_adjustment_factor.md
│   ├── README_fix_triggers_test.md
│   ├── README_testing.md
│   ├── adjustment_factor_updater.py
│   ├── apply_triggers.py
│   ├── sql/
│   │   ├── 01_tables/
│   │   ├── 02_functions/
│   │   └── 03_triggers/
│   ├── test_config.yaml
│   ├── test_triggers.py
│   └── test_triggers_enhanced.py
├── ui/                     # 用户界面
│   ├── __init__.py
│   ├── chart_view.py
│   ├── data_view.py
│   ├── main_window.py
│   ├── strategy_view.py
│   └── test_matplotlib_qt.py
└── utils/                  # 工具函数
    ├── config_loader.py
    └── logger.py
├── main.py                 # 主程序入口
├── requirements.txt        # Python依赖文件
```

## 模块职责

### 数据层

#### 数据获取模块 (fetcher)

- **market/**: 负责获取市场整体数据，如指数、板块、行业等
- **stock/**: 负责获取个股相关数据，包括基本信息、行情、财务等
- **index/**: 负责获取指数相关数据，包括成分股、权重等
- **special/**: 负责获取特色数据，如融资融券、大宗交易等
- **trader/**: 负责获取有影响力的股票持有者数据，包括龙虎榜、股东信息、机构持仓、营业部排行等

#### 数据库管理模块 (db)

- **enhanced_postgresql_manager.py**: 增强型PostgreSQL管理器，提供更高级的数据库操作
  - 适用场景：存储结构化历史数据、财务报表、公司信息等需要关系查询的数据
  - 提供数据版本管理、历史追溯功能
  - 支持复杂SQL查询和数据分析

- **postgresql_manager.py**: PostgreSQL管理器，提供基本的数据库连接和操作
  - 适用场景：存储结构化历史数据、财务报表、公司信息等需要关系查询的数据
  - 提供数据版本管理、历史追溯功能
  - 支持复杂SQL查询和数据分析

- **redis_manager.py**: Redis管理器，管理Redis连接和操作
  - 适用场景：缓存实时行情、热点数据、临时计算结果等
  - 提供高速读写和过期策略
  - 支持发布/订阅模式实现数据更新通知

- **table_data_reader.py**: 表数据读取器，用于从数据库读取表数据
- **table_structure_manager.py**: 表结构管理器，用于管理数据库表的结构

### 业务逻辑层

#### 分析引擎 (core/analyzer)

- **derived_indicator_loader.py**: 派生指标加载器，用于加载和管理派生指标
- **derived_indicators.py**: 派生指标计算，实现各种派生指标的计算
- **technical_indicators.py**: 技术指标计算，实现各种技术指标计算（MA、MACD、RSI等）

#### 策略模块 (core/strategy)

- **json_strategy_loader.py**: JSON策略加载器，用于从JSON文件加载策略配置
- **strategy_base.py**: 策略基类，定义策略基类和接口
- **strategy_manager.py**: 策略管理器，用于管理和执行策略

### 表现层

#### 用户界面 (ui)

- **main_window.py**: 主窗口实现，整合各个视图
- **data_view.py**: 数据浏览和查询界面
- **chart_view.py**: 图表展示界面
- **strategy_view.py**: 策略配置和结果展示界面

### 工具模块 (utils)

- **logger.py**: 日志记录工具
- **config_loader.py**: 配置加载工具

## 数据库设计与初始化

### 数据库表结构设计

1. **PostgreSQL数据库表**：
   - **股票基本信息表**：存储股票代码、名称、上市日期、所属行业等基本信息
   - **日线行情表**：存储股票的日K线数据，包括开盘价、收盘价、最高价、最低价、成交量等
   - **财务数据表**：存储季度财务报表数据，包括营收、净利润、资产负债等
   - **指数数据表**：存储各类指数的行情数据
   - **板块数据表**：存储行业板块、概念板块的成分股及行情数据

2. **Redis数据结构**：
   - **行情:股票代码**：使用Hash结构存储实时行情数据
   - **热门:板块**：使用Sorted Set存储热门板块及其热度分数
   - **指标:股票代码**：使用Hash结构存储计算后的技术指标
   - **缓存:查询标识**：使用String结构存储查询结果缓存

### 数据库初始化流程

1. **首次初始化步骤**：
   - 读取配置文件中的数据库连接信息
   - 创建数据库（如不存在）
   - 创建表结构（根据schema定义）
   - 初始化基础数据（股票列表、行业分类等）
   - 设置数据更新计划任务

2. **数据迁移与版本管理**：
   - 使用版本号管理数据库结构变更
   - 提供向上/向下迁移脚本
   - 记录数据库变更日志

3. **数据完整性检查**：
   - 检查数据表结构完整性
   - 验证关键数据是否存在
   - 检查数据一致性

## 数据流设计

1. **数据获取流程**：
   - 通过数据适配器访问AKShare API获取原始数据
   - 数据清洗和标准化处理（保留中文列名和表名）
   - 根据数据特性选择存储策略：
     - 历史数据、结构化数据 → PostgreSQL
     - 实时数据、热点数据、临时数据 → Redis

2. **数据分析流程**：
   - 根据分析需求从适当的数据源读取数据
   - 计算技术指标或基本面指标
   - 生成分析结果并可选择性缓存

3. **策略执行流程**：
   - 加载策略配置
   - 获取分析数据
   - 执行策略逻辑

4. **数据库触发器与自动化数据处理**：
   - 项目使用PostgreSQL数据库触发器实现特定数据表的自动化处理，例如后复权价格的计算。
   - 触发器定义在 <mcfolder name="03_triggers" path="trigger/sql/03_triggers/"></mcfolder> 目录下，并通过 <mcfile name="apply_triggers.py" path="trigger/apply_triggers.py"></mcfile> 脚本进行部署。
   - 主要触发器包括：
     - `trg_update_hfq_factor_on_dividend_change`: 在 `除权除息信息` 表发生变动时触发，调用 `update_hfq_factor_on_dividend_change` 函数。
     - `trg_calculate_hfq_price_on_daily_data_change`: 在 `股票历史行情_不复权` 表有新的不复权行情数据插入或更新时触发，调用 `calculate_and_insert_hfq_price` 函数。
     - `trg_calculate_hfq_price_on_factor_change`: 在 `复权因子表` 中的后复权因子更新时触发，调用 `calculate_and_insert_hfq_price` 函数。
   - 这些触发器确保了在相关基础数据（如除权除息信息、不复权行情、复权因子）发生变化时，衍生数据（如后复权行情）能够自动更新，保证了数据的一致性和实时性。
   - 生成选股结果
   - 评估策略性能

## 技术选型

- **数据获取**：AKShare (轻量级适配而非重复封装)
- **数据存储**：
  - PostgreSQL：存储结构化历史数据，支持复杂查询和数据分析
  - Redis：缓存实时数据和热点数据，提供高速访问和发布/订阅功能
- **数据处理**：pandas, numpy
- **技术分析**：ta-lib
- **可视化**：PyQt6, pyqtgraph
- **配置管理**：PyYAML

## 项目初始化与环境配置

### 环境准备

1. **Python环境**：
   - Python 3.8+
   - 安装依赖：`pip install -r requirements.txt`

2. **数据库环境**：
   - PostgreSQL 13+
   - Redis 6+
   - 确保数据库服务已启动

### 首次运行步骤

1. **配置文件设置**：
   - 复制`config`目录下的示例配置文件，并根据实际环境修改
   - 设置数据库连接参数（主机、端口、用户名、密码等）
   - 配置Redis连接信息

2. **数据库初始化**：
   - 运行`python initialize/db_initializer.py --create-tables`创建数据库表结构
   - 运行`python initialize/db_initializer.py --init-basic-data`初始化基础数据
   - 运行`python initialize/db_initializer.py --check`验证数据库初始化状态

3. **数据获取与更新**：
   - 运行`python scripts/data_update.py --initial`获取初始历史数据
   - 设置定时任务，定期运行`python scripts/data_update.py`更新数据

4. **启动应用**：
   - 运行`python main.py`启动主应用程序
   - 首次运行时会进行系统检查，确保所有组件正常工作

## 命名规范

- **表名和列名**：使用中文命名，与AKShare接口返回的数据保持一致
  - 例如：使用"股票代码"而非"symbol"，使用"交易日期"而非"trade_date"
  - 数据库表名如"股票基本信息"、"日线行情"、"财务数据"、"指数数据"等
  - Redis键前缀如"行情:"、"热门:"、"指标:"等
  - 所有配置文件中的字段名、表名均使用中文，确保与AKShare返回的数据格式一致
  - 这样可以避免在数据处理过程中进行不必要的中英文转换，提高系统效率

## 扩展性设计

- **数据源扩展**：通过适配器模式设计数据获取模块，可轻松添加新数据源（如Wind、Choice等）
- **存储策略扩展**：根据数据特性选择合适的存储方式，可扩展支持其他数据库（如MongoDB、ClickHouse等）
- **策略模块扩展**：使用策略模式设计策略模块，便于添加新策略
- **指标计算扩展**：采用工厂模式设计指标计算模块，便于添加新指标
- **模块间通信**：使用事件驱动架构，实现模块间松耦合
- **数据处理管道**：支持构建灵活的数据处理流水线，便于添加新的数据处理步骤