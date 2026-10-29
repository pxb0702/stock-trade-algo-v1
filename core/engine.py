"""
China A-Share Backtesting Engine
Event-driven simulation honoring T+1 settlement, 100-share lot sizes,
stamp duty, broker commission minimums, and trailing stop exits.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime

from config import TradingConfig
from core.strategy import TrendMomentumStrategy


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
    Realistic A-Share Backtesting Engine.
    """
    def __init__(self, config: Optional[TradingConfig] = None):
        self.config = config or TradingConfig()
        
    def run(self, df: pd.DataFrame, stock_code: str = "510300") -> Dict[str, Any]:
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

        for i in range(n_bars):
            row = data.iloc[i]
            bar_date = str(row['date'])[:10]
            open_p = float(row['open'])
            high_p = float(row['high'])
            low_p = float(row['low'])
            close_p = float(row['close'])
            atr_val = float(row.get('atr', close_p * 0.02))
            
            # --- 1. Daily T+1 Settlement (Morning Routine) ---
            # Unfreeze shares bought on previous days
            shares_available += shares_frozen
            shares_frozen = 0
            
            # Current holding valuation at today's close
            stock_value = shares_held * close_p
            total_equity = cash + stock_value
            peak_equity = max(peak_equity, total_equity)
            drawdown = (total_equity - peak_equity) / peak_equity if peak_equity > 0 else 0.0
            
            benchmark_equity = benchmark_initial_cash + (benchmark_initial_shares * close_p)
            
            # --- 2. Check Exits for Existing Positions ---
            if shares_held > 0 and shares_available > 0:
                # Update trailing stop price ratcheting
                if high_p > highest_price_seen:
                    highest_price_seen = high_p
                    new_stop = highest_price_seen - (atr_val * self.config.atr_multiplier)
                    current_stop_price = max(current_stop_price, new_stop)
                    
                exit_triggered = False
                exit_price = 0.0
                exit_reason = ""
                
                # Check ATR Stop Hit (Intraday Low breached stop price)
                if low_p <= current_stop_price:
                    exit_triggered = True
                    # If opened below stop, execute at open; otherwise stop level minus slippage
                    exit_price = min(open_p, current_stop_price) * (1.0 - self.config.slippage_pct)
                    exit_reason = "ATR Trailing Stop"
                
                # Check Macro Strategy Sell Signal
                elif bool(row.get('raw_sell_signal', False)):
                    exit_triggered = True
                    # Exit at close with slippage
                    exit_price = close_p * (1.0 - self.config.slippage_pct)
                    exit_reason = "Trend Reversal Signal"
                    
                # Force exit at the very last bar of backtest
                elif i == n_bars - 1:
                    exit_triggered = True
                    exit_price = close_p
                    exit_reason = "End of Backtest Period"
                    
                if exit_triggered:
                    trade_counter += 1
                    sell_shares = shares_available
                    gross_proceeds = sell_shares * exit_price
                    
                    # Calculate Fees
                    # Broker Commission (Min 5 RMB)
                    commission = max(gross_proceeds * self.config.commission_rate, self.config.min_commission)
                    # Transfer Fee
                    transfer_fee = gross_proceeds * self.config.transfer_fee_rate
                    # Stamp Duty (Sell side only)
                    stamp_duty = gross_proceeds * self.config.stamp_duty_rate
                    total_sell_fees = commission + transfer_fee + stamp_duty
                    
                    net_proceeds = gross_proceeds - total_sell_fees
                    cash += net_proceeds
                    
                    # PnL metrics
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
                    
                    # Clear position
                    shares_held -= sell_shares
                    shares_available = 0
                    entry_price = 0.0
                    entry_date = ""
                    highest_price_seen = 0.0
                    current_stop_price = 0.0
            
            # --- 3. Check Entries if Flat ---
            if shares_held == 0 and i < n_bars - 1:
                buy_signal = bool(row.get('raw_buy_signal', False))
                if buy_signal:
                    exec_buy_price = close_p * (1.0 + self.config.slippage_pct)
                    
                    # Volatility-based Risk Budgeting
                    risk_amount = total_equity * self.config.risk_per_trade_pct
                    risk_per_share = max(atr_val * self.config.atr_multiplier, exec_buy_price * 0.02)
                    
                    target_shares = int(risk_amount / risk_per_share)
                    
                    # Round down to A-share lot size (100 shares = 1 手)
                    target_shares = (target_shares // self.config.lot_size) * self.config.lot_size
                    
                    # Max position budget check (max allocation % of current cash)
                    max_affordable_shares = int((cash * self.config.max_position_pct) / exec_buy_price)
                    max_affordable_shares = (max_affordable_shares // self.config.lot_size) * self.config.lot_size
                    
                    buy_shares = min(target_shares, max_affordable_shares)
                    
                    if buy_shares >= self.config.lot_size:
                        gross_cost = buy_shares * exec_buy_price
                        commission = max(gross_cost * self.config.commission_rate, self.config.min_commission)
                        transfer_fee = gross_cost * self.config.transfer_fee_rate
                        total_buy_fees = commission + transfer_fee
                        
                        if cash >= (gross_cost + total_buy_fees):
                            cash -= (gross_cost + total_buy_fees)
                            shares_held = buy_shares
                            shares_frozen = buy_shares  # T+1 rule: locked until next day
                            shares_available = 0
                            
                            entry_price = exec_buy_price
                            entry_date = bar_date
                            entry_index = i
                            highest_price_seen = high_p
                            current_stop_price = entry_price - (atr_val * self.config.atr_multiplier)
            
            # Recompute total equity at end of day
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
