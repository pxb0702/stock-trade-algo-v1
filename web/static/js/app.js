/**
 * Stock Trade Algo v2.1 - Frontend JavaScript
 * ECharts Candlestick, MACD, Equity Curve, Dynamic Dual-Regime Backtesting Controller,
 * and Persistent Watchlist Management (Add/Remove Stocks)
 */

let klineChart = null;
let equityChart = null;
let currentData = null;
let currentWatchlist = [];

document.addEventListener("DOMContentLoaded", () => {
    initCharts();
    initEventListeners();
    initWatchlistHandlers();
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

function showToast(message, type = 'info', duration = 3200) {
    const container = document.getElementById("toastContainer");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    
    let icon = '<i class="fa-solid fa-circle-info"></i>';
    if (type === 'success') icon = '<i class="fa-solid fa-circle-check"></i>';
    if (type === 'error') icon = '<i class="fa-solid fa-circle-exclamation"></i>';

    toast.innerHTML = `${icon} <span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        toast.style.transition = 'all 0.25s ease';
        setTimeout(() => toast.remove(), 250);
    }, duration);
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

    // Form submit
    const form = document.getElementById("backtestForm");
    if (form) {
        form.addEventListener("submit", (e) => {
            e.preventDefault();
            runBacktest();
        });
    }

    // Sidebar stockCode input live resolver
    const stockInput = document.getElementById("stockCode");
    let resolveTimer = null;
    if (stockInput) {
        stockInput.addEventListener("input", (e) => {
            clearTimeout(resolveTimer);
            const val = e.target.value.trim();
            if (val.length >= 6) {
                resolveTimer = setTimeout(async () => {
                    try {
                        const res = await fetch(`/api/stock/resolve?code=${encodeURIComponent(val)}`);
                        const d = await res.json();
                        if (d.success && d.name) {
                            const badge = document.getElementById("currentStockName");
                            if (badge) badge.textContent = d.name;
                        }
                    } catch (err) {}
                }, 250);
            }
        });
    }
}

// ----------------------------------------------------
// Watchlist Management (Add, Delete, Resolve, Render)
// ----------------------------------------------------
function initWatchlistHandlers() {
    bindWatchlistPillClicks();

    // Modal controls
    const openBtn = document.getElementById("openAddModalBtn");
    const closeBtn = document.getElementById("closeAddModalBtn");
    const cancelBtn = document.getElementById("cancelAddModalBtn");
    const modal = document.getElementById("addStockModal");
    const addForm = document.getElementById("addStockForm");
    const modalCodeInput = document.getElementById("modalStockCode");
    const modalNameInput = document.getElementById("modalStockName");
    const modalBadge = document.getElementById("modalResolvedBadge");

    function openModal() {
        if (!modal) return;
        modal.style.display = "flex";
        if (modalCodeInput) {
            modalCodeInput.value = "";
            modalCodeInput.focus();
        }
        if (modalNameInput) modalNameInput.value = "";
        if (modalBadge) modalBadge.textContent = "输入后自动解析";
    }

    function closeModal() {
        if (!modal) return;
        modal.style.display = "none";
    }

    if (openBtn) openBtn.addEventListener("click", openModal);
    if (closeBtn) closeBtn.addEventListener("click", closeModal);
    if (cancelBtn) cancelBtn.addEventListener("click", closeModal);
    if (modal) {
        modal.addEventListener("click", (e) => {
            if (e.target === modal) closeModal();
        });
    }

    // Modal code input auto resolve
    let modalResolveTimer = null;
    if (modalCodeInput) {
        modalCodeInput.addEventListener("input", (e) => {
            clearTimeout(modalResolveTimer);
            const code = e.target.value.trim();
            if (code.length >= 5) {
                if (modalBadge) modalBadge.textContent = "查询中...";
                modalResolveTimer = setTimeout(async () => {
                    try {
                        const res = await fetch(`/api/stock/resolve?code=${encodeURIComponent(code)}`);
                        const d = await res.json();
                        if (d.success && d.name) {
                            if (modalBadge) modalBadge.textContent = d.name;
                            if (modalNameInput && !modalNameInput.value) {
                                modalNameInput.value = d.name;
                            }
                        } else {
                            if (modalBadge) modalBadge.textContent = "未识别名称";
                        }
                    } catch (err) {
                        if (modalBadge) modalBadge.textContent = "解析异常";
                    }
                }, 200);
            } else {
                if (modalBadge) modalBadge.textContent = "输入后自动解析";
            }
        });
    }

    // Modal suggestion tags
    const suggestTags = document.querySelectorAll(".btn-tag");
    suggestTags.forEach(tag => {
        tag.addEventListener("click", () => {
            const code = tag.getAttribute("data-code");
            const name = tag.getAttribute("data-name");
            if (modalCodeInput) modalCodeInput.value = code;
            if (modalNameInput) modalNameInput.value = name;
            if (modalBadge) modalBadge.textContent = name;
        });
    });

    // Form submit: Add Stock
    if (addForm) {
        addForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const code = document.getElementById("modalStockCode").value.trim();
            const name = document.getElementById("modalStockName").value.trim();
            const desc = document.getElementById("modalStockDesc") ? document.getElementById("modalStockDesc").value.trim() : "";

            if (!code) return;

            const submitBtn = document.getElementById("confirmAddStockBtn");
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 添加中...';
            }

            try {
                const res = await fetch("/api/watchlist/add", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ code, name, desc })
                });
                const d = await res.json();
                if (d.success) {
                    showToast(d.message || "添加成功", "success");
                    closeModal();
                    renderWatchlist(d.watchlist, code);
                    // Set current stock and run backtest immediately
                    const stockInput = document.getElementById("stockCode");
                    if (stockInput) stockInput.value = code;
                    runBacktest();
                } else {
                    showToast(d.message || "添加失败", "error");
                }
            } catch (err) {
                showToast(`添加请求异常: ${err.message}`, "error");
            } finally {
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = '<i class="fa-solid fa-check"></i> 保存并添加到自选';
                }
            }
        });
    }

    // Reset Watchlist Button
    const resetBtn = document.getElementById("resetWatchlistBtn");
    if (resetBtn) {
        resetBtn.addEventListener("click", async () => {
            if (!confirm("确定要恢复默认的自选股列表吗？自定义添加的股票将被重置。")) return;
            try {
                const res = await fetch("/api/watchlist/reset", { method: "POST" });
                const d = await res.json();
                if (d.success) {
                    showToast("已成功重置为默认自选股票池", "success");
                    renderWatchlist(d.watchlist, "000001");
                }
            } catch (err) {
                showToast(`重置失败: ${err.message}`, "error");
            }
        });
    }

    // Sidebar quick add button
    const sidebarAddBtn = document.getElementById("sidebarAddWatchlistBtn");
    if (sidebarAddBtn) {
        sidebarAddBtn.addEventListener("click", async () => {
            const codeInput = document.getElementById("stockCode");
            const code = codeInput ? codeInput.value.trim() : "";
            const nameBadge = document.getElementById("currentStockName");
            const name = nameBadge ? nameBadge.textContent.trim() : "";

            if (!code) {
                showToast("请输入标的代码", "error");
                return;
            }

            try {
                const res = await fetch("/api/watchlist/add", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ code, name })
                });
                const d = await res.json();
                if (d.success) {
                    showToast(d.message || "已添加到自选", "success");
                    renderWatchlist(d.watchlist, code);
                } else {
                    showToast(d.message || "添加失败", "info");
                }
            } catch (err) {
                showToast(`操作异常: ${err.message}`, "error");
            }
        });
    }

    // Sidebar quick remove button
    const sidebarRemoveBtn = document.getElementById("sidebarRemoveWatchlistBtn");
    if (sidebarRemoveBtn) {
        sidebarRemoveBtn.addEventListener("click", async () => {
            const codeInput = document.getElementById("stockCode");
            const code = codeInput ? codeInput.value.trim() : "";
            if (!code) return;
            if (!confirm(`确定将标的 ${code} 移出自选列表吗？`)) return;

            try {
                const res = await fetch("/api/watchlist/delete", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ code })
                });
                const d = await res.json();
                if (d.success) {
                    showToast(d.message || "已移出自选", "success");
                    renderWatchlist(d.watchlist);
                } else {
                    showToast(d.message || "移除失败", "error");
                }
            } catch (err) {
                showToast(`移除异常: ${err.message}`, "error");
            }
        });
    }
}

function bindWatchlistPillClicks() {
    const container = document.getElementById("watchlistContainer");
    if (!container) return;

    // Select pill
    const pills = container.querySelectorAll(".watchlist-pill");
    pills.forEach(pill => {
        const selectBtn = pill.querySelector(".pill-select-btn");
        const delBtn = pill.querySelector(".pill-del-btn");
        const code = pill.getAttribute("data-code");

        if (selectBtn) {
            selectBtn.addEventListener("click", () => {
                pills.forEach(p => p.classList.remove("active"));
                pill.classList.add("active");
                const stockInput = document.getElementById("stockCode");
                if (stockInput) {
                    stockInput.value = code;
                    runBacktest();
                }
            });
        }

        if (delBtn) {
            delBtn.addEventListener("click", async (e) => {
                e.stopPropagation();
                const stockName = selectBtn ? selectBtn.querySelector(".name").textContent : code;
                if (!confirm(`确定将 ${stockName} (${code}) 从自选列表删除吗？`)) return;

                try {
                    const res = await fetch("/api/watchlist/delete", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ code })
                    });
                    const d = await res.json();
                    if (d.success) {
                        showToast(`已删除 ${stockName}`, "success");
                        renderWatchlist(d.watchlist);
                    } else {
                        showToast(d.message || "删除失败", "error");
                    }
                } catch (err) {
                    showToast(`删除异常: ${err.message}`, "error");
                }
            });
        }
    });
}

function renderWatchlist(watchlist, activeCode = null) {
    const container = document.getElementById("watchlistContainer");
    if (!container || !watchlist) return;

    const currentCode = activeCode || (document.getElementById("stockCode") ? document.getElementById("stockCode").value.trim() : "");

    let html = "";
    watchlist.forEach((item) => {
        const isActive = item.code === currentCode;
        html += `
            <div class="watchlist-pill ${isActive ? 'active' : ''}" data-code="${item.code}">
                <button class="pill-select-btn" type="button" title="${item.desc || item.name}">
                    <span class="code">${item.code}</span>
                    <span class="name">${item.name}</span>
                </button>
                <button class="pill-del-btn" type="button" title="从自选列表移除 ${item.name}" data-code="${item.code}">
                    <i class="fa-solid fa-xmark"></i>
                </button>
            </div>
        `;
    });

    container.innerHTML = html;
    bindWatchlistPillClicks();
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

    // Highlight current active pill
    const pills = document.querySelectorAll(".watchlist-pill");
    pills.forEach(p => {
        if (p.getAttribute("data-code") === code) {
            p.classList.add("active");
        } else {
            p.classList.remove("active");
        }
    });

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
            showToast(`回测失败: ${data.error || "未知错误"}`, "error");
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
        showToast(`请求发生异常: ${err.message}`, "error");
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fa-solid fa-play"></i> 运行 v2 优化回测';
        }
    }
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
