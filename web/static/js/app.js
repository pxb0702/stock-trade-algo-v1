/**
 * Stock Trade Algo v2 - Frontend JavaScript
 * ECharts Candlestick, MACD, Equity Curve and Dynamic Dual-Regime Backtesting Controller
 */

let klineChart = null;
let equityChart = null;
let currentData = null;

document.addEventListener("DOMContentLoaded", () => {
    initCharts();
    initEventListeners();
    // Auto run first backtest on load for 平安银行 (000001)
    runBacktest();
});

function initCharts() {
    const klineDom = document.getElementById("klineChart");
    const equityDom = document.getElementById("equityChart");

    if (klineDom) {
        klineChart = echarts.init(klineDom, "dark");
    }
    if (equityDom) {
        equityChart = echarts.init(equityDom, "dark");
    }

    window.addEventListener("resize", () => {
        if (klineChart) klineChart.resize();
        if (equityChart) equityChart.resize();
    });
}

function initEventListeners() {
    // Slider value sync
    const tpSlider = document.getElementById("takeProfitPct");
    const tpDisplay = document.getElementById("tpVal");
    if (tpSlider && tpDisplay) {
        tpSlider.addEventListener("input", (e) => {
            tpDisplay.textContent = `+${(parseFloat(e.target.value) * 100).toFixed(1)}%`;
        });
    }

    const slSlider = document.getElementById("stopLossPct");
    const slDisplay = document.getElementById("slVal");
    if (slSlider && slDisplay) {
        slSlider.addEventListener("input", (e) => {
            slDisplay.textContent = `-${(parseFloat(e.target.value) * 100).toFixed(1)}%`;
        });
    }

    const atrSlider = document.getElementById("atrMultiplier");
    const atrDisplay = document.getElementById("atrVal");
    if (atrSlider && atrDisplay) {
        atrSlider.addEventListener("input", (e) => {
            atrDisplay.textContent = `${parseFloat(e.target.value).toFixed(1)} × ATR`;
        });
    }

    // Tab switching
    const tabBtns = document.querySelectorAll(".tab-btn");
    tabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            tabBtns.forEach(b => b.classList.remove("active"));
            document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));

            btn.classList.add("active");
            const targetId = btn.getAttribute("data-tab");
            const targetContent = document.getElementById(targetId);
            if (targetContent) {
                targetContent.classList.add("active");
                setTimeout(() => {
                    if (targetId === "klineTab" && klineChart) klineChart.resize();
                    if (targetId === "equityTab" && equityChart) equityChart.resize();
                }, 50);
            }
        });
    });

    // Watchlist fast switcher
    const watchlistBtns = document.querySelectorAll(".watchlist-btn");
    watchlistBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            watchlistBtns.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            const code = btn.getAttribute("data-code");
            const input = document.getElementById("stockCode");
            if (input) {
                input.value = code;
                runBacktest();
            }
        });
    });

    // Form submit
    const form = document.getElementById("backtestForm");
    if (form) {
        form.addEventListener("submit", (e) => {
            e.preventDefault();
            runBacktest();
        });
    }
}

async function runBacktest() {
    const submitBtn = document.getElementById("submitBtn");
    const code = document.getElementById("stockCode").value.trim() || "000001";
    const startDate = document.getElementById("startDate").value;
    const endDate = document.getElementById("endDate").value;
    const initialCash = parseFloat(document.getElementById("initialCash").value) || 100000;
    const tpPct = parseFloat(document.getElementById("takeProfitPct").value) || 0.08;
    const slPct = parseFloat(document.getElementById("stopLossPct").value) || 0.03;
    const atrMultiplier = parseFloat(document.getElementById("atrMultiplier").value) || 2.2;
    const enableRegime = document.getElementById("enableRegime") ? document.getElementById("enableRegime").checked : true;
    const enableOversold = document.getElementById("enableOversold") ? document.getElementById("enableOversold").checked : true;

    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 回测计算中...';
    }

    try {
        const response = await fetch("/api/backtest", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                code: code,
                start_date: startDate,
                end_date: endDate,
                initial_cash: initialCash,
                take_profit_pct: tpPct,
                stop_loss_pct: slPct,
                atr_multiplier: atrMultiplier,
                enable_regime_filter: enableRegime,
                enable_oversold_swing: enableOversold,
                position_pct: 0.95
            })
        });

        const data = await response.json();
        if (!data.success) {
            alert(`回测失败: ${data.error || "未知错误"}`);
            return;
        }

        currentData = data;

        // 1. Update Stock Badge
        const nameBadge = document.getElementById("currentStockName");
        if (nameBadge) {
            nameBadge.textContent = data.stock_name || code;
        }

        // 2. Update Metrics
        renderMetrics(data.metrics);

        // 3. Render K-Line Chart
        renderKlineChart(data.chart_data, data.stock_name, data.stock_code);

        // 4. Render Equity Curve
        renderEquityChart(data.equity_data);

        // 5. Render Trade Table
        renderTradesTable(data.trade_logs);

    } catch (err) {
        console.error("Backtest request error:", err);
        alert(`请求发生异常: ${err.message}`);
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fa-solid fa-play"></i> 运行 v2 优化回测';
        }
    }
}

function renderMetrics(m) {
    if (!m) return;

    // Total Return
    const totalRetEl = document.getElementById("valTotalReturn");
    const benchRetEl = document.getElementById("valBenchmarkReturn");
    totalRetEl.textContent = `${m.total_return_pct >= 0 ? '+' : ''}${m.total_return_pct.toFixed(2)}%`;
    totalRetEl.className = `metric-value ${m.total_return_pct >= 0 ? 'positive' : 'negative'}`;
    benchRetEl.textContent = `基准 (买入持有): ${m.benchmark_return_pct >= 0 ? '+' : ''}${m.benchmark_return_pct.toFixed(2)}%`;

    // CAGR & Alpha
    const cagrEl = document.getElementById("valCagr");
    const alphaEl = document.getElementById("valExcessReturn");
    cagrEl.textContent = `${m.cagr_pct >= 0 ? '+' : ''}${m.cagr_pct.toFixed(2)}%`;
    cagrEl.className = `metric-value ${m.cagr_pct >= 0 ? 'positive' : 'negative'}`;
    alphaEl.textContent = `超额 Alpha: ${m.excess_return_pct >= 0 ? '+' : ''}${m.excess_return_pct.toFixed(2)}%`;

    // Max Drawdown
    const mddEl = document.getElementById("valMaxDrawdown");
    const calmarEl = document.getElementById("valCalmar");
    mddEl.textContent = `-${m.max_drawdown_pct.toFixed(2)}%`;
    calmarEl.textContent = `卡玛比率 (Calmar): ${m.calmar_ratio.toFixed(2)}`;

    // Sharpe & Sortino
    const sharpeEl = document.getElementById("valSharpe");
    const sortinoEl = document.getElementById("valSortino");
    sharpeEl.textContent = m.sharpe_ratio.toFixed(2);
    sortinoEl.textContent = `索提诺比率: ${m.sortino_ratio.toFixed(2)}`;

    // Win Rate & Profit Factor
    const winRateEl = document.getElementById("valWinRate");
    const winLossEl = document.getElementById("valWinLossRatio");
    winRateEl.textContent = `${m.win_rate_pct.toFixed(1)}% (${m.winning_trades}/${m.total_trades})`;
    winLossEl.textContent = `盈亏比: ${m.win_loss_ratio.toFixed(2)} | 获利因子: ${m.profit_factor.toFixed(2)}`;

    // Final Equity & Trades Count
    const finalEquityEl = document.getElementById("valFinalEquity");
    const tradeCountEl = document.getElementById("valTradeCount");
    finalEquityEl.textContent = `¥${m.final_equity.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    tradeCountEl.textContent = `总交易: ${m.total_trades} 笔 (持仓均 ${m.avg_holding_days} 天)`;

    // Trades count badge
    const badge = document.getElementById("tradesBadgeCount");
    if (badge) badge.textContent = m.total_trades;
}

function renderKlineChart(chartData, name, code) {
    if (!klineChart) return;

    const dates = chartData.dates;
    const ohlc = chartData.ohlc;
    const volumes = chartData.volumes;
    const emaFast = chartData.ema_fast;
    const emaSlow = chartData.ema_slow;
    const sma60 = chartData.sma_60;
    const dif = chartData.macd_dif;
    const dea = chartData.macd_dea;
    const hist = chartData.macd_hist;

    // Build MarkPoints for Buy / Sell
    const markData = [];
    chartData.buy_markers.forEach(b => {
        markData.push({
            name: '买入',
            coord: [b.date, b.price],
            value: `买入\n¥${b.price}`,
            symbol: 'triangle',
            symbolSize: 14,
            symbolRotate: 0,
            itemStyle: { color: '#ef4444' }
        });
    });

    chartData.sell_markers.forEach(s => {
        const isProfit = s.pnl >= 0;
        markData.push({
            name: '平仓',
            coord: [s.date, s.price],
            value: `${isProfit ? '+' : ''}${s.return_pct}%\n¥${s.price}`,
            symbol: 'triangle',
            symbolSize: 14,
            symbolRotate: 180,
            itemStyle: { color: isProfit ? '#f59e0b' : '#10b981' }
        });
    });

    const option = {
        backgroundColor: '#151a28',
        animation: false,
        legend: {
            data: ['K线', 'EMA快线', 'EMA慢线', 'SMA60牛熊线', '成交量', 'DIF', 'DEA', 'MACD柱'],
            textStyle: { color: '#94a3b8', fontSize: 11 },
            top: 6,
            left: 10
        },
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'cross', lineStyle: { color: '#64748b' } },
            backgroundColor: 'rgba(17, 22, 36, 0.95)',
            borderColor: '#242c44',
            textStyle: { color: '#f1f5f9', fontFamily: 'JetBrains Mono', fontSize: 12 }
        },
        axisPointer: { link: [{ xAxisIndex: 'all' }] },
        grid: [
            { left: '4%', right: '3%', top: '7%', height: '52%' },      // K-line Grid
            { left: '4%', right: '3%', top: '63%', height: '14%' },     // Volume Grid
            { left: '4%', right: '3%', top: '80%', height: '14%' }      // MACD Grid
        ],
        xAxis: [
            { type: 'category', data: dates, boundaryGap: true, axisLine: { lineStyle: { color: '#242c44' } }, axisLabel: { show: false }, min: 'dataMin', max: 'dataMax' },
            { type: 'category', gridIndex: 1, data: dates, boundaryGap: true, axisLine: { lineStyle: { color: '#242c44' } }, axisLabel: { show: false }, min: 'dataMin', max: 'dataMax' },
            { type: 'category', gridIndex: 2, data: dates, boundaryGap: true, axisLine: { lineStyle: { color: '#242c44' } }, axisLabel: { color: '#64748b', fontSize: 10 }, min: 'dataMin', max: 'dataMax' }
        ],
        yAxis: [
            { scale: true, splitArea: { show: false }, splitLine: { lineStyle: { color: '#1e2638' } }, axisLabel: { color: '#94a3b8' } },
            { gridIndex: 1, scale: true, splitLine: { show: false }, axisLabel: { show: false } },
            { gridIndex: 2, scale: true, splitLine: { lineStyle: { color: '#1e2638' } }, axisLabel: { color: '#94a3b8' } }
        ],
        dataZoom: [
            { type: 'inside', xAxisIndex: [0, 1, 2], start: Math.max(0, 100 - (200 / dates.length * 100)), end: 100 },
            { show: true, xAxisIndex: [0, 1, 2], type: 'slider', bottom: 4, height: 16, borderColor: 'transparent', fillerColor: 'rgba(59, 130, 246, 0.2)' }
        ],
        series: [
            {
                name: 'K线',
                type: 'candlestick',
                data: ohlc,
                itemStyle: {
                    color: '#ef4444',          // Up: Red
                    color0: '#10b981',         // Down: Green
                    borderColor: '#ef4444',
                    borderColor0: '#10b981'
                },
                markPoint: {
                    data: markData,
                    label: {
                        show: true,
                        position: 'top',
                        fontSize: 9,
                        color: '#fff',
                        fontFamily: 'JetBrains Mono'
                    }
                }
            },
            {
                name: 'EMA快线',
                type: 'line',
                data: emaFast,
                smooth: true,
                showSymbol: false,
                lineStyle: { color: '#38bdf8', width: 1.5 }
            },
            {
                name: 'EMA慢线',
                type: 'line',
                data: emaSlow,
                smooth: true,
                showSymbol: false,
                lineStyle: { color: '#f59e0b', width: 1.5 }
            },
            {
                name: 'SMA60牛熊线',
                type: 'line',
                data: sma60,
                smooth: true,
                showSymbol: false,
                lineStyle: { color: '#a855f7', width: 1.8, type: 'dashed' }
            },
            {
                name: '成交量',
                type: 'bar',
                xAxisIndex: 1,
                yAxisIndex: 1,
                data: volumes,
                itemStyle: {
                    color: (params) => {
                        const i = params.dataIndex;
                        return ohlc[i] && ohlc[i][1] >= ohlc[i][0] ? 'rgba(239, 68, 68, 0.6)' : 'rgba(16, 185, 129, 0.6)';
                    }
                }
            },
            {
                name: 'DIF',
                type: 'line',
                xAxisIndex: 2,
                yAxisIndex: 2,
                data: dif,
                showSymbol: false,
                lineStyle: { color: '#60a5fa', width: 1.2 }
            },
            {
                name: 'DEA',
                type: 'line',
                xAxisIndex: 2,
                yAxisIndex: 2,
                data: dea,
                showSymbol: false,
                lineStyle: { color: '#f43f5e', width: 1.2 }
            },
            {
                name: 'MACD柱',
                type: 'bar',
                xAxisIndex: 2,
                yAxisIndex: 2,
                data: hist,
                itemStyle: {
                    color: (params) => (params.value >= 0 ? '#ef4444' : '#10b981')
                }
            }
        ]
    };

    klineChart.setOption(option, true);
}

function renderEquityChart(eqData) {
    if (!equityChart) return;

    const dates = eqData.dates;
    const strategy = eqData.strategy;
    const benchmark = eqData.benchmark;
    const drawdown = eqData.drawdown.map(d => -Math.abs(d));

    const option = {
        backgroundColor: '#151a28',
        animation: false,
        legend: {
            data: ['策略净值 (Strategy)', '基准净值 (Buy & Hold)', '回撤 (Drawdown %)'],
            textStyle: { color: '#94a3b8', fontSize: 11 },
            top: 6,
            left: 10
        },
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'cross', lineStyle: { color: '#64748b' } },
            backgroundColor: 'rgba(17, 22, 36, 0.95)',
            borderColor: '#242c44',
            textStyle: { color: '#f1f5f9', fontFamily: 'JetBrains Mono', fontSize: 12 }
        },
        axisPointer: { link: [{ xAxisIndex: 'all' }] },
        grid: [
            { left: '4%', right: '3%', top: '10%', height: '58%' },     // Equity Grid
            { left: '4%', right: '3%', top: '74%', height: '20%' }      // Drawdown Grid
        ],
        xAxis: [
            { type: 'category', data: dates, boundaryGap: false, axisLine: { lineStyle: { color: '#242c44' } }, axisLabel: { show: false }, min: 'dataMin', max: 'dataMax' },
            { type: 'category', gridIndex: 1, data: dates, boundaryGap: false, axisLine: { lineStyle: { color: '#242c44' } }, axisLabel: { color: '#64748b', fontSize: 10 }, min: 'dataMin', max: 'dataMax' }
        ],
        yAxis: [
            { scale: true, splitLine: { lineStyle: { color: '#1e2638' } }, axisLabel: { color: '#94a3b8', formatter: (v) => `¥${Math.round(v).toLocaleString()}` } },
            { gridIndex: 1, scale: true, splitLine: { lineStyle: { color: '#1e2638' } }, axisLabel: { color: '#f87171', formatter: '{value}%' } }
        ],
        dataZoom: [
            { type: 'inside', xAxisIndex: [0, 1], start: 0, end: 100 },
            { show: true, xAxisIndex: [0, 1], type: 'slider', bottom: 4, height: 16, borderColor: 'transparent', fillerColor: 'rgba(59, 130, 246, 0.2)' }
        ],
        series: [
            {
                name: '策略净值 (Strategy)',
                type: 'line',
                data: strategy,
                smooth: true,
                showSymbol: false,
                lineStyle: { color: '#3b82f6', width: 2.2 },
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: 'rgba(59, 130, 246, 0.4)' },
                        { offset: 1, color: 'rgba(59, 130, 246, 0.02)' }
                    ])
                }
            },
            {
                name: '基准净值 (Buy & Hold)',
                type: 'line',
                data: benchmark,
                smooth: true,
                showSymbol: false,
                lineStyle: { color: '#64748b', width: 1.5, type: 'dashed' }
            },
            {
                name: '回撤 (Drawdown %)',
                type: 'line',
                xAxisIndex: 1,
                yAxisIndex: 1,
                data: drawdown,
                showSymbol: false,
                lineStyle: { color: '#ef4444', width: 1.2 },
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: 'rgba(239, 68, 68, 0.35)' },
                        { offset: 1, color: 'rgba(239, 68, 68, 0.05)' }
                    ])
                }
            }
        ]
    };

    equityChart.setOption(option, true);
}

function renderTradesTable(trades) {
    const tbody = document.getElementById("tradesTableBody");
    if (!tbody) return;

    if (!trades || trades.length === 0) {
        tbody.innerHTML = '<tr><td colspan="11" class="empty-state">所选回测周期内未触发任何平仓交易。</td></tr>';
        return;
    }

    let rowsHtml = '';
    trades.forEach((t) => {
        const isPos = t.net_pnl >= 0;
        const pnlClass = isPos ? 'pnl-pos' : 'pnl-neg';
        const sign = isPos ? '+' : '';
        const isStop = t.exit_reason.includes("Stop") || t.exit_reason.includes("Break");

        rowsHtml += `
            <tr>
                <td>#${t.trade_id}</td>
                <td>${t.entry_date}</td>
                <td>¥${t.entry_price.toFixed(2)}</td>
                <td>${t.exit_date}</td>
                <td>¥${t.exit_price.toFixed(2)}</td>
                <td>${t.shares.toLocaleString()}</td>
                <td>¥${t.fees.toFixed(2)}</td>
                <td class="${pnlClass}">${sign}¥${t.net_pnl.toFixed(2)}</td>
                <td class="${pnlClass}">${sign}${t.return_pct.toFixed(2)}%</td>
                <td>${t.holding_days} 天</td>
                <td><span class="tag-reason ${isStop ? 'stop' : ''}">${t.exit_reason}</span></td>
            </tr>
        `;
    });

    tbody.innerHTML = rowsHtml;
}
