"""
Dual-Regime Adaptive Strategy (Trend Momentum + Oversold Swing Reversal)
Combines macro trend regime identification, multi-stage profit lock,
and extreme panic capitulation bounce recognition.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import pandas as pd
import numpy as np


class DualRegimeAdaptiveStrategy:
    """
    Dual-Regime Adaptive Quantitative Strategy:
    1. Trend Momentum Mode (顺势波段突破): Operates during bullish macro regimes.
    2. Oversold Swing Reversal Mode (超跌共振反弹): Captures sharp capitulation rebounds.
    """
    def __init__(
        self,
        fast_ema: int = 12,
        slow_ema: int = 26,
        macd_signal: int = 9,
        sma_trend: int = 60,
        sma_fast: int = 20,
        slope_lookback: int = 5,
        enable_regime_filter: bool = True,
        enable_oversold_swing: bool = True,
        lot_size: int = 100
    ):
        self.fast_ema = fast_ema
        self.slow_ema = slow_ema
        self.macd_signal = macd_signal
        self.sma_trend = sma_trend
        self.sma_fast = sma_fast
        self.slope_lookback = slope_lookback
        self.enable_regime_filter = enable_regime_filter
        self.enable_oversold_swing = enable_oversold_swing
        self.lot_size = lot_size

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate dual-regime buy and exit signals across the dataset.
        """
        data = df.copy()
        
        # 1. Macro Trend Slope Filter
        sma60_slope = data['sma_60'] - data['sma_60'].shift(self.slope_lookback)
        if self.enable_regime_filter:
            data['is_bull_regime'] = (data['close'] > data['sma_60']) & (sma60_slope > 0)
        else:
            data['is_bull_regime'] = True

        # 2. Limit-up check (can't buy if locked at ceiling)
        data['is_limit_up'] = (data['close'] == data['high']) & (data['pct_change'] >= 9.8)
        
        # 3. Mode A: Trend Momentum Signal
        trend_entry = (
            data['is_bull_regime'] &
            (data['close'] > data['sma_20']) &
            (data['ema_fast'] > data['ema_slow']) &
            (data['macd_hist'] > 0) &
            (data['macd_hist'] > data['macd_hist'].shift(1)) &
            (data['rsi'] < 70.0) &
            (~data['is_limit_up'])
        )

        # 4. Mode B: Oversold Panic Reversal Signal
        if self.enable_oversold_swing:
            candle_range = data['high'] - data['low'] + 1e-6
            lower_rejection = (data['close'] > data['open']) & (data['close'] > data['low'] + candle_range * 0.45)
            oversold_entry = (
                ((data['rsi_fast'] < 22) | (data['low'] < data['bb_lower'])) &
                lower_rejection &
                (data['macd_hist'] > data['macd_hist'].shift(1)) &
                (~data['is_limit_up'])
            )
        else:
            oversold_entry = pd.Series(False, index=data.index)

        data['raw_buy_trend'] = trend_entry
        data['raw_buy_oversold'] = oversold_entry
        data['raw_buy_signal'] = trend_entry | oversold_entry

        # Macro Trend breakdown for exit
        data['raw_sell_signal'] = (data['close'] < data['sma_20']) | (data['ema_fast'] < data['ema_slow'])
        
        return data


# Backward compatibility alias
TrendMomentumStrategy = DualRegimeAdaptiveStrategy
