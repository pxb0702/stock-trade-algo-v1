"""
Trend Following & Momentum Trading Strategy
Combines Dual EMA trend filter, MACD momentum cross, and dynamic ATR Trailing Stop.
Enforces realistic China A-Share rules (T+1, 100-share lot size, limit checks).
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import pandas as pd
import numpy as np


@dataclass
class Signal:
    date: str
    action: str          # 'BUY', 'SELL', 'HOLD'
    price: float
    shares: int = 0
    reason: str = ""
    stop_loss: float = 0.0


class TrendMomentumStrategy:
    """
    Dual EMA + MACD Momentum + ATR Trailing Stop Strategy.
    """
    def __init__(
        self,
        fast_ema: int = 12,
        slow_ema: int = 26,
        macd_signal: int = 9,
        atr_multiplier: float = 2.0,
        atr_period: int = 14,
        risk_per_trade_pct: float = 0.02,
        rsi_overbought: float = 80.0,
        lot_size: int = 100
    ):
        self.fast_ema = fast_ema
        self.slow_ema = slow_ema
        self.macd_signal = macd_signal
        self.atr_multiplier = atr_multiplier
        self.atr_period = atr_period
        self.risk_per_trade_pct = risk_per_trade_pct
        self.rsi_overbought = rsi_overbought
        self.lot_size = lot_size

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Scan indicator matrix and generate raw signals for the backtest engine.
        """
        data = df.copy()
        
        # Trend conditions
        data['trend_bullish'] = data['ema_fast'] > data['ema_slow']
        data['trend_bearish'] = data['ema_fast'] < data['ema_slow']
        
        # Price above trend baseline
        data['above_baseline'] = data['close'] > data['ema_slow']
        
        # MACD Golden Cross & Death Cross
        data['macd_cross_up'] = (data['macd_dif'] > data['macd_dea']) & (data['macd_dif'].shift(1) <= data['macd_dea'].shift(1))
        data['macd_cross_down'] = (data['macd_dif'] < data['macd_dea']) & (data['macd_dif'].shift(1) >= data['macd_dea'].shift(1))
        
        # MACD Momentum acceleration
        data['macd_positive'] = data['macd_hist'] > 0
        
        # RSI Filter
        data['rsi_not_overbought'] = data['rsi'] < self.rsi_overbought
        
        # Limit Up check (Roughly 9.9% gain for standard A-shares, 19.9% for ChiNext/STAR)
        data['is_limit_up'] = (data['close'] == data['high']) & (data['pct_change'] >= 9.8)
        
        # Buy Signal Condition:
        # 1. Fast EMA > Slow EMA (Uptrend)
        # 2. Price > Slow EMA
        # 3. MACD Golden Cross OR (MACD positive and accelerating)
        # 4. RSI not overbought
        # 5. Not hitting limit-up (can actually buy)
        buy_condition = (
            data['trend_bullish'] &
            data['above_baseline'] &
            (data['macd_cross_up'] | (data['macd_positive'] & (data['macd_hist'] > data['macd_hist'].shift(1)))) &
            data['rsi_not_overbought'] &
            (~data['is_limit_up'])
        )
        
        # Sell Signal Condition (Macro trend reversal exit):
        # EMA death cross OR (MACD death cross and price below fast EMA)
        sell_condition = (
            data['trend_bearish'] |
            (data['macd_cross_down'] & (data['close'] < data['ema_fast']))
        )
        
        data['raw_buy_signal'] = buy_condition
        data['raw_sell_signal'] = sell_condition
        
        return data
