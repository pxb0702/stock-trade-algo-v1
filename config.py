"""
Configuration file for China A-Shares Algorithmic Trading Framework v2
"""

from dataclasses import dataclass
from typing import Dict, Any, List

@dataclass
class TradingConfig:
    # Capital
    initial_cash: float = 100_000.0   # Default 100,000 RMB
    
    # A-Share Market Rules
    lot_size: int = 100              # Minimum buy unit: 100 shares (1 手)
    t_plus_one: bool = True          # T+1 trading settlement rule
    max_position_pct: float = 0.95   # Max portfolio capital allocated to a single asset
    
    # Costs & Slippage (Realistic A-Share Broker Structure)
    commission_rate: float = 0.0003  # Broker commission: 0.03% (万三)
    min_commission: float = 5.0      # Minimum commission per trade: 5 RMB (各券商普遍有5元起收)
    stamp_duty_rate: float = 0.0005  # Stamp duty: 0.05% on sell side only (印花税减半后 0.05%)
    transfer_fee_rate: float = 0.00001 # Transfer fee: 0.001% (中证登过户费)
    slippage_pct: float = 0.001      # Slippage: 0.1% per trade

    # Strategy v2: Dual-Regime (Trend Momentum + Oversold Swing Reversal)
    enable_regime_filter: bool = True # Filter bear markets using SMA60 slope
    enable_oversold_swing: bool = True# Capture panic capitulation bounces
    fast_ema: int = 12               # Fast EMA period
    slow_ema: int = 26               # Slow EMA period
    macd_signal: int = 9             # MACD signal line period
    sma_trend: int = 60              # Major trend baseline (SMA 60)
    sma_fast: int = 20               # Short-term trend (SMA 20)
    slope_lookback: int = 5          # Trend slope lookback bars
    rsi_period: int = 14             # Standard RSI period
    rsi_fast_period: int = 6         # Fast RSI for oversold detection
    
    # Multi-Stage Risk & Profit Management
    take_profit_pct: float = 0.08    # Profit target: default 8% (锁定波段收益)
    stop_loss_pct: float = 0.035     # Hard stop loss: default 3.5% (单笔严格止损)
    atr_multiplier: float = 2.2      # Trailing stop distance = 2.2 * ATR
    atr_period: int = 14             # ATR calculation period

# Default watchlist for China A-Shares
DEFAULT_WATCHLIST = [
    {
        "code": "002463",
        "name": "沪电股份",
        "market": "SZ",
        "desc": "PCB印制电路板龙头 | AI服务器高多层板及新能源汽车车载板核心供应商"
    },
    {
        "code": "688629",
        "name": "华丰科技",
        "market": "SH",
        "desc": "防务与通讯连接器龙头 | 高速背板连接器核心标的，深度受益算力基础设施"
    },
    {
        "code": "002475",
        "name": "立讯精密",
        "market": "SZ",
        "desc": "精密制造与消费电子龙头 | 苹果核心供应链，汽车线束与通信业务多轮驱动"
    },
    {
        "code": "600176",
        "name": "中国巨石",
        "market": "SH",
        "desc": "玻璃纤维全球绝对龙头 | 规模与成本壁垒极高，风电与高端复材需求支撑"
    },
    {
        "code": "600183",
        "name": "生益科技",
        "market": "SH",
        "desc": "覆铜板CCL全球领先 | 高频高速覆铜板技术领先，AI算力及通信升级受益"
    },
    {
        "code": "603986",
        "name": "兆易创新",
        "market": "SH",
        "desc": "存储芯片与MCU龙头 | NOR Flash全球前列，汽车级MCU与DRAM协同布局"
    },
    {
        "code": "601995",
        "name": "中金公司",
        "market": "SH",
        "desc": "头部投行券商旗舰 | 跨境业务与投资银行综合实力卓越，财富管理快速增长"
    },
    {
        "code": "688825",
        "name": "长鑫科技",
        "market": "SH",
        "desc": "存储芯片自主创新核心标的 | 国产DRAM存储产业链核心基石，成长空间广阔"
    },
    {
        "code": "600089",
        "name": "特变电工",
        "market": "SH",
        "desc": "输变电与多晶硅龙头 | 全球特高压核心设备供应商，兼具新能源与煤电双轮驱动"
    }
]
