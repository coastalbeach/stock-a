# PostgreSQL 数据库触发器与函数

本目录包含用于增强 PostgreSQL 数据库功能的 SQL 脚本，主要目标是实现基于数据库事件的自动化数据处理，特别是针对股票后复权价格的计算。

## 目录结构

- `sql/`: 存放所有的 SQL DDL 和 DML 脚本，包括表创建、函数定义和触发器创建。
- `apply_triggers.py`: Python 脚本，用于将 `sql/` 目录下的脚本统一部署到 PostgreSQL 数据库中。

## 功能概述

核心功能是通过数据库触发器，在相关数据发生变化时，自动计算并更新股票的后复权历史行情数据。主要涉及以下几个方面：

1.  **除权除息信息表 (`除权除息信息`)**: 存储股票的送股、转增、派息、配股等事件的详细信息。这是计算复权因子的基础。
2.  **复权因子表 (`复权因子表`)**: 存储每只股票每日的前复权因子和后复权因子。这些因子由 Python 程序根据 `除权除息信息` 计算并更新（理想情况下），或者在更复杂的数据库函数中计算。
3.  **触发器函数与触发器**:
    *   当 `除权除息信息` 表发生变动（INSERT, UPDATE, DELETE）时，触发器 `trg_update_hfq_factor_on_dividend_change` (定义于 `sql/03_triggers/adjustment_factor_triggers.sql`) 会调用函数 `update_hfq_factor_on_dividend_change` (定义于 `sql/01_functions/adjustment_factor_functions.sql`)。此函数负责根据最新的除权除息信息更新 `复权因子表` 中对应股票的后复权因子。
    *   当 `股票历史行情_不复权` 表有新的不复权行情数据插入或更新时，触发器 `trg_calculate_hfq_price_on_daily_data_change` (定义于 `sql/03_triggers/market_data_triggers.sql`) 会调用函数 `calculate_and_insert_hfq_price` (定义于 `sql/01_functions/adjustment_factor_functions.sql`)。
    *   当 `复权因子表` 中的 `后复权因子` 列发生更新时，触发器 `trg_calculate_hfq_price_on_factor_change` (定义于 `sql/03_triggers/adjustment_factor_triggers.sql`) 也会调用函数 `calculate_and_insert_hfq_price`。
        *   **优化说明**: 此触发器仅在 `后复权因子` 实际发生变化时触发，并且仅监听 `UPDATE` 操作，因为 `INSERT` 操作通常伴随着对 `股票历史行情_不复权` 表的插入，由上述 `trg_calculate_hfq_price_on_daily_data_change` 触发器处理，避免了重复计算。
    *   函数 `calculate_and_insert_hfq_price` 的核心逻辑是：根据对应股票和日期的不复权价格以及最新的后复权因子，计算出后复权价格，并将其插入或更新到 `股票历史行情_后复权` 表中。

## 设计思路与权衡

-   **数据流**: 
    1.  Python 程序获取股票的除权除息信息，并存入 `除权除息信息` 表。
    2.  Python 程序（或一个复杂的数据库函数）根据 `除权除息信息` 计算每日的后复权因子，并存入 `复权因子表`。
    3.  Python 程序获取股票的不复权历史行情数据，并存入 `股票历史行情_不复权` 表。
    4.  当不复权行情数据写入或复权因子更新时，触发器自动计算并填充 `股票历史行情_后复权` 表。

-   **简化处理**: 
    *   后复权因子的计算是一个复杂的过程，涉及到追溯调整。在本实现中，`update_hfq_factor_on_dividend_change` 函数并未直接在数据库中完成这一复杂计算，而是假设这一计算由 Python 端或其他专门流程处理，并将结果更新到 `复权因子表`。
    *   `calculate_and_insert_hfq_price` 函数直接使用 `复权因子表` 中的因子进行价格转换，简化了触发器内的逻辑。

-   **优点**: 
    *   自动化：一旦不复权数据和复权因子准备就绪，后复权数据的生成是自动的。
    *   数据一致性：有助于确保 `股票历史行情_后复权` 表与不复权数据及复权因子保持一致。
    *   减轻应用层负担：部分数据转换逻辑下沉到数据库层面。

-   **潜在挑战与改进方向**: 
    *   **复权因子计算的复杂性**: 精确的、历史追溯的复权因子计算在纯 SQL 中实现可能非常复杂且性能不高。目前依赖外部程序更新 `复权因子表` 是一个务实的折衷。
    *   **性能**: 大量数据写入时，触发器的执行会增加开销。需要监控和优化。
    *   **错误处理与调试**: 数据库触发器的调试相对复杂。
    *   **依赖顺序**: `复权因子表` 的数据必须在相应的不复权行情数据写入之前或同时准备好，否则计算出的后复权价格可能不正确（或使用默认因子）。

## 如何使用 `apply_triggers.py`

该脚本提供了通过命令行将 `sql/` 目录下的 SQL 文件应用到数据库的功能。

**先决条件**: 

*   确保项目根目录下的 `config/connection.yaml` 文件中已正确配置 PostgreSQL 数据库连接信息。
*   确保相关的 Python 依赖已安装 (如 `psycopg2-binary`, `PyYAML`)。
*   确保 `utils.logger.LoggerManager` 和 `data.storage.postgresql_manager.PostgreSQLManager` 模块可用且功能正常。

**列出可用的SQL文件及顺序**:

```bash
python trigger/apply_triggers.py --list
```

**应用所有SQL文件 (按预定顺序)**:

```bash
python trigger/apply_triggers.py --apply all
```

**应用单个SQL文件**:

```bash
python trigger/apply_triggers.py --apply create_ex_dividend_info_table.sql
```

(将 `create_ex_dividend_info_table.sql` 替换为实际要应用的SQL文件名)

**执行顺序**:

脚本内置了推荐的SQL文件执行顺序 (`SQL_EXECUTION_ORDER` 变量)，通常遵循：
1.  创建表结构 (如 `create_ex_dividend_info_table.sql`, `create_adjustment_factor_table.sql`)
2.  创建函数 (如 `sql/01_functions/adjustment_factor_functions.sql`, `sql/01_functions/periodic_data_functions.sql`)
3.  创建触发器 (如 `sql/03_triggers/adjustment_factor_triggers.sql`, `sql/03_triggers/market_data_triggers.sql`)

如果选择 `--apply all`，脚本会严格按照此顺序执行。如果单个文件执行失败，后续将不会执行，且已执行的更改会回滚。

**重要说明**: 先前存在于项目根目录下的独立触发器SQL文件 (例如 `trigger_on_dividend_info_change.sql`, `trigger_on_unadjusted_price_change.sql`, `trigger_on_adjustment_factor_change.sql`) 已被整合到 `sql/03_triggers/` 目录下的对应文件中 (主要是 `adjustment_factor_triggers.sql` 和 `market_data_triggers.sql`)。这些独立的旧文件已被删除，以避免重复定义和潜在冲突。请始终参考 `sql/03_triggers/` 中的脚本作为最新的触发器定义。

## 注意事项

*   在生产环境中应用这些脚本前，请务必在测试环境中充分测试。
*   理解每个SQL脚本的作用和依赖关系非常重要。
*   如果数据库中已存在同名对象（表、函数、触发器），CREATE IF NOT EXISTS 语句会跳过创建，但如果需要更新定义，则可能需要先手动 DROP 对应的对象，或修改SQL脚本使用 `CREATE OR REPLACE` (对于函数和视图) 或先 `DROP` 再 `CREATE` (对于表和触发器，注意数据迁移)。本实现中的函数使用了 `CREATE OR REPLACE`，表使用了 `CREATE TABLE IF NOT EXISTS`。