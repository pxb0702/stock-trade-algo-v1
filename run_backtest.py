"""
CLI Backtest Runner for Stock Trade Algo v1
Usage:
    python run_backtest.py --code 510300 --start 2021-01-01 --end 2024-12-31
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
from core.strategy import TrendMomentumStrategy
from core.engine import BacktestEngine
from core.metrics import calculate_performance_metrics


def run_cli_backtest(
    code: str = "510300",
    start_date: str = "2021-01-01",
    end_date: str = "2025-01-01",
    initial_cash: float = 100_000.0,
    fast_ema: int = 12,
    slow_ema: int = 26,
    macd_signal: int = 9,
    atr_multiplier: float = 2.0,
    risk_pct: float = 0.02
):
    console = Console()
    console.print(Panel(f"[bold cyan]China A-Shares Quantitative Backtest Engine v1[/bold cyan]\n"
                        f"Asset: [yellow]{code}[/yellow] | Window: [green]{start_date} ~ {end_date}[/green] | Capital: [white]RMB {initial_cash:,.2f}[/white]",
                        title="[bold blue]Stock Trade Algo v1[/bold blue]", border_style="cyan"))

    # 1. Config
    config = TradingConfig(
        initial_cash=initial_cash,
        fast_ema=fast_ema,
        slow_ema=slow_ema,
        macd_signal=macd_signal,
        atr_multiplier=atr_multiplier,
        risk_per_trade_pct=risk_pct
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
        rsi_period=config.rsi_period
    )

    # 4. Generate Strategy Signals
    strat = TrendMomentumStrategy(
        fast_ema=config.fast_ema,
        slow_ema=config.slow_ema,
        macd_signal=config.macd_signal,
        atr_multiplier=config.atr_multiplier,
        risk_per_trade_pct=config.risk_per_trade_pct,
        rsi_overbought=config.rsi_overbought,
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

    summary_table.add_row("Total Return", f"{metrics['total_return_pct']:+.2f}%", f"{metrics['benchmark_return_pct']:+.2f}%")
    summary_table.add_row("Annualized Return (CAGR)", f"{metrics['cagr_pct']:+.2f}%", f"{metrics['benchmark_cagr_pct']:+.2f}%")
    summary_table.add_row("Excess Alpha", f"{metrics['excess_return_pct']:+.2f}%", "-")
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
        trade_table.add_column("Exit Reason", width=22)

        for t in trades[-10:]:  # Display last 10
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
    parser = argparse.ArgumentParser(description="China A-Shares Backtest Runner")
    parser.add_argument("--code", type=str, default="510300", help="Stock or ETF code (e.g. 510300, 600519)")
    parser.add_argument("--start", type=str, default="2021-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, default="2025-01-01", help="End date (YYYY-MM-DD)")
    parser.add_argument("--capital", type=float, default=100000.0, help="Initial cash capital")
    parser.add_argument("--fast", type=int, default=12, help="Fast EMA period")
    parser.add_argument("--slow", type=int, default=26, help="Slow EMA period")
    parser.add_argument("--signal", type=int, default=9, help="MACD signal period")
    parser.add_argument("--atr_mult", type=float, default=2.0, help="ATR trailing stop multiplier")
    parser.add_argument("--risk", type=float, default=0.02, help="Risk per trade percentage")

    args = parser.parse_args()
    run_cli_backtest(
        code=args.code,
        start_date=args.start,
        end_date=args.end,
        initial_cash=args.capital,
        fast_ema=args.fast,
        slow_ema=args.slow,
        macd_signal=args.signal,
        atr_multiplier=args.atr_mult,
        risk_pct=args.risk
    )
