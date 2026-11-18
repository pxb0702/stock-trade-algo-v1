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
        "code": "601398",
        "name": "工商银行",
        "market": "SH",
        "desc": "高股息金融 | 分红总额居A股首位，股息率约3.9%，长线资金青睐"
    },
    {
        "code": "600036",
        "name": "招商银行",
        "market": "SH",
        "desc": "股份行龙头 | 股息率约4.79%，兼具高分红与零售银行盈利弹性"
    },
    {
        "code": "600941",
        "name": "中国移动",
        "market": "SH",
        "desc": "通信运营商 | 现金流充沛，股息率超4.6%，受益算力网络与AI政企"
    },
    {
        "code": "601088",
        "name": "中国神华",
        "market": "SH",
        "desc": "煤炭能源龙头 | 股息率接近5%，长协煤占比高，盈利分红稳定性强"
    },
    {
        "code": "600938",
        "name": "中国海油",
        "market": "SH",
        "desc": "石油石化龙头 | 桶油成本控制优异，股息率稳健，高自由现金流"
    },
    {
        "code": "600519",
        "name": "贵州茅台",
        "market": "SH",
        "desc": "白酒消费龙头 | 核心资产代表，分红超350亿，股息率提升至3.7%以上"
    },
    {
        "code": "000333",
        "name": "美的集团",
        "market": "SZ",
        "desc": "白色家电龙头 | 高股息红利与品牌出海双重属性，海外OBM贡献增量"
    },
    {
        "code": "300750",
        "name": "宁德时代",
        "market": "SZ",
        "desc": "新能源电池龙头 | 全球动力与储能绝对龙头，市占率与单位盈利韧性强"
    },
    {
        "code": "300308",
        "name": "中际旭创",
        "market": "SZ",
        "desc": "AI算力光模块 | 全球光模块核心供应商，高速率光模块具备估值弹性"
    },
    {
        "code": "603259",
        "name": "药明康德",
        "market": "SH",
        "desc": "医药CXO龙头 | 研发外包龙头，受益创新药投融资回暖与新质生产力"
    }
]
