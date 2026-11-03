const $ = (id) => document.getElementById(id);

const csrfToken =
    document.querySelector('meta[name="csrf-token"]')?.content || "";

const money = new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2
});

let simulatedMarketPrice = 2500;
const priceHistory = Array(30).fill(simulatedMarketPrice);

function drawMarketChart() {
    const canvas = $("marketChart");
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    if (!rect.width || !rect.height) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.round(rect.width * dpr);
    canvas.height = Math.round(rect.height * dpr);

    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const width = rect.width;
    const height = rect.height;
    const padding = 12;

    const minPrice = Math.min(...priceHistory);
    const maxPrice = Math.max(...priceHistory);
    const range = Math.max(maxPrice - minPrice, 1);
    const low = minPrice - range * 0.2;
    const high = maxPrice + range * 0.2;

    ctx.clearRect(0, 0, width, height);

    ctx.strokeStyle = "rgba(145, 164, 186, 0.14)";
    ctx.lineWidth = 1;

    for (let i = 0; i < 4; i++) {
        const y = padding + (height - padding * 2) * i / 3;
        ctx.beginPath();
        ctx.moveTo(padding, y);
        ctx.lineTo(width - padding, y);
        ctx.stroke();
    }

    const points = priceHistory.map((price, index) => ({
        x: padding + index * (width - padding * 2) / (priceHistory.length - 1),
        y: height - padding -
            ((price - low) / (high - low)) * (height - padding * 2)
    }));

    const rising = priceHistory.at(-1) >= priceHistory[0];
    const lineColor = rising ? "#20d6a0" : "#ff657a";

    ctx.beginPath();
    points.forEach((point, index) => {
        if (index === 0) ctx.moveTo(point.x, point.y);
        else ctx.lineTo(point.x, point.y);
    });

    ctx.strokeStyle = lineColor;
    ctx.lineWidth = 2.5;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    ctx.stroke();

    const last = points[points.length - 1];
    ctx.beginPath();
    ctx.arc(last.x, last.y, 4, 0, Math.PI * 2);
    ctx.fillStyle = lineColor;
    ctx.fill();
}

function updateChartLabels() {
    const firstPrice = priceHistory[0];
    const change = ((simulatedMarketPrice - firstPrice) / firstPrice) * 100;

    $("chartCurrentPrice").textContent = money.format(simulatedMarketPrice);

    const changeElement = $("priceChange");
    changeElement.textContent = `${change >= 0 ? "+" : ""}${change.toFixed(2)}%`;
    changeElement.classList.toggle("negative", change < 0);
}

async function api(url, options = {}) {
    const method = (options.method || "GET").toUpperCase();

    const headers = {
        "Content-Type": "application/json",
        ...(options.headers || {})
    };

    if (method !== "GET") {
        headers["X-CSRF-Token"] = csrfToken;
    }

    const response = await fetch(url, {
        ...options,
        method,
        headers
    });

    if (response.status === 401) {
        window.location.href = "/login";
        throw new Error("Session expired. Please login again.");
    }

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.error || "API request failed");
    }

    return data;
}

function updateMarketPrice() {
    simulatedMarketPrice += (Math.random() - 0.5) * 12;
    simulatedMarketPrice = Math.max(1, simulatedMarketPrice);

    $("marketPrice").textContent = money.format(simulatedMarketPrice);

    priceHistory.push(simulatedMarketPrice);
    if (priceHistory.length > 60) priceHistory.shift();

    updateChartLabels();
    drawMarketChart();
}

function updateOrderValue() {
    const price = Number($("price").value);
    const quantity = Number($("quantity").value);
    const value = price * quantity;

    $("orderValue").textContent =
        Number.isFinite(value) && value > 0 ? money.format(value) : money.format(0);
}

function updateOrderSide() {
    const form = $("orderForm");
    form.classList.remove("buy-mode", "sell-mode");

    if ($("side").value === "BUY") {
        form.classList.add("buy-mode");
    } else {
        form.classList.add("sell-mode");
    }
}

function renderRows(element, rows, emptyText) {
    if (!rows.length) {
        element.innerHTML = `<tr><td colspan="2" class="empty">${emptyText}</td></tr>`;
        return;
    }

    element.innerHTML = rows.map(row => `
        <tr>
            <td>${row.price}</td>
            <td>${row.quantity}</td>
        </tr>
    `).join("");
}

function renderOpenOrders(orders) {
    const body = $("openOrdersBody");

    if (!orders || !orders.length) {
        body.innerHTML = '<tr><td colspan="5" class="empty">No open orders</td></tr>';
        return;
    }

    body.innerHTML = orders.map(order => `
        <tr>
            <td>#${order.order_id}</td>
            <td>${order.side}</td>
            <td>${order.price}</td>
            <td>${order.quantity}</td>
            <td>
                <button type="button"
                    class="cancel-order-button"
                    data-order-id="${order.order_id}">
                    Cancel
                </button>
            </td>
        </tr>
    `).join("");
}

async function refreshDashboard() {
    try {
        const status = await api("/api/status");

        $("connectionStatus").textContent = "Connected";
        $("engineStatus").textContent = status.status.toUpperCase();
        $("ordersProcessed").textContent = status.orders_processed;
        $("executedTrades").textContent = status.executed_trades;
        $("bestBid").textContent = status.best_bid ?? "—";
        $("bestAsk").textContent = status.best_ask ?? "—";

        renderRows($("bidsBody"), status.orderbook.bids, "No buy orders");
        renderRows($("asksBody"), status.orderbook.asks, "No sell orders");
        renderOpenOrders(status.orderbook.open_orders);

        await refreshTrades();
    } catch (error) {
        $("connectionStatus").textContent = "Disconnected";
        $("engineStatus").textContent = error.message;
    }
}

async function refreshTrades() {
    const data = await api("/api/trades");
    const body = $("tradesBody");

    if (!data.trades.length) {
        body.innerHTML = '<tr><td colspan="4" class="empty">No executed trades yet</td></tr>';
        return;
    }

    body.innerHTML = data.trades.slice().reverse().map(trade => `
        <tr>
            <td>${trade.buy_order_id}</td>
            <td>${trade.sell_order_id}</td>
            <td>${trade.price}</td>
            <td>${trade.quantity}</td>
        </tr>
    `).join("");
}

$("openOrdersBody").addEventListener("click", async (event) => {
    const button = event.target.closest(".cancel-order-button");
    if (!button) return;

    const orderId = Number(button.dataset.orderId);
    const message = $("cancelMessage");

    button.disabled = true;
    message.textContent = `Cancelling order #${orderId}...`;

    try {
        const result = await api("/api/order/cancel", {
            method: "POST",
            body: JSON.stringify({ order_id: orderId })
        });

        message.textContent = `Order #${result.order_id} cancelled successfully.`;
        await refreshDashboard();
    } catch (error) {
        message.textContent = error.message;
        button.disabled = false;
    }
});

$("orderForm").addEventListener("submit", async (event) => {
    event.preventDefault();

    const message = $("orderMessage");
    message.textContent = "Submitting order...";

    try {
        const result = await api("/api/order", {
            method: "POST",
            body: JSON.stringify({
                side: $("side").value,
                price: $("price").value,
                quantity: $("quantity").value
            })
        });

        message.textContent =
            `Order #${result.order_id} accepted. Trades executed: ${result.new_trades.length}`;

        await refreshDashboard();
    } catch (error) {
        message.textContent = error.message;
    }
});

$("simulateButton").addEventListener("click", async () => {
    const message = $("simulationMessage");
    const button = $("simulateButton");

    button.disabled = true;
    message.textContent = "Running simulation...";

    try {
        const result = await api("/api/simulate", {
            method: "POST",
            body: JSON.stringify({
                count: $("simulationCount").value
            })
        });

        message.textContent =
            `Processed ${result.orders_processed} simulated orders. Total trades: ${result.total_trades}`;

        await refreshDashboard();
    } catch (error) {
        message.textContent = error.message;
    } finally {
        button.disabled = false;
    }
});

function benchmarkNumber(value, digits = 2) {
    const number = Number(value);
    return Number.isFinite(number)
        ? number.toLocaleString("en-IN", { maximumFractionDigits: digits })
        : "—";
}

function benchmarkEscape(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;",
        '"': "&quot;", "'": "&#39;"
    })[char]);
}

function benchmarkCard(label, value, unit, note = "") {
    return `
        <div class="benchmark-metric">
            <span>${benchmarkEscape(label)}</span>
            <strong>${benchmarkEscape(value)} <small>${benchmarkEscape(unit)}</small></strong>
            <em>${benchmarkEscape(note)}</em>
        </div>`;
}

function renderEngineComparison(data) {
    const engines = Object.entries(data.engines || {});
    if (!engines.length) return "";

    const labels = {
        python: "Python",
        cython_original: "Original Cython",
        cython_optimized: "Optimized Cython",
        cython: "Cython"
    };

    const values = engines.map(([key, engine]) => ({
        key,
        name: labels[key] || key.replaceAll("_", " "),
        summary: engine.summary || {}
    }));

    const maxThroughput = Math.max(
        1,
        ...values.map(item => Number(item.summary.mean_throughput_orders_per_second) || 0)
    );

    const fastest = [...values].sort(
        (a, b) =>
            (Number(b.summary.mean_throughput_orders_per_second) || 0) -
            (Number(a.summary.mean_throughput_orders_per_second) || 0)
    )[0];

    const rows = values.map(item => {
        const throughput = Number(item.summary.mean_throughput_orders_per_second) || 0;
        const width = Math.max(0, Math.min(100, throughput / maxThroughput * 100));

        return `
            <div class="benchmark-engine">
                <div class="benchmark-engine-top">
                    <strong>${benchmarkEscape(item.name)}</strong>
                    <span>${benchmarkNumber(throughput, 0)} orders/sec</span>
                </div>
                <div class="benchmark-track">
                    <div class="benchmark-fill" style="width:${width.toFixed(2)}%"></div>
                </div>
                <div class="benchmark-engine-details">
                    <span>P95: ${benchmarkNumber(item.summary.median_p95_latency_us, 3)} µs</span>
                    <span>P99: ${benchmarkNumber(item.summary.median_p99_latency_us, 3)} µs</span>
                    <span>Average: ${benchmarkNumber(item.summary.mean_throughput_orders_per_second, 0)} ops/sec</span>
                </div>
            </div>`;
    }).join("");

    const workload = data.workload || {};
    const parity = data.correctness?.all_runs_passed_parity;

    return `
        <section class="benchmark-section">
            <div class="benchmark-section-heading">
                <div>
                    <span class="eyebrow">ENGINE PERFORMANCE</span>
                    <h4>Three-way engine comparison</h4>
                    <p>${benchmarkNumber(workload.orders_per_run, 0)} orders/run ·
                       ${benchmarkNumber(workload.runs, 0)} measured runs ·
                       ${benchmarkNumber(workload.warmup_runs, 0)} warm-up</p>
                </div>
                <span class="benchmark-status ${parity === true ? "passed" : parity === false ? "failed" : "unknown"}">
                    ${parity === true ? "✓ PARITY PASSED" : parity === false ? "✕ PARITY FAILED" : "PARITY UNKNOWN"}
                </span>
            </div>
            <div class="benchmark-winner">
                <span>HIGHEST MEAN THROUGHPUT</span>
                <strong>${benchmarkEscape(fastest.name)}</strong>
                <small>${benchmarkNumber(fastest.summary.mean_throughput_orders_per_second, 0)} orders/sec</small>
            </div>
            <div class="benchmark-engine-list">${rows}</div>
            <p class="benchmark-footnote">Comparison uses the same workload and measured run count for each engine. Higher throughput is better; lower latency is better.</p>
        </section>`;
}

function renderPipeline(data) {
    const summary = data.summary || {};
    if (!summary.mean_pipeline_latency_ms &&
        !summary.mean_throughput_orders_per_second) return "";

    return `
        <section class="benchmark-section">
            <div class="benchmark-section-heading">
                <div>
                    <span class="eyebrow">END-TO-END PERFORMANCE</span>
                    <h4>Trading pipeline analytics</h4>
                    <p>${benchmarkEscape(data.benchmark || "Pipeline benchmark")}</p>
                </div>
                <span class="benchmark-status">PIPELINE</span>
            </div>
            <div class="benchmark-metric-grid">
                ${benchmarkCard("Mean throughput", benchmarkNumber(summary.mean_throughput_orders_per_second, 0), "orders/sec")}
                ${benchmarkCard("Mean pipeline latency", benchmarkNumber(summary.mean_pipeline_latency_ms, 3), "ms")}
                ${benchmarkCard("P95 pipeline latency", benchmarkNumber(summary.p95_pipeline_latency_ms, 3), "ms")}
                ${benchmarkCard("P99 pipeline latency", benchmarkNumber(summary.p99_pipeline_latency_ms, 3), "ms")}
                ${benchmarkCard("Per-order average", benchmarkNumber(summary.mean_individual_order_processing_latency_us, 3), "µs")}
                ${benchmarkCard("Per-order P99", benchmarkNumber(summary.median_run_order_p99_latency_us, 3), "µs")}
            </div>
            <p class="benchmark-footnote">Pipeline latency measures the complete pipeline. Per-order latency is a separate measurement.</p>
        </section>`;
}

function renderBenchmarkHistory(items) {
    const friendlyName = file => {
        if (file.includes("three_way")) return "Three-way engine comparison";
        if (file.includes("engine_comparison")) return "Engine comparison";
        if (file.includes("engine_baseline")) return "Engine baseline";
        if (file.includes("pipeline")) return "Trading pipeline";
        if (file.includes("improved")) return "Improved Python benchmark";
        if (file.includes("baseline")) return "Python baseline";
        if (file.includes("smoke")) return "Smoke test";
        return "Python matching engine";
    };

    return `
        <section class="benchmark-section benchmark-history">
            <div class="benchmark-section-heading">
                <div>
                    <span class="eyebrow">SAVED MEASUREMENTS</span>
                    <h4>Benchmark history</h4>
                    <p>${items.length} result files found</p>
                </div>
            </div>
            <div class="benchmark-history-list">
                ${items.map(item => {
                    const data = item.data || {};
                    const summary = data.summary || {};
                    const workload = data.workload || {};
                    const firstEngine = Object.values(data.engines || {})[0];
                    const throughput =
                        summary.mean_throughput_orders_per_second ??
                        firstEngine?.summary?.mean_throughput_orders_per_second;

                    return `
                        <div class="benchmark-history-row">
                            <div>
                                <strong>${benchmarkEscape(friendlyName(item.file))}</strong>
                                <small>${benchmarkEscape(item.file)}</small>
                            </div>
                            <div class="benchmark-history-meta">
                                <span>${benchmarkEscape(
                                    workload.orders_per_run ??
                                    data.orders_per_run ??
                                    "—"
                                )} orders/run</span>
                                <span>${benchmarkEscape(
                                    workload.runs ??
                                    data.runs ??
                                    "—"
                                )} runs</span>
                            </div>
                            <strong class="benchmark-history-value">
                                ${throughput ? `${benchmarkNumber(throughput, 0)} ops/s` : "Pipeline / details"}
                            </strong>
                        </div>`;
                }).join("")}
            </div>
        </section>`;
}

async function loadBenchmarks() {
    const container = $("benchmarkResults");

    try {
        const result = await api("/api/benchmarks");
        const items = result.results || [];

        if (!items.length) {
            container.textContent = "No benchmark result files found.";
            return;
        }

        const valid = items.filter(item => item.data && !item.error);
        const threeWay = valid.find(item =>
            item.file === "results_engine_three_way_20000_15runs.json"
        );
        const pipeline = valid.find(item =>
            item.file === "results_pipeline_latency_10000.json"
        );

        const engineData = threeWay?.data;
        const pipelineData = pipeline?.data;

        const summary = engineData?.engines?.python?.summary || {};
        const workload = engineData?.workload || {};

        container.innerHTML = `
            <div class="benchmark-dashboard">
                <div class="benchmark-overview">
                    <div>
                        <span class="eyebrow">CHRONOSMATCH PERFORMANCE</span>
                        <h4>System benchmark overview</h4>
                        <p>Measured results from your saved benchmark runs</p>
                    </div>
                    <span class="benchmark-total">${valid.length} DATASETS</span>
                </div>

                <div class="benchmark-metric-grid">
                    ${benchmarkCard("Python throughput", benchmarkNumber(summary.mean_throughput_orders_per_second, 0), "orders/sec", `${benchmarkNumber(workload.runs, 0)} measured runs`)}
                    ${benchmarkCard("Python P95 latency", benchmarkNumber(summary.median_p95_latency_us, 3), "µs", "Median run P95")}
                    ${benchmarkCard("Python P99 latency", benchmarkNumber(summary.median_p99_latency_us, 3), "µs", "Median run P99")}
                    ${benchmarkCard("Orders per run", benchmarkNumber(workload.orders_per_run, 0), "orders", "Three-way comparison")}
                </div>

                ${engineData ? renderEngineComparison(engineData) : ""}
                ${pipelineData ? renderPipeline(pipelineData) : ""}
                ${renderBenchmarkHistory(valid)}
                <p class="benchmark-footnote">All values are loaded from saved benchmark JSON files. No performance values are estimated or generated.</p>
            </div>`;

    } catch (error) {
        container.textContent = error.message;
    }
}

$("useMarketPriceButton").addEventListener("click", () => {
    $("price").value = simulatedMarketPrice.toFixed(2);
    updateOrderValue();
    $("orderMessage").textContent = "Simulated market price copied to limit price.";
});

$("price").addEventListener("input", updateOrderValue);
$("quantity").addEventListener("input", updateOrderValue);
$("side").addEventListener("change", updateOrderSide);

updateMarketPrice();
window.addEventListener("resize", drawMarketChart);
updateOrderValue();
updateOrderSide();

setInterval(updateMarketPrice, 4000);
refreshDashboard();
loadBenchmarks();
setInterval(refreshDashboard, 2000);
