"""
China A-Share Backtesting Engine v2
Event-driven simulation honoring T+1 settlement, 100-share lot sizes,
stamp duty, broker commission minimums, slippage,
and multi-stage profit lock / hard stop loss / ATR trailing stops.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np

from config import TradingConfig


@dataclass
class TradeRecord:
    trade_id: int
    stock_code: str
    entry_date: str
    entry_price: float
    exit_date: str
    exit_price: float
    shares: int
    gross_pnl: float
    total_fees: float
    net_pnl: float
    return_pct: float
    holding_days: int
    exit_reason: str


@dataclass
class DailySnapshot:
    date: str
    cash: float
    shares: int
    stock_value: float
    total_equity: float
    daily_return: float
    drawdown: float
    benchmark_equity: float
    in_position: bool


class BacktestEngine:
    """
    Realistic A-Share Backtesting Engine with Multi-Stage Risk & Profit Architecture.
    """
    def __init__(self, config: Optional[TradingConfig] = None):
        self.config = config or TradingConfig()
        
    def run(self, df: pd.DataFrame, stock_code: str = "000001") -> Dict[str, Any]:
        """
        Execute backtest over historical dataset.
        df must contain: date, open, high, low, close, volume, indicators, raw signals.
        """
        data = df.copy().reset_index(drop=True)
        n_bars = len(data)
        if n_bars < 20:
            raise ValueError(f"Insufficient historical data ({n_bars} bars)")

        # State Variables
        cash = float(self.config.initial_cash)
        shares_held = 0           # Total shares held
        shares_available = 0      # Shares available to sell today (T+1 rule)
        shares_frozen = 0         # Shares bought today (locked until tomorrow)
        
        entry_price = 0.0
        entry_date = ""
        entry_index = 0
        current_stop_price = 0.0
        highest_price_seen = 0.0
        
        trades: List[TradeRecord] = []
        equity_curve: List[DailySnapshot] = []
        
        # Benchmark buy & hold initialization
        benchmark_start_close = data.loc[0, 'close']
        benchmark_initial_shares = int(self.config.initial_cash / benchmark_start_close)
        benchmark_initial_cash = self.config.initial_cash - (benchmark_initial_shares * benchmark_start_close)
        
        peak_equity = cash
        trade_counter = 0

        # Start evaluation after warmup period
        warmup = max(60, self.config.sma_trend + self.config.slope_lookback)

        for i in range(n_bars):
            row = data.iloc[i]
            bar_date = str(row['date'])[:10]
            open_p = float(row['open'])
            high_p = float(row['high'])
            low_p = float(row['low'])
            close_p = float(row['close'])
            atr_val = float(row.get('atr', close_p * 0.02))
            sma20_val = float(row.get('sma_20', close_p))
            
            # --- 1. Daily T+1 Settlement (Morning Routine) ---
            shares_available += shares_frozen
            shares_frozen = 0
            
            stock_value = shares_held * close_p
            total_equity = cash + stock_value
            peak_equity = max(peak_equity, total_equity)
            drawdown = (total_equity - peak_equity) / peak_equity if peak_equity > 0 else 0.0
            benchmark_equity = benchmark_initial_cash + (benchmark_initial_shares * close_p)
            
            # --- 2. Check Exits for Existing Positions ---
            if shares_held > 0 and shares_available > 0 and i > entry_index:
                highest_price_seen = max(highest_price_seen, high_p)
                max_gain = (high_p - entry_price) / entry_price
                cur_gain = (close_p - entry_price) / entry_price
                
                # Dynamic ATR Trailing Stop calculation
                trailing_stop_level = highest_price_seen - (atr_val * self.config.atr_multiplier)
                
                exit_triggered = False
                exit_price = 0.0
                exit_reason = ""
                
                # Rule 1: Target Take Profit
                if max_gain >= self.config.take_profit_pct:
                    exit_triggered = True
                    target_p = entry_price * (1.0 + self.config.take_profit_pct)
                    exit_price = target_p * (1.0 - self.config.slippage_pct)
                    exit_reason = f"Target Take Profit (+{self.config.take_profit_pct*100:.1f}%)"
                    
                # Rule 2: Hard Stop Loss (Protects against sharp drops)
                elif (entry_price - low_p) / entry_price >= self.config.stop_loss_pct and max_gain < 0.015:
                    exit_triggered = True
                    stop_p = entry_price * (1.0 - self.config.stop_loss_pct)
                    exit_price = stop_p * (1.0 - self.config.slippage_pct)
                    exit_reason = f"Hard Stop Loss (-{self.config.stop_loss_pct*100:.1f}%)"
                    
                # Rule 3: ATR Trailing Stop (Ratchets to lock in profits once gained > 2%)
                elif low_p <= trailing_stop_level and max_gain >= 0.02:
                    exit_triggered = True
                    exit_price = max(low_p, trailing_stop_level) * (1.0 - self.config.slippage_pct)
                    exit_reason = "ATR Trailing Profit Lock"
                    
                # Rule 4: Trend Breakdown Exit (Cut losses when breaking SMA20)
                elif close_p < sma20_val and cur_gain < -0.01:
                    exit_triggered = True
                    exit_price = close_p * (1.0 - self.config.slippage_pct)
                    exit_reason = "Trend Breakdown (SMA20 Break)"
                    
                # Rule 5: End of Backtest Period
                elif i == n_bars - 1:
                    exit_triggered = True
                    exit_price = close_p
                    exit_reason = "End of Backtest Period"
                    
                if exit_triggered:
                    trade_counter += 1
                    sell_shares = shares_available
                    gross_proceeds = sell_shares * exit_price
                    
                    # Transaction Fees
                    commission = max(gross_proceeds * self.config.commission_rate, self.config.min_commission)
                    transfer_fee = gross_proceeds * self.config.transfer_fee_rate
                    stamp_duty = gross_proceeds * self.config.stamp_duty_rate  # Sell side only
                    total_sell_fees = commission + transfer_fee + stamp_duty
                    
                    net_proceeds = gross_proceeds - total_sell_fees
                    cash += net_proceeds
                    
                    invested_cost = sell_shares * entry_price
                    gross_pnl = (exit_price - entry_price) * sell_shares
                    net_pnl = gross_pnl - total_sell_fees
                    ret_pct = (net_pnl / invested_cost) * 100.0 if invested_cost > 0 else 0.0
                    holding_days = i - entry_index
                    
                    trades.append(TradeRecord(
                        trade_id=trade_counter,
                        stock_code=stock_code,
                        entry_date=entry_date,
                        entry_price=round(entry_price, 3),
                        exit_date=bar_date,
                        exit_price=round(exit_price, 3),
                        shares=sell_shares,
                        gross_pnl=round(gross_pnl, 2),
                        total_fees=round(total_sell_fees, 2),
                        net_pnl=round(net_pnl, 2),
                        return_pct=round(ret_pct, 2),
                        holding_days=max(1, holding_days),
                        exit_reason=exit_reason
                    ))
                    
                    shares_held -= sell_shares
                    shares_available = 0
                    entry_price = 0.0
                    entry_date = ""
                    highest_price_seen = 0.0
                    current_stop_price = 0.0
            
            # --- 3. Check Entries if Flat ---
            if shares_held == 0 and i >= warmup and i < n_bars - 1:
                buy_signal = bool(row.get('raw_buy_signal', False))
                if buy_signal:
                    exec_buy_price = close_p * (1.0 + self.config.slippage_pct)
                    
                    # Allocate based on maximum position capital budget
                    available_budget = cash * self.config.max_position_pct
                    buy_shares = int(available_budget / exec_buy_price)
                    buy_shares = (buy_shares // self.config.lot_size) * self.config.lot_size
                    
                    if buy_shares >= self.config.lot_size:
                        gross_cost = buy_shares * exec_buy_price
                        commission = max(gross_cost * self.config.commission_rate, self.config.min_commission)
                        transfer_fee = gross_cost * self.config.transfer_fee_rate
                        total_buy_fees = commission + transfer_fee
                        
                        if cash >= (gross_cost + total_buy_fees):
                            cash -= (gross_cost + total_buy_fees)
                            shares_held = buy_shares
                            shares_frozen = buy_shares  # T+1 lock
                            shares_available = 0
                            
                            entry_price = exec_buy_price
                            entry_date = bar_date
                            entry_index = i
                            highest_price_seen = high_p
                            current_stop_price = entry_price * (1.0 - self.config.stop_loss_pct)
            
            daily_total_equity = cash + (shares_held * close_p)
            prev_equity = equity_curve[-1].total_equity if equity_curve else self.config.initial_cash
            daily_ret = (daily_total_equity - prev_equity) / prev_equity if prev_equity > 0 else 0.0
            
            equity_curve.append(DailySnapshot(
                date=bar_date,
                cash=round(cash, 2),
                shares=shares_held,
                stock_value=round(shares_held * close_p, 2),
                total_equity=round(daily_total_equity, 2),
                daily_return=round(daily_ret, 5),
                drawdown=round(drawdown * 100.0, 2),
                benchmark_equity=round(benchmark_equity, 2),
                in_position=shares_held > 0
            ))
            
        return {
            "trades": trades,
            "equity_curve": equity_curve,
            "data": data,
            "config": self.config
        }
