"""
Core algorithmic trading modules for China A-Shares.
"""
from core.data_feed import load_stock_data, get_market_prefix, get_secid, resolve_stock_name
from core.indicators import add_all_indicators, calculate_ema, calculate_macd, calculate_atr, calculate_rsi
from core.strategy import TrendMomentumStrategy, DualRegimeAdaptiveStrategy
from core.engine import BacktestEngine, TradeRecord, DailySnapshot
from core.metrics import calculate_performance_metrics
from core.watchlist import load_watchlist, save_watchlist, add_stock_to_watchlist, remove_stock_from_watchlist, reset_watchlist_to_default
