"""
Technical Indicators Calculation Module
Vectorized, robust implementations supporting numpy and pandas.
"""

import numpy as np
import pandas as pd
from typing import Tuple


def calculate_ema(series: pd.Series, span: int) -> pd.Series:
    """Calculate Exponential Moving Average (EMA)."""
    return series.ewm(span=span, adjust=False).mean()


def calculate_sma(series: pd.Series, window: int) -> pd.Series:
    """Calculate Simple Moving Average (SMA)."""
    return series.rolling(window=window, min_periods=1).mean()


def calculate_macd(
    close: pd.Series,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate MACD indicator:
    - DIF (Fast EMA - Slow EMA)
    - DEA (Signal line: EMA of DIF)
    - MACD Histogram (2 * (DIF - DEA) in Chinese standard convention)
    """
    ema_fast = calculate_ema(close, fast_period)
    ema_slow = calculate_ema(close, slow_period)
    dif = ema_fast - ema_slow
    dea = calculate_ema(dif, signal_period)
    macd_hist = 2.0 * (dif - dea)
    return dif, dea, macd_hist


def calculate_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14
) -> pd.Series:
    """Calculate Average True Range (ATR)."""
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    atr = tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    atr = atr.bfill().fillna(0.0)
    return atr


def calculate_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index (RSI)."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    
    rs = avg_gain / (avg_loss + 1e-10)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.fillna(50.0)


def calculate_bollinger_bands(
    close: pd.Series,
    period: int = 20,
    num_std: float = 2.0
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate Bollinger Bands (Upper, Middle, Lower)."""
    middle = close.rolling(window=period, min_periods=1).mean()
    std = close.rolling(window=period, min_periods=1).std(ddof=0).fillna(0.0)
    upper = middle + num_std * std
    lower = middle - num_std * std
    return upper, middle, lower


def add_all_indicators(
    df: pd.DataFrame,
    fast_ema: int = 12,
    slow_ema: int = 26,
    macd_signal: int = 9,
    atr_period: int = 14,
    rsi_period: int = 14,
    sma_fast: int = 20,
    sma_trend: int = 60
) -> pd.DataFrame:
    """
    Enrich OHLCV dataframe with comprehensive indicators for Dual-Regime strategy.
    """
    data = df.copy()
    
    # Moving Averages
    data['ema_fast'] = calculate_ema(data['close'], fast_ema)
    data['ema_slow'] = calculate_ema(data['close'], slow_ema)
    data['sma_20'] = calculate_sma(data['close'], sma_fast)
    data['sma_60'] = calculate_sma(data['close'], sma_trend)
    data['sma_120'] = calculate_sma(data['close'], 120)
    data['vol_ma5'] = calculate_sma(data['volume'], 5)
    
    # MACD
    dif, dea, hist = calculate_macd(data['close'], fast_ema, slow_ema, macd_signal)
    data['macd_dif'] = dif
    data['macd_dea'] = dea
    data['macd_hist'] = hist
    
    # ATR & RSIs
    data['atr'] = calculate_atr(data['high'], data['low'], data['close'], atr_period)
    data['rsi'] = calculate_rsi(data['close'], rsi_period)
    data['rsi_fast'] = calculate_rsi(data['close'], 6)
    
    # Bollinger Bands
    bb_up, bb_mid, bb_low = calculate_bollinger_bands(data['close'], 20, 2.0)
    data['bb_upper'] = bb_up
    data['bb_middle'] = bb_mid
    data['bb_lower'] = bb_low
    
    return data
