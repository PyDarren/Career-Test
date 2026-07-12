/**
 * admin-dashboard.js — 后台数据看板交互脚本
 * 功能：KPI 卡片渲染、Canvas 趋势折线图、柱状图、转化漏斗、
 *       异常告警面板、时间范围切换、截图导出、每小时自动刷新
 */

(function () {
    'use strict';

    // ============== 配置 ==============
    var CONFIG = {
        refreshInterval: 3600000, // 1 小时
        colors: {
            purple: '#9B7ED8',
            purpleLight: '#B8A4E0',
            green: '#5ea67e',
            greenLight: '#7cc09b',
            blue: '#5a96b1',
            blueLight: '#7ab5cf',
            gold: '#deb45c',
            goldLight: '#e8c878',
            red: '#e17055',
            teal: '#7DD3C0',
            gray: '#e7eae8',
            textDark: '#2d2d3a',
            textMid: '#636e72',
            textLight: '#9B9BAB'
        }
    };

    // ============== 模拟数据 ==============
    var MOCK_KPI = {
        dau: { label: 'DAU', value: '4,283', change: '+12.5%', direction: 'up', icon: 'purple', sparkline: [3200, 3400, 3100, 3800, 4200, 4100, 4283] },
        completionRate: { label: '完成率', value: '68.4%', change: '+3.2%', direction: 'up', icon: 'green', sparkline: [60, 62, 63, 65, 64, 66, 68.4] },
        conversionRate: { label: '付费转化率', value: '15.7%', change: '-1.3%', direction: 'down', icon: 'blue', sparkline: [18, 17.5, 17, 16.8, 16.5, 16, 15.7] },
        avgOrder: { label: '客单价', value: '¥2.99', change: '0%', direction: 'flat', icon: 'gold', sparkline: [2.99, 2.99, 2.99, 2.99, 2.99, 2.99, 2.99] },
        shareRate: { label: '分享率', value: '23.1%', change: '+5.8%', direction: 'up', icon: 'teal', sparkline: [15, 16, 17, 18, 20, 22, 23.1] },
        d7Retention: { label: 'D7 留存', value: '31.2%', change: '+2.1%', direction: 'up', icon: 'red', sparkline: [26, 27, 28, 29, 30, 30.5, 31.2] }
    };

    var MOCK_TREND = {
        labels: ['07-06', '07-07', '07-08', '07-09', '07-10', '07-11', '07-12'],
        dau: [3200, 3450, 3100, 3800, 4200, 4100, 4283],
        newUsers: [1850, 1920, 1680, 2100, 2350, 2280, 2400],
        completions: [2180, 2360, 2120, 2600, 2870, 2790, 2930]
    };

    var MOCK_BAR = {
        labels: ['微信支付', '支付宝'],
        values: [186, 134],
        colors: [CONFIG.colors.green, CONFIG.colors.blue]
    };

    var MOCK_FUNNEL = [
        { name: '访问页面', value: 12450, color: '1' },
        { name: '开始测评', value: 8520, color: '2' },
        { name: '完成测评', value: 5830, color: '3' },
        { name: '付费解锁', value: 916, color: '4' },
        { name: '分享结果', value: 212, color: '5' }
    ];

    var MOCK_ALERTS = [
        { level: 'critical', title: '付费转化率下降', desc: '付费转化率从 17.2% 降至 15.7%，低于阈值 16%', time: '2026-07-12 10:30' },
        { level: 'warning', title: '完成率波动', desc: '07-08 完成率突降至 63%，疑似题目加载异常', time: '2026-07-08 14:15' },
        { level: 'info', title: 'DAU 创新高', desc: '07-10 DAU 达到 4200，较上周增长 18%', time: '2026-07-10 09:00' }
    ];

    // ============== DOM 引用 ==============
    var els = {
        logoutBtn: document.getElementById('logoutBtn'),
        syncInfo: document.getElementById('syncInfo'),
        // 时间范围
        timeRangeTabs: document.getElementById('timeRangeTabs'),
        timeRangeCustom: document.getElementById('timeRangeCustom'),
        customDateStart: document.getElementById('customDateStart'),
        customDateEnd: document.getElementById('customDateEnd'),
        customApplyBtn: document.getElementById('customApplyBtn'),
        currentRangeLabel: document.getElementById('currentRangeLabel'),
        // KPI
        kpiGrid: document.getElementById('kpiGrid'),
        // 图表
        trendChart: document.getElementById('trendChart'),
        barChart: document.getElementById('barChart'),
        // 漏斗
        funnelContainer: document.getElementById('funnelContainer'),
        // 告警
        alertBadge: document.getElementById('alertBadge'),
        alertList: document.getElementById('alertList'),
        // 截图
        screenshotBtn: document.getElementById('screenshotBtn'),
        screenshotModal: document.getElementById('screenshotModal'),
        screenshotOverlay: document.getElementById('screenshotOverlay'),
        screenshotPreview: document.getElementById('screenshotPreview'),
        screenshotClose: document.getElementById('screenshotClose'),
        screenshotDownload: document.getElementById('screenshotDownload'),
        // Toast
        toast: document.getElementById('adminToast')
    };

    // ============== 状态 ==============
    var state = {
        timeRange: '7d',
        currentMetric: 'dau',
        lastRefreshTime: Date.now(),
        refreshTimer: null
    };

    // ========================================================
    //  1. KPI 卡片渲染
    // ========================================================
    function renderKPI() {
        var kpis = [
            MOCK_KPI.dau,
            MOCK_KPI.completionRate,
            MOCK_KPI.conversionRate,
            MOCK_KPI.avgOrder,
            MOCK_KPI.shareRate,
            MOCK_KPI.d7Retention
        ];

        els.kpiGrid.innerHTML = kpis.map(function (kpi, i) {
            var iconClass = 'kpi-card__icon--' + kpi.icon;
            var changeClass = 'kpi-card__change--' + kpi.direction;
            var arrowSvg = kpi.direction === 'up'
                ? '<svg viewBox="0 0 24 24" width="10" height="10" fill="none" stroke="currentColor" stroke-width="3"><polyline points="18 15 12 9 6 15"/></svg>'
                : kpi.direction === 'down'
                    ? '<svg viewBox="0 0 24 24" width="10" height="10" fill="none" stroke="currentColor" stroke-width="3"><polyline points="6 9 12 15 18 9"/></svg>'
                    : '<svg viewBox="0 0 24 24" width="10" height="10" fill="none" stroke="currentColor" stroke-width="3"><line x1="5" y1="12" x2="19" y2="12"/></svg>';

            var iconSvg = getKpiIcon(i);

            return '<div class="kpi-card">' +
                '<div class="kpi-card__header">' +
                    '<span class="kpi-card__label">' + kpi.label + '</span>' +
                    '<div class="kpi-card__icon ' + iconClass + '">' + iconSvg + '</div>' +
                '</div>' +
                '<div class="kpi-card__value">' + kpi.value + '</div>' +
                '<div class="kpi-card__change ' + changeClass + '">' + arrowSvg + ' ' + kpi.change + ' vs 上期</div>' +
                '<canvas class="kpi-card__sparkline" id="spark_' + i + '" width="160" height="32"></canvas>' +
            '</div>';
        }).join('');

        // 绘制 sparkline
        kpis.forEach(function (kpi, i) {
            var canvas = document.getElementById('spark_' + i);
            if (canvas) drawSparkline(canvas, kpi.sparkline, CONFIG.colors[kpi.icon] || CONFIG.colors.purple);
        });
    }

    function getKpiIcon(index) {
        var icons = [
            '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
            '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>',
            '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>',
            '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>',
            '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>',
            '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="M16 16h5v5"/></svg>'
        ];
        return icons[index] || icons[0];
    }

    // ========================================================
    //  2. Sparkline 迷你折线图
    // ========================================================
    function drawSparkline(canvas, data, color) {
        var ctx = canvas.getContext('2d');
        var w = canvas.width;
        var h = canvas.height;
        ctx.clearRect(0, 0, w, h);

        if (data.length < 2) return;

        var max = Math.max.apply(null, data);
        var min = Math.min.apply(null, data);
        var range = max - min || 1;
        var stepX = w / (data.length - 1);
        var padding = 4;

        // 填充渐变
        var gradient = ctx.createLinearGradient(0, 0, 0, h);
        gradient.addColorStop(0, color + '30');
        gradient.addColorStop(1, color + '00');

        ctx.beginPath();
        ctx.moveTo(0, h);
        data.forEach(function (val, i) {
            var x = i * stepX;
            var y = h - padding - ((val - min) / range) * (h - padding * 2);
            if (i === 0) {
                ctx.lineTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });
        ctx.lineTo(w, h);
        ctx.closePath();
        ctx.fillStyle = gradient;
        ctx.fill();

        // 折线
        ctx.beginPath();
        data.forEach(function (val, i) {
            var x = i * stepX;
            var y = h - padding - ((val - min) / range) * (h - padding * 2);
            if (i === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });
        ctx.strokeStyle = color;
        ctx.lineWidth = 1.5;
        ctx.stroke();
    }

    // ========================================================
    //  3. 趋势折线图
    // ========================================================
    function drawTrendChart() {
        var canvas = els.trendChart;
        var ctx = canvas.getContext('2d');
        var w = canvas.width;
        var h = canvas.height;
        ctx.clearRect(0, 0, w, h);

        var data = MOCK_TREND[state.currentMetric] || MOCK_TREND.dau;
        var labels = MOCK_TREND.labels;
        var color = state.currentMetric === 'dau' ? CONFIG.colors.purple
                   : state.currentMetric === 'newUsers' ? CONFIG.colors.blue
                   : CONFIG.colors.green;

        var padding = { top: 20, right: 30, bottom: 40, left: 50 };
        var chartW = w - padding.left - padding.right;
        var chartH = h - padding.top - padding.bottom;

        var max = Math.max.apply(null, data) * 1.1;
        var min = 0;
        var range = max - min || 1;

        // Y 轴网格 & 标签
        var ySteps = 4;
        for (var i = 0; i <= ySteps; i++) {
            var y = padding.top + (chartH / ySteps) * i;
            var value = max - (range / ySteps) * i;

            // 网格线
            ctx.beginPath();
            ctx.moveTo(padding.left, y);
            ctx.lineTo(w - padding.right, y);
            ctx.strokeStyle = '#f0f1f3';
            ctx.lineWidth = 1;
            ctx.stroke();

            // Y 标签
            ctx.fillStyle = CONFIG.colors.textLight;
            ctx.font = '11px Montserrat, sans-serif';
            ctx.textAlign = 'right';
            ctx.fillText(formatNumber(Math.round(value)), padding.left - 8, y + 4);
        }

        // X 轴标签
        var stepX = chartW / (data.length - 1);
        labels.forEach(function (label, i) {
            var x = padding.left + stepX * i;
            ctx.fillStyle = CONFIG.colors.textLight;
            ctx.font = '11px Inter, sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText(label, x, h - padding.bottom + 18);
        });

        // 填充渐变
        var gradient = ctx.createLinearGradient(0, padding.top, 0, padding.top + chartH);
        gradient.addColorStop(0, color + '30');
        gradient.addColorStop(1, color + '00');

        ctx.beginPath();
        ctx.moveTo(padding.left, padding.top + chartH);
        data.forEach(function (val, i) {
            var x = padding.left + stepX * i;
            var y = padding.top + chartH - ((val - min) / range) * chartH;
            ctx.lineTo(x, y);
        });
        ctx.lineTo(padding.left + stepX * (data.length - 1), padding.top + chartH);
        ctx.closePath();
        ctx.fillStyle = gradient;
        ctx.fill();

        // 折线
        ctx.beginPath();
        data.forEach(function (val, i) {
            var x = padding.left + stepX * i;
            var y = padding.top + chartH - ((val - min) / range) * chartH;
            if (i === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });
        ctx.strokeStyle = color;
        ctx.lineWidth = 2.5;
        ctx.lineJoin = 'round';
        ctx.stroke();

        // 数据点
        data.forEach(function (val, i) {
            var x = padding.left + stepX * i;
            var y = padding.top + chartH - ((val - min) / range) * chartH;

            // 外圈
            ctx.beginPath();
            ctx.arc(x, y, 5, 0, Math.PI * 2);
            ctx.fillStyle = '#fff';
            ctx.fill();
            ctx.strokeStyle = color;
            ctx.lineWidth = 2.5;
            ctx.stroke();

            // 数值标签（最后一个点）
            if (i === data.length - 1) {
                ctx.fillStyle = color;
                ctx.font = 'bold 12px Montserrat, sans-serif';
                ctx.textAlign = 'left';
                ctx.fillText(formatNumber(val), x + 10, y + 4);
            }
        });
    }

    // ========================================================
    //  4. 柱状图
    // ========================================================
    function drawBarChart() {
        var canvas = els.barChart;
        var ctx = canvas.getContext('2d');
        var w = canvas.width;
        var h = canvas.height;
        ctx.clearRect(0, 0, w, h);

        var data = MOCK_BAR;
        var padding = { top: 20, right: 20, bottom: 50, left: 50 };
        var chartW = w - padding.left - padding.right;
        var chartH = h - padding.top - padding.bottom;

        var max = Math.max.apply(null, data.values) * 1.15;
        var barWidth = chartW / data.values.length * 0.5;
        var gap = chartW / data.values.length * 0.5;

        // Y 轴网格
        var ySteps = 4;
        for (var i = 0; i <= ySteps; i++) {
            var y = padding.top + (chartH / ySteps) * i;
            var value = max - (max / ySteps) * i;

            ctx.beginPath();
            ctx.moveTo(padding.left, y);
            ctx.lineTo(w - padding.right, y);
            ctx.strokeStyle = '#f0f1f3';
            ctx.lineWidth = 1;
            ctx.stroke();

            ctx.fillStyle = CONFIG.colors.textLight;
            ctx.font = '11px Montserrat, sans-serif';
            ctx.textAlign = 'right';
            ctx.fillText('¥' + Math.round(value * 2.99), padding.left - 8, y + 4);
        }

        // 柱子
        data.values.forEach(function (val, i) {
            var x = padding.left + gap * 0.5 + i * (barWidth + gap);
            var barH = (val / max) * chartH;
            var y = padding.top + chartH - barH;

            // 渐变柱
            var gradient = ctx.createLinearGradient(0, y, 0, y + barH);
            gradient.addColorStop(0, data.colors[i]);
            gradient.addColorStop(1, data.colors[i] + '80');

            ctx.beginPath();
            var radius = 6;
            ctx.moveTo(x + radius, y);
            ctx.lineTo(x + barWidth - radius, y);
            ctx.arcTo(x + barWidth, y, x + barWidth, y + radius, radius);
            ctx.lineTo(x + barWidth, y + barH);
            ctx.lineTo(x, y + barH);
            ctx.lineTo(x, y + radius);
            ctx.arcTo(x, y, x + radius, y, radius);
            ctx.closePath();
            ctx.fillStyle = gradient;
            ctx.fill();

            // 数值
            ctx.fillStyle = CONFIG.colors.textDark;
            ctx.font = 'bold 13px Montserrat, sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText(val + ' 笔', x + barWidth / 2, y - 8);

            // X 标签
            ctx.fillStyle = CONFIG.colors.textMid;
            ctx.font = '12px Inter, sans-serif';
            ctx.fillText(data.labels[i], x + barWidth / 2, h - padding.bottom + 20);

            // 金额
            ctx.fillStyle = CONFIG.colors.textLight;
            ctx.font = '11px Montserrat, sans-serif';
            ctx.fillText('¥' + (val * 2.99).toFixed(2), x + barWidth / 2, h - padding.bottom + 36);
        });
    }

    // ========================================================
    //  5. 转化漏斗
    // ========================================================
    function renderFunnel() {
        var max = MOCK_FUNNEL[0].value;
        var html = '';

        MOCK_FUNNEL.forEach(function (step, i) {
            var pct = (step.value / max) * 100;
            var prevValue = i > 0 ? MOCK_FUNNEL[i - 1].value : step.value;
            var convRate = i > 0 ? ((step.value / prevValue) * 100).toFixed(1) : '100.0';
            var convClass = i > 0 && parseFloat(convRate) < 50 ? 'funnel-step__conv--drop' : '';

            html += '<div class="funnel-step">' +
                '<div class="funnel-step__info">' +
                    '<div class="funnel-step__name">' + step.name + '</div>' +
                    '<div class="funnel-step__conv ' + convClass + '">转化率 ' + convRate + '%</div>' +
                '</div>' +
                '<div class="funnel-step__bar-wrapper">' +
                    '<div class="funnel-step__bar funnel-step__bar--' + step.color + '" style="width:' + pct + '%">' +
                        '<span class="funnel-step__label">' + step.name + '</span>' +
                        '<span class="funnel-step__value">' + formatNumber(step.value) + '</span>' +
                    '</div>' +
                '</div>' +
            '</div>';
        });

        els.funnelContainer.innerHTML = html;
    }

    // ========================================================
    //  6. 异常告警面板
    // ========================================================
    function renderAlerts() {
        var alerts = MOCK_ALERTS;

        if (alerts.length === 0) {
            els.alertList.innerHTML = '<div class="alert-empty">暂无异常告警，系统运行正常</div>';
            els.alertBadge.textContent = '运行正常';
            els.alertBadge.classList.add('alert-badge--ok');
            return;
        }

        els.alertBadge.textContent = alerts.length + ' 条告警';

        var iconSvgs = {
            critical: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12" y2="17"/></svg>',
            warning: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12" y2="17"/></svg>',
            info: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="8"/></svg>'
        };

        els.alertList.innerHTML = alerts.map(function (a) {
            return '<div class="alert-item alert-item--' + a.level + '">' +
                '<div class="alert-item__icon">' + iconSvgs[a.level] + '</div>' +
                '<div class="alert-item__body">' +
                    '<div class="alert-item__title">' + a.title + '</div>' +
                    '<div class="alert-item__desc">' + a.desc + '</div>' +
                    '<div class="alert-item__time">' + a.time + '</div>' +
                '</div>' +
            '</div>';
        }).join('');
    }

    // ========================================================
    //  7. 时间范围切换
    // ========================================================
    function initTimeRange() {
        els.timeRangeTabs.querySelectorAll('.time-tab').forEach(function (tab) {
            tab.addEventListener('click', function () {
                els.timeRangeTabs.querySelectorAll('.time-tab').forEach(function (t) {
                    t.classList.remove('time-tab--active');
                });
                tab.classList.add('time-tab--active');

                var range = tab.getAttribute('data-range');
                state.timeRange = range;

                if (range === 'custom') {
                    els.timeRangeCustom.style.display = 'flex';
                } else {
                    els.timeRangeCustom.style.display = 'none';
                    updateRangeLabel(range);
                    refreshData();
                }
            });
        });

        els.customApplyBtn.addEventListener('click', function () {
            var start = els.customDateStart.value;
            var end = els.customDateEnd.value;
            if (!start || !end) {
                showToast('请选择完整的日期范围');
                return;
            }
            if (start > end) {
                showToast('开始日期不能晚于结束日期');
                return;
            }
            els.currentRangeLabel.textContent = start + ' 至 ' + end;
            refreshData();
            showToast('已应用自定义时间范围');
        });
    }

    function updateRangeLabel(range) {
        var today = new Date('2026-07-12');
        var labels = {
            yesterday: getRangeLabel(1, 1),
            '7d': getRangeLabel(7, 1),
            '30d': getRangeLabel(30, 1)
        };
        els.currentRangeLabel.textContent = labels[range] || labels['7d'];
    }

    function getRangeLabel(days, offset) {
        var end = new Date('2026-07-12');
        end.setDate(end.getDate() - offset + 1);
        var start = new Date(end);
        start.setDate(start.getDate() - days + 1);
        return formatDate(start) + ' 至 ' + formatDate(end);
    }

    function formatDate(d) {
        function pad(n) { return n < 10 ? '0' + n : '' + n; }
        return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate());
    }

    // ========================================================
    //  8. 图表指标切换
    // ========================================================
    function initChartToggles() {
        document.querySelectorAll('.chart-toggle').forEach(function (btn) {
            btn.addEventListener('click', function () {
                document.querySelectorAll('.chart-toggle').forEach(function (b) {
                    b.classList.remove('chart-toggle--active');
                });
                btn.classList.add('chart-toggle--active');
                state.currentMetric = btn.getAttribute('data-metric');
                drawTrendChart();
                trackEvent('chart_metric_change', { metric: state.currentMetric });
            });
        });
    }

    // ========================================================
    //  9. 截图导出
    // ========================================================
    function initScreenshot() {
        els.screenshotBtn.addEventListener('click', function () {
            showToast('正在生成截图...');

            setTimeout(function () {
                // 模拟截图生成（实际使用 html2canvas 或后端截图服务）
                var previewHtml = '<div style="background:#fff;border-radius:8px;padding:16px;text-align:left;">' +
                    '<div style="font-size:14px;font-weight:700;color:#2d2d3a;margin-bottom:8px;">数据看板 — 近 7 日</div>' +
                    '<div style="display:flex;gap:12px;margin-bottom:12px;">' +
                        '<div style="flex:1;background:#f5f6f8;border-radius:6px;padding:8px;text-align:center;"><div style="font-size:18px;font-weight:700;color:#9B7ED8;font-family:Montserrat;">4,283</div><div style="font-size:10px;color:#9B9BAB;">DAU</div></div>' +
                        '<div style="flex:1;background:#f5f6f8;border-radius:6px;padding:8px;text-align:center;"><div style="font-size:18px;font-weight:700;color:#5ea67e;font-family:Montserrat;">68.4%</div><div style="font-size:10px;color:#9B9BAB;">完成率</div></div>' +
                        '<div style="flex:1;background:#f5f6f8;border-radius:6px;padding:8px;text-align:center;"><div style="font-size:18px;font-weight:700;color:#5a96b1;font-family:Montserrat;">15.7%</div><div style="font-size:10px;color:#9B9BAB;">转化率</div></div>' +
                    '</div>' +
                    '<div style="font-size:11px;color:#9B9BAB;text-align:right;">生成时间：' + getCurrentTimeStr() + '</div>' +
                '</div>';

                els.screenshotPreview.innerHTML = previewHtml +
                    '<div class="screenshot-preview__label">截图预览（实际将导出完整看板为 PNG 图片）</div>';

                els.screenshotModal.classList.add('modal--open');
                trackEvent('screenshot_export');
            }, 800);
        });

        els.screenshotClose.addEventListener('click', function () {
            els.screenshotModal.classList.remove('modal--open');
        });

        els.screenshotOverlay.addEventListener('click', function () {
            els.screenshotModal.classList.remove('modal--open');
        });

        els.screenshotDownload.addEventListener('click', function () {
            // 模拟下载
            var blob = new Blob(['Career Test 数据看板截图\n生成时间：' + getCurrentTimeStr()], { type: 'text/plain' });
            var url = URL.createObjectURL(blob);
            var a = document.createElement('a');
            a.href = url;
            a.download = 'dashboard_' + new Date().toISOString().substring(0, 10) + '.png';
            a.click();
            URL.revokeObjectURL(url);

            els.screenshotModal.classList.remove('modal--open');
            showToast('截图已下载');
        });
    }

    // ========================================================
    // 10. 自动刷新
    // ========================================================
    function initAutoRefresh() {
        updateSyncTime();
        state.refreshTimer = setInterval(function () {
            refreshData();
            showToast('图表数据已刷新');
        }, CONFIG.refreshInterval);

        // 每分钟更新同步时间显示
        setInterval(updateSyncTime, 60000);
    }

    function updateSyncTime() {
        var elapsed = Math.floor((Date.now() - state.lastRefreshTime) / 1000);
        var text;
        if (elapsed < 60) {
            text = '刚刚';
        } else if (elapsed < 3600) {
            text = Math.floor(elapsed / 60) + ' 分钟前';
        } else {
            text = Math.floor(elapsed / 3600) + ' 小时前';
        }
        els.syncInfo.querySelector('span').textContent = '图表刷新：' + text;
    }

    function refreshData() {
        state.lastRefreshTime = Date.now();
        renderKPI();
        drawTrendChart();
        drawBarChart();
        renderFunnel();
        renderAlerts();
        updateSyncTime();
    }

    // ========================================================
    // 11. 退出 & 侧边栏
    // ========================================================
    function initMisc() {
        els.logoutBtn.addEventListener('click', function () {
            if (confirm('确认退出登录？')) {
                showToast('已退出登录');
                setTimeout(function () {
                    window.location.href = 'index.html';
                }, 1000);
            }
        });

        document.querySelectorAll('.admin-menu__item').forEach(function (item) {
            item.addEventListener('click', function (e) {
                e.preventDefault();
                var page = item.getAttribute('data-page');
                if (page === 'dashboard') return;
                showToast('「' + item.querySelector('span').textContent + '」页面开发中');
            });
        });
    }

    // ========================================================
    // 12. ESC 键
    // ========================================================
    function initKeyboard() {
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && els.screenshotModal.classList.contains('modal--open')) {
                els.screenshotModal.classList.remove('modal--open');
            }
        });
    }

    // ========================================================
    // 工具函数
    // ========================================================
    function formatNumber(n) {
        if (n >= 10000) {
            return (n / 10000).toFixed(1) + 'w';
        }
        if (n >= 1000) {
            return n.toLocaleString();
        }
        return '' + n;
    }

    function getCurrentTimeStr() {
        var now = new Date();
        function pad(n) { return n < 10 ? '0' + n : '' + n; }
        return now.getFullYear() + '-' + pad(now.getMonth() + 1) + '-' + pad(now.getDate()) + ' ' + pad(now.getHours()) + ':' + pad(now.getMinutes()) + ':' + pad(now.getSeconds());
    }

    function trackEvent(eventName, data) {
        console.log('[Admin Track]', eventName, data || {});
    }

    var toastTimer = null;
    function showToast(message) {
        if (toastTimer) clearTimeout(toastTimer);
        els.toast.textContent = message;
        els.toast.classList.add('admin-toast--visible');
        toastTimer = setTimeout(function () {
            els.toast.classList.remove('admin-toast--visible');
        }, 2500);
    }

    // ========================================================
    // 初始化
    // ========================================================
    function init() {
        renderKPI();
        drawTrendChart();
        drawBarChart();
        renderFunnel();
        renderAlerts();

        initTimeRange();
        initChartToggles();
        initScreenshot();
        initAutoRefresh();
        initMisc();
        initKeyboard();

        // 窗口大小变化时重绘图表
        window.addEventListener('resize', function () {
            drawTrendChart();
            drawBarChart();
        });

        trackEvent('admin_dashboard_page_view');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
