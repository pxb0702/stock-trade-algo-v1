# Stock Trade Algo v1 (A股趋势动量量化交易系统)

一个专为 **中国A股市场 (China A-Shares)** 设计的高性能量化回测与交易策略系统。内置双均线趋势过滤、MACD 动量共振、ATR 动态追踪止损，以及真实 A 股交易制度模拟（严格 **T+1 制度**、**100股 (1手) 整数倍约束**、**印花税**、**券商佣金最低5元** 与 **滑点**）。

系统包含 **模块化量化核心**、**丰富 CLI 终端回测器** 以及基于 **Flask + Apache ECharts 的交互式 Web 视觉终端**。

---

## 🌟 核心特性

1. **真实 A 股微观结构仿真**：
   - **T+1 制度**：当日买入股票自动冻结，次日开盘方可卖出。
   - **整手交易约束**：买入数量严格向下取整至 100 股（1手）的整数倍。
   - **全真交易摩擦成本**：
     - 券商佣金：万三（0.03%），每笔最低 5 元起收。
     - 印花税：千分之 0.5（0.05%，仅卖出端征收）。
     - 中证登过户费：十万分之一（0.001%）。
     - 冲击成本与滑点：默认 0.1%。

2. **核心策略逻辑：双均线趋势 + MACD 动量 + ATR 追踪止损**：
   - **入场过滤器**：
     1. 快线 EMA（如 12 日）> 慢线 EMA（如 26 日）且价格位于慢线之上（均线多头排列）；
     2. MACD 金叉或柱体红柱加速扩张（动量共振确认）；
     3. 过滤极端超买（RSI < 80）与涨停板（无法买入）。
   - **动态仓位管理 (Volatility Position Sizing)**：
     - 依据单笔风险预算（如总资产 2%）与 ATR 波动率自适应计算开仓股数：
       $$\text{Target Shares} = \lfloor \frac{\text{Equity} \times \text{RiskPct}}{\text{ATR} \times M \times 100} \rfloor \times 100$$
   - **出场与风控**：
     - **ATR 移动止损 (Trailing Stop)**：入场后设定初始止损为 $P_{\text{entry}} - M \times \text{ATR}$。随着价格创出新高，止损价逐日向上推升，**绝不向下移动**，锁定波段利润；
     - **宏观趋势逆转**：快慢线死叉或 MACD 破位时有序平仓。

3. **双层回测界面**：
   - **CLI 终端**：使用 `rich` 呈现彩色绩效看板、回撤分析与交易流水明细。
   - **Web 仪表盘**：内置专业暗色交易终端（Bloomberg / TradingView 风格），支持 ECharts K线十字光标、买卖标记点交互、资金净值与水下回撤对比曲线、参数实时热调整重跑。

4. **高韧性数据源管道**：
   - 自动对接全球 CDN（yfinance A股节点）与东方财富官方行情 API；
   - 本地自动持久化 CSV 缓存（`data/cache/`），秒级读取；
   - 内置离线防崩溃仿真数据引擎，断网环境亦可正常测试。

---

## 📁 目录架构

```
algo_trading_v1/
├── config.py                 # 全局配置（资金、交易费率、预设观察池）
├── requirements.txt          # Python 依赖清单
├── README.md                 # 完整系统与策略说明
├── run_backtest.py           # CLI 命令行回测脚本
├── start_dashboard.py        # 一键启动 Web 交互终端
├── core/
│   ├── __init__.py
│   ├── data_feed.py          # 多源行情数据采集与缓存
│   ├── indicators.py         # 向量化技术指标计算 (EMA, MACD, ATR, RSI, Bollinger)
│   ├── strategy.py           # 趋势动量与风控信号逻辑
│   ├── engine.py             # A股事件驱动回测引擎 (T+1, 手数, 费用)
│   └── metrics.py            # 量化投资绩效评估 (CAGR, Sharpe, MaxDD, WinRate 等)
└── web/
    ├── app.py                # Flask 后端 RESTful API
    ├── static/
    │   ├── css/style.css     # 暗色量化终端主题
    │   └── js/app.js         # ECharts 联动与回测状态管理
    └── templates/
        └── index.html        # Web 交互控制台模板
```

---

## 🚀 快速启动

### 1. 运行 CLI 命令行回测

直接在终端执行回测，查看详细指标与最近交易记录：

```bash
# 默认回测 沪深300 ETF (510300)
python algo_trading_v1/run_backtest.py --code 510300 --start 2021-01-01 --end 2024-12-31

# 回测 比亚迪 (002594)
python algo_trading_v1/run_backtest.py --code 002594 --start 2021-01-01 --end 2024-12-31

# 回测 贵州茅台 (600519)，自定义参数
python algo_trading_v1/run_backtest.py --code 600519 --capital 200000 --fast 10 --slow 30 --atr_mult 2.5
```

**CLI 参数说明**：
- `--code`: 股票或 ETF 代码（如 `510300`, `600519`, `002594`, `300750`）
- `--start`: 起始日期（YYYY-MM-DD）
- `--end`: 结束日期（YYYY-MM-DD）
- `--capital`: 初始本金（默认 100,000 元）
- `--fast`: 快线 EMA 周期（默认 12）
- `--slow`: 慢线 EMA 周期（默认 26）
- `--signal`: MACD 信号线平滑周期（默认 9）
- `--atr_mult`: ATR 追踪止损倍数（默认 2.0）
- `--risk`: 单笔最大风险预算比例（默认 0.02 即 2%）

---

### 2. 启动交互式 Web 视觉终端

执行以下命令启动 Web 界面：

```bash
python algo_trading_v1/start_dashboard.py
```

终端启动后将在本地 `http://127.0.0.1:5000` 监听，并自动在浏览器中打开页面：
1. **顶部导航**：一键切换热门标的预设（沪深300ETF、贵州茅台、比亚迪、宁德时代、中国平安、证券ETF、创业板ETF等）；
2. **左侧控制面板**：调整日期、初始资金、EMA/MACD 参数、ATR 追踪倍数与风险预算；
3. **主看板**：
   - 6 大核心绩效指标卡（总收益、年化 CAGR、最大回撤、夏普比率、胜率与盈亏比、期末净值）；
   - **K线形态与交易信号图**：展示蜡烛图、EMA 12/26 双线、成交量、MACD 指标柱，以及入场（▲）与平仓出场（▼）的视觉标记点；
   - **净值曲线 vs 基准图**：展示策略动态资产净值与买入持有基准对比，以及水下回撤（Underwater Drawdown）；
   - **完整交易流水表**：展示每笔交易的买入日期/价格、卖出日期/价格、股数、手续费、净盈亏、收益率与平仓原因。

---

## 📊 评估指标说明

- **累计收益率 (Total Return)**：回测周期内账户总资产净变化率。
- **基准收益率 (Benchmark Return)**：同期基准标的“买入并持有”收益率。
- **超额收益 (Alpha)**：策略相对于基准的超额收益率。
- **复合年化收益率 (CAGR)**：按标准 250 交易日折算的复合年化收益。
- **最大回撤 (Max Drawdown)**：历史上资产从最高峰值向下跌落的最大幅度。
- **夏普比率 (Sharpe Ratio)**：以 2.5% 无风险利率计算的超额年化收益与波动率之比。
- **索提诺比率 (Sortino Ratio)**：仅对下行波动进行惩罚的风险调整后收益指标。
- **胜率 (Win Rate)**：盈利交易笔数 / 总平仓交易笔数。
- **获利因子 (Profit Factor)**：总盈利金额 / 总亏损金额。
- **盈亏比 (Win/Loss Ratio)**：平均单笔盈利 / 平均单笔亏损。
