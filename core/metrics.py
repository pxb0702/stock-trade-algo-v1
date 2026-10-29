"""
Financial Performance Metrics Module
Calculates standard quantitative trading metrics (Sharpe, Drawdown, Sortino, Win Rate, etc.)
"""

from typing import List, Dict, Any
import numpy as np
import pandas as pd


def calculate_performance_metrics(
    equity_curve: List[Any],
    trades: List[Any],
    initial_cash: float,
    risk_free_rate: float = 0.025
) -> Dict[str, Any]:
    """
    Calculate full suite of institutional performance metrics.
    """
    if not equity_curve:
        return {}
        
    df_eq = pd.DataFrame([s.__dict__ if hasattr(s, '__dict__') else s for s in equity_curve])
    total_days = len(df_eq)
    if total_days < 2:
        return {}
        
    final_equity = df_eq['total_equity'].iloc[-1]
    final_benchmark = df_eq['benchmark_equity'].iloc[-1]
    
    # Returns
    total_return = ((final_equity - initial_cash) / initial_cash) * 100.0
    benchmark_return = ((final_benchmark - initial_cash) / initial_cash) * 100.0
    excess_return = total_return - benchmark_return
    
    years = max(total_days / 250.0, 0.05)
    cagr = ((final_equity / initial_cash) ** (1.0 / years) - 1.0) * 100.0 if final_equity > 0 else -100.0
    benchmark_cagr = ((final_benchmark / initial_cash) ** (1.0 / years) - 1.0) * 100.0 if final_benchmark > 0 else -100.0
    
    # Volatility and Sharpe
    daily_rets = df_eq['daily_return'].values
    ann_vol = float(np.std(daily_rets) * np.sqrt(250) * 100.0) if len(daily_rets) > 1 else 0.0
    
    # Daily risk free rate
    rf_daily = (1.0 + risk_free_rate) ** (1.0 / 250.0) - 1.0
    excess_daily = daily_rets - rf_daily
    
    sharpe = float(np.mean(excess_daily) / (np.std(excess_daily) + 1e-9) * np.sqrt(250))
    
    # Downside Volatility for Sortino
    neg_rets = excess_daily[excess_daily < 0]
    downside_std = float(np.std(neg_rets) * np.sqrt(250)) if len(neg_rets) > 0 else 1e-9
    sortino = float((np.mean(excess_daily) * np.sqrt(250)) / (downside_std + 1e-9))
    
    # Drawdown
    cum_max = df_eq['total_equity'].cummax()
    drawdowns = (df_eq['total_equity'] - cum_max) / cum_max
    max_drawdown = float(abs(drawdowns.min()) * 100.0)
    
    # Calmar Ratio
    calmar = float(cagr / (max_drawdown + 1e-9)) if max_drawdown > 0 else 0.0
    
    # Market Exposure
    in_pos_days = df_eq['in_position'].sum() if 'in_position' in df_eq.columns else 0
    exposure_pct = float((in_pos_days / total_days) * 100.0)
    
    # Trade statistics
    total_trades = len(trades)
    if total_trades > 0:
        pnl_list = [t.net_pnl if hasattr(t, 'net_pnl') else t['net_pnl'] for t in trades]
        ret_list = [t.return_pct if hasattr(t, 'return_pct') else t['return_pct'] for t in trades]
        holding_list = [t.holding_days if hasattr(t, 'holding_days') else t['holding_days'] for t in trades]
        
        wins = [p for p in pnl_list if p > 0]
        losses = [p for p in pnl_list if p <= 0]
        
        num_wins = len(wins)
        num_losses = len(losses)
        win_rate = float((num_wins / total_trades) * 100.0)
        
        total_profit = sum(wins)
        total_loss = abs(sum(losses))
        profit_factor = float(total_profit / (total_loss + 1e-9)) if total_loss > 0 else (99.0 if total_profit > 0 else 0.0)
        
        avg_win = float(np.mean(wins)) if wins else 0.0
        avg_loss = float(abs(np.mean(losses))) if losses else 0.0
        win_loss_ratio = float(avg_win / (avg_loss + 1e-9)) if avg_loss > 0 else 0.0
        
        avg_trade_return = float(np.mean(ret_list))
        avg_holding_days = float(np.mean(holding_list))
        
        # Max consecutive wins / losses
        max_cons_wins = 0
        max_cons_losses = 0
        curr_wins = 0
        curr_losses = 0
        for p in pnl_list:
            if p > 0:
                curr_wins += 1
                curr_losses = 0
                max_cons_wins = max(max_cons_wins, curr_wins)
            else:
                curr_losses += 1
                curr_wins = 0
                max_cons_losses = max(max_cons_losses, curr_losses)
    else:
        num_wins = 0
        num_losses = 0
        win_rate = 0.0
        profit_factor = 0.0
        avg_win = 0.0
        avg_loss = 0.0
        win_loss_ratio = 0.0
        avg_trade_return = 0.0
        avg_holding_days = 0.0
        max_cons_wins = 0
        max_cons_losses = 0
        total_profit = 0.0
        total_loss = 0.0

    return {
        "initial_capital": round(initial_cash, 2),
        "final_equity": round(final_equity, 2),
        "total_return_pct": round(total_return, 2),
        "benchmark_return_pct": round(benchmark_return, 2),
        "excess_return_pct": round(excess_return, 2),
        "cagr_pct": round(cagr, 2),
        "benchmark_cagr_pct": round(benchmark_cagr, 2),
        "annualized_volatility_pct": round(ann_vol, 2),
        "sharpe_ratio": round(sharpe, 2),
        "sortino_ratio": round(sortino, 2),
        "max_drawdown_pct": round(max_drawdown, 2),
        "calmar_ratio": round(calmar, 2),
        "market_exposure_pct": round(exposure_pct, 1),
        "total_trades": total_trades,
        "winning_trades": num_wins,
        "losing_trades": num_losses,
        "win_rate_pct": round(win_rate, 2),
        "profit_factor": round(profit_factor, 2),
        "win_loss_ratio": round(win_loss_ratio, 2),
        "avg_trade_return_pct": round(avg_trade_return, 2),
        "avg_holding_days": round(avg_holding_days, 1),
        "max_consecutive_wins": max_cons_wins,
        "max_consecutive_losses": max_cons_losses,
        "total_profit": round(total_profit, 2),
        "total_loss": round(total_loss, 2),
        "trading_days": total_days
    }
