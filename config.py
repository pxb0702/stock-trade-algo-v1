"""
Configuration file for China A-Shares Algorithmic Trading Framework v1
"""

from dataclasses import dataclass
from typing import Dict, Any

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

    # Risk Management
    risk_per_trade_pct: float = 0.02 # Risk budget per trade: 2% of total equity
    atr_multiplier: float = 2.0      # Trailing stop distance = 2.0 * ATR
    atr_period: int = 14             # ATR calculation period

    # Strategy Parameters (EMA + MACD Trend Momentum)
    fast_ema: int = 12               # Fast EMA period
    slow_ema: int = 26               # Slow EMA period
    macd_signal: int = 9             # MACD signal line period
    rsi_period: int = 14             # RSI period for momentum filter
    rsi_overbought: float = 80.0     # RSI overbought threshold

# Default watchlist for China A-Shares
DEFAULT_WATCHLIST = [
    {"code": "510300", "name": "沪深300ETF", "market": "SH", "desc": "CSI 300 Index ETF (Broad Market)"},
    {"code": "600519", "name": "贵州茅台", "market": "SH", "desc": "Kweichow Moutai (Consumer Leader)"},
    {"code": "002594", "name": "比亚迪", "market": "SZ", "desc": "BYD Company (EV & Battery Leader)"},
    {"code": "300750", "name": "宁德时代", "market": "SZ", "desc": "CATL (Lithium Battery Leader)"},
    {"code": "601318", "name": "中国平安", "market": "SH", "desc": "Ping An Insurance (Financials)"},
    {"code": "512880", "name": "证券ETF", "market": "SH", "desc": "Securities Sector ETF (High Beta)"},
    {"code": "159915", "name": "创业板ETF", "market": "SZ", "desc": "ChiNext Index ETF (Tech Growth)"},
    {"code": "000001", "name": "平安银行", "market": "SZ", "desc": "Ping An Bank (Commercial Bank)"},
]
