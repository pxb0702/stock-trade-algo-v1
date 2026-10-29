"""
Flask Web Dashboard for Stock Trade Algo v2
Interactive Quantitative Backtesting Dashboard for China A-Shares.
"""

import os
import sys

# Configure UTF-8 for Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import numpy as np
import pandas as pd
from datetime import datetime
from flask import Flask, render_template, request, jsonify

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import TradingConfig, DEFAULT_WATCHLIST
from core.data_feed import load_stock_data, COMMON_NAMES
from core.indicators import add_all_indicators
from core.strategy import DualRegimeAdaptiveStrategy
from core.engine import BacktestEngine
from core.metrics import calculate_performance_metrics

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "static")
)


@app.route("/")
def index():
    return render_template("index.html", watchlist=DEFAULT_WATCHLIST)


@app.route("/api/watchlist", methods=["GET"])
def get_watchlist():
    return jsonify({"success": True, "watchlist": DEFAULT_WATCHLIST})


@app.route("/api/backtest", methods=["POST"])
def run_backtest_api():
    try:
        data = request.get_json() or {}
        code = str(data.get("code", "000001")).strip()
        start_date = data.get("start_date", "2021-01-01")
        end_date = data.get("end_date", datetime.now().strftime("%Y-%m-%d"))
        initial_cash = float(data.get("initial_cash", 100_000.0))
        
        # Strategy v2 parameters
        fast_ema = int(data.get("fast_ema", 12))
        slow_ema = int(data.get("slow_ema", 26))
        macd_signal = int(data.get("macd_signal", 9))
        atr_multiplier = float(data.get("atr_multiplier", 2.2))
        atr_period = int(data.get("atr_period", 14))
        take_profit_pct = float(data.get("take_profit_pct", 0.08))
        stop_loss_pct = float(data.get("stop_loss_pct", 0.03))
        position_pct = float(data.get("position_pct", 0.95))
        enable_regime = bool(data.get("enable_regime_filter", True))
        enable_oversold = bool(data.get("enable_oversold_swing", True))
        
        config = TradingConfig(
            initial_cash=initial_cash,
            fast_ema=fast_ema,
            slow_ema=slow_ema,
            macd_signal=macd_signal,
            atr_multiplier=atr_multiplier,
            atr_period=atr_period,
            take_profit_pct=take_profit_pct,
            stop_loss_pct=stop_loss_pct,
            max_position_pct=position_pct,
            enable_regime_filter=enable_regime,
            enable_oversold_swing=enable_oversold
        )
        
        # 1. Load Data
        df = load_stock_data(code=code, start_date=start_date, end_date=end_date)
        if df is None or len(df) < 15:
            return jsonify({"success": False, "error": f"No data found for stock code {code}"}), 400
            
        clean_code = "".join(filter(str.isdigit, str(code)))
        stock_name = getattr(df, 'attrs', {}).get('stock_name') or COMMON_NAMES.get(clean_code, clean_code)
        
        # 2. Add Indicators
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
        
        # 3. Strategy Signals
        strategy = DualRegimeAdaptiveStrategy(
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
        df_signals = strategy.generate_signals(df_ind)
        
        # 4. Engine Backtest
        engine = BacktestEngine(config=config)
        results = engine.run(df_signals, stock_code=code)
        
        trades = results['trades']
        equity_curve = results['equity_curve']
        
        # 5. Metrics
        metrics = calculate_performance_metrics(equity_curve, trades, initial_cash)
        
        # 6. Prepare Chart-ready Series
        dates = [str(d)[:10] for d in df_signals['date']]
        ohlc = df_signals[['open', 'close', 'low', 'high']].round(3).values.tolist()
        volumes = df_signals['volume'].astype(int).tolist()
        ema_fast_line = [None if np.isnan(v) else round(v, 3) for v in df_signals['ema_fast']]
        ema_slow_line = [None if np.isnan(v) else round(v, 3) for v in df_signals['ema_slow']]
        sma_60_line = [None if np.isnan(v) else round(v, 3) for v in df_signals['sma_60']]
        macd_dif = [None if np.isnan(v) else round(v, 3) for v in df_signals['macd_dif']]
        macd_dea = [None if np.isnan(v) else round(v, 3) for v in df_signals['macd_dea']]
        macd_hist = [None if np.isnan(v) else round(v, 3) for v in df_signals['macd_hist']]
        rsi_series = [None if np.isnan(v) else round(v, 2) for v in df_signals['rsi']]
        
        # Trade Markers
        buy_markers = []
        sell_markers = []
        trade_logs = []
        
        for t in trades:
            buy_markers.append({
                "date": t.entry_date,
                "price": t.entry_price,
                "shares": t.shares,
                "trade_id": t.trade_id
            })
            sell_markers.append({
                "date": t.exit_date,
                "price": t.exit_price,
                "shares": t.shares,
                "pnl": t.net_pnl,
                "return_pct": t.return_pct,
                "reason": t.exit_reason,
                "trade_id": t.trade_id
            })
            trade_logs.append({
                "trade_id": t.trade_id,
                "entry_date": t.entry_date,
                "entry_price": t.entry_price,
                "exit_date": t.exit_date,
                "exit_price": t.exit_price,
                "shares": t.shares,
                "gross_pnl": t.gross_pnl,
                "fees": t.total_fees,
                "net_pnl": t.net_pnl,
                "return_pct": t.return_pct,
                "holding_days": t.holding_days,
                "exit_reason": t.exit_reason
            })
            
        # Equity Curve series
        eq_dates = [s.date for s in equity_curve]
        eq_strategy = [s.total_equity for s in equity_curve]
        eq_benchmark = [s.benchmark_equity for s in equity_curve]
        eq_drawdown = [s.drawdown for s in equity_curve]
        eq_cash = [s.cash for s in equity_curve]
        
        response_payload = {
            "success": True,
            "stock_code": clean_code,
            "stock_name": stock_name,
            "data_count": len(df_signals),
            "metrics": metrics,
            "chart_data": {
                "dates": dates,
                "ohlc": ohlc,
                "volumes": volumes,
                "ema_fast": ema_fast_line,
                "ema_slow": ema_slow_line,
                "sma_60": sma_60_line,
                "macd_dif": macd_dif,
                "macd_dea": macd_dea,
                "macd_hist": macd_hist,
                "rsi": rsi_series,
                "buy_markers": buy_markers,
                "sell_markers": sell_markers
            },
            "equity_data": {
                "dates": eq_dates,
                "strategy": eq_strategy,
                "benchmark": eq_benchmark,
                "drawdown": eq_drawdown,
                "cash": eq_cash
            },
            "trade_logs": trade_logs
        }
        return jsonify(response_payload)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


def start_server(port: int = 5000, debug: bool = False):
    print(f"\n=======================================================")
    print(f"🚀 Stock Trade Algo v2 Dashboard is running!")
    print(f"🌐 Access Dashboard at: http://127.0.0.1:{port}")
    print(f"=======================================================\n")
    app.run(host="0.0.0.0", port=port, debug=debug)


if __name__ == "__main__":
    start_server()
