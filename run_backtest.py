"""
CLI Backtest Runner for Stock Trade Algo v2
Usage:
    python run_backtest.py --code 000001 --start 2021-01-01 --end 2024-12-31 --tp 0.08 --sl 0.03
"""

import argparse
import sys
import os

# Set UTF-8 encoding for Windows terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from config import TradingConfig, DEFAULT_WATCHLIST
from core.data_feed import load_stock_data
from core.indicators import add_all_indicators
from core.strategy import DualRegimeAdaptiveStrategy
from core.engine import BacktestEngine
from core.metrics import calculate_performance_metrics


def run_cli_backtest(
    code: str = "000001",
    start_date: str = "2021-01-01",
    end_date: str = "2024-12-31",
    initial_cash: float = 100_000.0,
    fast_ema: int = 12,
    slow_ema: int = 26,
    macd_signal: int = 9,
    take_profit_pct: float = 0.08,
    stop_loss_pct: float = 0.03,
    atr_multiplier: float = 2.2,
    position_pct: float = 0.95,
    enable_regime: bool = True,
    enable_oversold: bool = True
):
    console = Console()
    console.print(Panel(f"[bold cyan]China A-Shares Quantitative Backtest Engine v2 (Dual-Regime)[/bold cyan]\n"
                        f"Asset: [yellow]{code}[/yellow] | Window: [green]{start_date} ~ {end_date}[/green] | Capital: [white]RMB {initial_cash:,.2f}[/white]\n"
                        f"Strategy: [magenta]Take Profit +{take_profit_pct*100:.1f}% | Stop Loss -{stop_loss_pct*100:.1f}% | ATR Trailing {atr_multiplier}x[/magenta]",
                        title="[bold blue]Stock Trade Algo v2[/bold blue]", border_style="cyan"))

    # 1. Config
    config = TradingConfig(
        initial_cash=initial_cash,
        fast_ema=fast_ema,
        slow_ema=slow_ema,
        macd_signal=macd_signal,
        take_profit_pct=take_profit_pct,
        stop_loss_pct=stop_loss_pct,
        atr_multiplier=atr_multiplier,
        max_position_pct=position_pct,
        enable_regime_filter=enable_regime,
        enable_oversold_swing=enable_oversold
    )

    # 2. Fetch Data
    with console.status(f"[bold yellow]Fetching historical data for {code}...[/bold yellow]"):
        df = load_stock_data(code=code, start_date=start_date, end_date=end_date)
        stock_name = getattr(df, 'attrs', {}).get('stock_name', code)

    if df is None or len(df) < 30:
        console.print(f"[bold red]Error: Insufficient data found for {code}[/bold red]")
        return

    console.print(f"Loaded [bold green]{len(df)}[/bold green] trading bars for [bold yellow]{stock_name} ({code})[/bold yellow]")

    # 3. Calculate Indicators
    df_ind = add_all_indicators(
        df,
        fast_ema=config.fast_ema,
        slow_ema=config.slow_ema,
        macd_signal=config.macd_signal,
        atr_period=config.atr_period,
        rsi_period=config.rsi_period,
        sma_fast=config.sma_fast,
        sma_trend=config.sma_trend
    )

    # 4. Generate Strategy Signals
    strat = DualRegimeAdaptiveStrategy(
        fast_ema=config.fast_ema,
        slow_ema=config.slow_ema,
        macd_signal=config.macd_signal,
        sma_trend=config.sma_trend,
        sma_fast=config.sma_fast,
        slope_lookback=config.slope_lookback,
        enable_regime_filter=config.enable_regime_filter,
        enable_oversold_swing=config.enable_oversold_swing,
        lot_size=config.lot_size
    )
    df_signals = strat.generate_signals(df_ind)

    # 5. Execute Simulation
    engine = BacktestEngine(config=config)
    results = engine.run(df_signals, stock_code=code)
    
    trades = results['trades']
    equity_curve = results['equity_curve']

    # 6. Calculate Metrics
    metrics = calculate_performance_metrics(equity_curve, trades, initial_cash)

    # 7. Display Metrics Table
    summary_table = Table(title="[bold green]Backtest Performance Summary[/bold green]", show_header=True, header_style="bold magenta")
    summary_table.add_column("Metric", style="cyan", width=26)
    summary_table.add_column("Strategy Value", style="bold white", width=20)
    summary_table.add_column("Benchmark (Buy&Hold)", style="dim white", width=24)

    ret_color = "green" if metrics['total_return_pct'] >= 0 else "red"
    summary_table.add_row("Total Return", f"[{ret_color}]{metrics['total_return_pct']:+.2f}%[/{ret_color}]", f"{metrics['benchmark_return_pct']:+.2f}%")
    summary_table.add_row("Annualized Return (CAGR)", f"[{ret_color}]{metrics['cagr_pct']:+.2f}%[/{ret_color}]", f"{metrics['benchmark_cagr_pct']:+.2f}%")
    summary_table.add_row("Excess Alpha", f"[bold green]{metrics['excess_return_pct']:+.2f}%[/bold green]", "-")
    summary_table.add_row("Sharpe Ratio (Rf=2.5%)", f"{metrics['sharpe_ratio']:.2f}", "-")
    summary_table.add_row("Sortino Ratio", f"{metrics['sortino_ratio']:.2f}", "-")
    summary_table.add_row("Max Drawdown", f"[red]-{metrics['max_drawdown_pct']:.2f}%[/red]", "-")
    summary_table.add_row("Calmar Ratio", f"{metrics['calmar_ratio']:.2f}", "-")
    summary_table.add_row("Win Rate", f"{metrics['win_rate_pct']:.1f}% ({metrics['winning_trades']}/{metrics['total_trades']})", "-")
    summary_table.add_row("Profit Factor", f"{metrics['profit_factor']:.2f}", "-")
    summary_table.add_row("Win/Loss Ratio", f"{metrics['win_loss_ratio']:.2f}", "-")
    summary_table.add_row("Avg Holding Period", f"{metrics['avg_holding_days']:.1f} days", "-")
    summary_table.add_row("Final Account Equity", f"RMB {metrics['final_equity']:,.2f}", f"RMB {metrics['benchmark_return_pct']/100*initial_cash + initial_cash:,.2f}")

    console.print(summary_table)

    # 8. Display Recent Trades Table
    if trades:
        trade_table = Table(title=f"[bold yellow]Executed Trades Log (Total: {len(trades)})[/bold yellow]", show_header=True, header_style="bold blue")
        trade_table.add_column("#", justify="right", width=4)
        trade_table.add_column("Entry Date", width=12)
        trade_table.add_column("Entry Price", justify="right", width=12)
        trade_table.add_column("Exit Date", width=12)
        trade_table.add_column("Exit Price", justify="right", width=12)
        trade_table.add_column("Shares", justify="right", width=8)
        trade_table.add_column("Net PnL (RMB)", justify="right", width=14)
        trade_table.add_column("Return %", justify="right", width=10)
        trade_table.add_column("Exit Reason", width=24)

        for t in trades[-12:]:  # Display last 12
            pnl_color = "green" if t.net_pnl >= 0 else "red"
            trade_table.add_row(
                str(t.trade_id),
                t.entry_date,
                f"{t.entry_price:.2f}",
                t.exit_date,
                f"{t.exit_price:.2f}",
                str(t.shares),
                f"[{pnl_color}]{t.net_pnl:+,.2f}[/{pnl_color}]",
                f"[{pnl_color}]{t.return_pct:+.2f}%[/{pnl_color}]",
                t.exit_reason
            )
        console.print(trade_table)
    else:
        console.print("[yellow]No trades triggered during this backtest period under selected criteria.[/yellow]")

    return metrics, trades, equity_curve


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="China A-Shares Backtest Runner v2")
    parser.add_argument("--code", type=str, default="000001", help="Stock or ETF code (e.g. 000001, 510300)")
    parser.add_argument("--start", type=str, default="2021-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, default="2024-12-31", help="End date (YYYY-MM-DD)")
    parser.add_argument("--capital", type=float, default=100000.0, help="Initial cash capital")
    parser.add_argument("--fast", type=int, default=12, help="Fast EMA period")
    parser.add_argument("--slow", type=int, default=26, help="Slow EMA period")
    parser.add_argument("--signal", type=int, default=9, help="MACD signal period")
    parser.add_argument("--tp", type=float, default=0.08, help="Target Take Profit percentage (e.g. 0.08 = 8%%)")
    parser.add_argument("--sl", type=float, default=0.03, help="Hard Stop Loss percentage (e.g. 0.03 = 3%%)")
    parser.add_argument("--atrm", type=float, default=2.2, help="ATR trailing stop multiplier")
    parser.add_argument("--pos_pct", type=float, default=0.95, help="Position capital allocation percentage")

    args = parser.parse_args()
    run_cli_backtest(
        code=args.code,
        start_date=args.start,
        end_date=args.end,
        initial_cash=args.capital,
        fast_ema=args.fast,
        slow_ema=args.slow,
        macd_signal=args.signal,
        take_profit_pct=args.tp,
        stop_loss_pct=args.sl,
        atr_multiplier=args.atrm,
        position_pct=args.pos_pct
    )
