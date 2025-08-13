# 股票分析系统

一个基于PyQt6的专业股票分析系统，参考同花顺iFinD、Wind等专业财经软件设计理念，提供全面的股票数据分析和可视化功能。

## 功能特性

### 📊 数据管理
- **多数据源支持**：基于akshare获取实时和历史股票数据
- **智能缓存**：Redis + PostgreSQL多级缓存策略
- **数据完整性**：自动数据验证和清洗

### 📈 技术分析
- **K线图表**：专业级K线图显示，支持多种技术指标
- **技术指标**：MA、MACD、RSI、KDJ等常用技术指标
- **自定义指标**：支持用户自定义技术指标计算

### 🎯 策略回测
- **策略管理**：可视化策略创建和管理
- **回测引擎**：高性能历史数据回测
- **性能分析**：详细的回测结果分析和可视化

### 🖥️ 用户界面
- **现代化UI**：基于PyQt6的专业界面设计
- **主题支持**：深色/浅色主题切换
- **响应式布局**：支持多屏幕和高DPI显示
- **可定制面板**：灵活的窗口布局和面板配置

## 系统架构

```
股票分析系统/
├── ui/                    # 用户界面模块
│   ├── main_window.py     # 主窗口
│   ├── widgets/           # UI组件
│   │   ├── stock_selector.py    # 股票选择器
│   │   ├── chart_widget.py      # 图表组件
│   │   ├── data_table.py        # 数据表格
│   │   ├── info_panel.py        # 信息面板
│   │   └── strategy_panel.py    # 策略面板
│   ├── dialogs/           # 对话框
│   ├── styles/            # 主题样式
│   └── utils/             # UI工具
├── core/                  # 核心业务逻辑
│   ├── analyzer/          # 技术分析
│   ├── backtest/          # 回测引擎
│   └── strategy/          # 策略管理
├── db/                    # 数据库管理
├── fetcher/               # 数据获取
└── config/                # 配置文件
```

## 技术栈

- **界面框架**：PyQt6
- **数据处理**：pandas, numpy
- **图表绘制**：pyqtgraph, matplotlib
- **数据库**：PostgreSQL, Redis
- **数据源**：akshare
- **技术指标**：TA-Lib
- **回测框架**：backtrader

## 安装说明

### 环境要求
- Python 3.8+
- PostgreSQL 12+
- Redis 6.0+

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd stock-a
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置数据库**
```bash
# 创建PostgreSQL数据库
createdb stock_analysis

# 初始化数据库表结构
python initialize/db_initializer.py
```

4. **配置Redis**
```bash
# 启动Redis服务
redis-server
```

5. **配置文件**
```bash
# 复制配置模板并修改
cp config/app.yaml.example config/app.yaml
cp config/connection.yaml.example config/connection.yaml
# 根据实际环境修改配置文件
```

## 使用指南

### 启动应用
```bash
python main.py
```

### 基本操作

1. **股票选择**
   - 使用股票选择器搜索或浏览股票
   - 支持按市场、行业分类筛选
   - 可添加股票到自选列表

2. **图表分析**
   - 查看K线图和技术指标
   - 调整时间周期和复权方式
   - 添加自定义技术指标

3. **数据查看**
   - 查看历史行情数据
   - 实时行情监控
   - 财务数据分析

4. **策略回测**
   - 创建和编辑交易策略
   - 设置回测参数
   - 查看回测结果和性能指标

## 配置说明

### 数据库配置 (config/connection.yaml)
```yaml
postgresql:
  host: localhost
  port: 5432
  database: stock_analysis
  username: your_username
  password: your_password

redis:
  host: localhost
  port: 6379
  db: 0
```

### 应用配置 (config/app.yaml)
```yaml
app:
  name: "股票分析系统"
  version: "1.0.0"
  theme: "dark"  # dark/light
  
data:
  cache_expire: 3600  # 缓存过期时间(秒)
  update_interval: 60  # 数据更新间隔(秒)
```

## 开发指南

### 代码规范
- 遵循PEP 8 Python代码规范
- 使用中文注释和文档字符串
- 数据库表名和字段名使用中文（技术字段除外）

### 数据获取优先级
1. 内存缓存
2. Redis持久化缓存
3. PostgreSQL数据库
4. akshare API接口

### 添加新功能
1. 在相应模块下创建新文件
2. 实现业务逻辑
3. 添加UI组件（如需要）
4. 更新配置文件
5. 编写测试用例

## 项目结构详解

### UI模块 (ui/)
- **main_window.py**: 主窗口，整合所有UI组件
- **widgets/**: 可复用的UI组件
- **dialogs/**: 对话框组件
- **styles/**: 主题和样式定义
- **utils/**: UI辅助工具

### 核心模块 (core/)
- **analyzer/**: 技术分析和指标计算
- **backtest/**: 回测引擎和性能分析
- **strategy/**: 策略管理和执行

### 数据模块 (db/, fetcher/)
- **db/**: 数据库连接和操作
- **fetcher/**: 外部数据源接口

## 常见问题

### Q: 如何添加新的技术指标？
A: 在 `core/analyzer/technical_indicators.py` 中添加指标计算函数，然后在UI中添加相应的显示逻辑。

### Q: 数据更新频率如何设置？
A: 在 `config/app.yaml` 中修改 `update_interval` 参数。

### Q: 如何备份数据？
A: 使用PostgreSQL的pg_dump工具备份数据库，Redis数据可通过RDB文件备份。

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 联系方式

- 项目主页：[github.com/coastalbeach/stock-a]
- 问题反馈：[Issues]
- 邮箱：[480436175@qq.com]


---

**注意**: 本系统仅供学习和研究使用，不构成投资建议。投资有风险，入市需谨慎。
