"""
Core algorithmic trading modules for China A-Shares.
"""
from core.data_feed import load_stock_data, get_market_prefix, get_secid
from core.indicators import add_all_indicators, calculate_ema, calculate_macd, calculate_atr, calculate_rsi
from core.strategy import TrendMomentumStrategy
from core.engine import BacktestEngine, TradeRecord, DailySnapshot
from core.metrics import calculate_performance_metrics
