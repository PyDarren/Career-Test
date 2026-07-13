/**
 * orders.js — 订单管理页交互脚本
 * 功能：订单筛选、卡片渲染、订单详情、退款申请、发票申领、PDF 导出
 */

(function () {
    'use strict';

    // ============== 配置 ==============
    var CONFIG = {
        storageKey: 'career_test_orders',
        versionKey: 'career_test_orders_version',
        dataVersion: '2.0',
        exportSteps: ['正在收集订单数据...', '正在生成账单...', '正在渲染 PDF...', '导出完成'],
        refundableDays: 7  // 7 天内可退款
    };

    // ============== 模拟订单数据 ==============
    var MOCK_ORDERS = [
        {
            id: 'CT202607120001',
            date: '2026-07-12',
            dateLabel: '2026-07-12 14:32',
            productName: '职业人格深度报告',
            amount: 2.99,
            originalAmount: 9.90,
            payMethod: '微信支付',
            status: 'completed',
            invoiceStatus: 'none',
            reportUrl: 'deep-report.html',
            typeCode: '沉稳架构师·IRC'
        },
        {
            id: 'CT202606280002',
            date: '2026-06-28',
            dateLabel: '2026-06-28 09:15',
            productName: '职业人格深度报告',
            amount: 2.99,
            originalAmount: 9.90,
            payMethod: '支付宝',
            status: 'refunding',
            refundReason: '重复购买',
            refundTime: '2026-07-01 10:00',
            invoiceStatus: 'none',
            reportUrl: 'deep-report.html',
            typeCode: '灵感传播者·AES'
        },
        {
            id: 'CT202605150003',
            date: '2026-05-15',
            dateLabel: '2026-05-15 16:48',
            productName: '职业人格深度报告',
            amount: 2.99,
            originalAmount: 9.90,
            payMethod: '微信支付',
            status: 'completed',
            invoiceStatus: 'issued',
            reportUrl: 'deep-report.html',
            typeCode: '沉稳架构师·IRC'
        }
    ];

    // ============== DOM 元素引用 ==============
    var els = {
        backBtn:          document.getElementById('backBtn'),
        exportAllBtn:     document.getElementById('exportAllBtn'),
        tabs:             document.getElementById('ordersTabs'),
        ordersList:       document.getElementById('ordersList'),
        ordersEmpty:      document.getElementById('ordersEmpty'),
        ordersFooter:     document.getElementById('ordersFooter'),
        countAll:         document.getElementById('countAll'),
        countCompleted:   document.getElementById('countCompleted'),
        countRefunding:   document.getElementById('countRefunding'),
        totalSpent:       document.getElementById('totalSpent'),
        validCount:       document.getElementById('validCount'),
        exportPdfBtn:     document.getElementById('exportPdfBtn'),
        // 详情弹窗
        detailModal:      document.getElementById('detailModal'),
        detailOverlay:    document.getElementById('detailOverlay'),
        detailClose:      document.getElementById('detailClose'),
        detailBody:       document.getElementById('detailBody'),
        // 退款弹窗
        refundModal:      document.getElementById('refundModal'),
        refundOverlay:    document.getElementById('refundOverlay'),
        refundInfo:       document.getElementById('refundInfo'),
        refundReason:     document.getElementById('refundReason'),
        refundDesc:       document.getElementById('refundDesc'),
        refundCancel:     document.getElementById('refundCancel'),
        refundConfirm:    document.getElementById('refundConfirm'),
        // 发票弹窗
        invoiceModal:     document.getElementById('invoiceModal'),
        invoiceOverlay:   document.getElementById('invoiceOverlay'),
        invoiceClose:     document.getElementById('invoiceClose'),
        invoicePreview:   document.getElementById('invoicePreview'),
        invoiceTitle:     document.getElementById('invoiceTitle'),
        taxField:         document.getElementById('taxField'),
        taxNumber:        document.getElementById('taxNumber'),
        invoiceEmail:     document.getElementById('invoiceEmail'),
        invoiceCancel:    document.getElementById('invoiceCancel'),
        invoiceConfirm:   document.getElementById('invoiceConfirm'),
        // 导出弹窗
        exportModal:      document.getElementById('exportModal'),
        exportOverlay:    document.getElementById('exportOverlay'),
        exportProgressFill: document.getElementById('exportProgressFill'),
        exportProgressText: document.getElementById('exportProgressText'),
        // Toast
        toast:            document.getElementById('ordersToast')
    };

    // ============== 内部状态 ==============
    var state = {
        orders: [],
        currentFilter: 'all',
        currentDetailId: null,
        currentRefundId: null,
        currentInvoiceId: null
    };

    // ========================================================
    //  1. 数据加载
    // ========================================================
    function loadOrders() {
        var savedVersion = localStorage.getItem(CONFIG.versionKey);
        if (savedVersion !== CONFIG.dataVersion) {
            localStorage.removeItem(CONFIG.storageKey);
            localStorage.setItem(CONFIG.versionKey, CONFIG.dataVersion);
        }
        var saved = localStorage.getItem(CONFIG.storageKey);
        if (saved) {
            try {
                var parsed = JSON.parse(saved);
                if (Array.isArray(parsed) && parsed.length > 0) {
                    state.orders = parsed;
                    return;
                }
            } catch (e) {
                // ignore
            }
        }
        state.orders = MOCK_ORDERS.slice();
        saveOrders();
    }

    function saveOrders() {
        localStorage.setItem(CONFIG.storageKey, JSON.stringify(state.orders));
    }

    // ========================================================
    //  2. 渲染订单列表
    // ========================================================
    function renderOrders() {
        var filtered = filterOrders();
        updateCounts();
        updateFooter();

        if (filtered.length === 0) {
            els.ordersList.style.display = 'none';
            els.ordersEmpty.style.display = 'flex';
            els.ordersFooter.style.display = 'none';
            return;
        }

        els.ordersList.style.display = 'flex';
        els.ordersEmpty.style.display = 'none';
        els.ordersFooter.style.display = 'flex';

        // 按时间倒序
        filtered.sort(function (a, b) {
            return new Date(b.date) - new Date(a.date);
        });

        els.ordersList.innerHTML = filtered.map(renderCard).join('');
        bindCardEvents();
    }

    function filterOrders() {
        if (state.currentFilter === 'all') {
            return state.orders.slice();
        }
        return state.orders.filter(function (o) {
            return o.status === state.currentFilter;
        });
    }

    function renderCard(order) {
        var statusClass = 'order-card__status--' + order.status;
        var statusText = {
            'completed': '已完成',
            'refunding': '退款中',
            'refunded': '已退款'
        }[order.status] || order.status;

        // 操作按钮
        var actions = '';
        if (order.status === 'completed') {
            actions =
                '<button class="order-action-btn order-action-btn--primary" data-action="detail">' +
                    '<svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>' +
                    '查看详情' +
                '</button>' +
                '<button class="order-action-btn" data-action="invoice">' +
                    '<svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="16" rx="2"/><line x1="8" y1="10" x2="16" y2="10"/><line x1="8" y1="14" x2="14" y2="14"/></svg>' +
                    (order.invoiceStatus === 'issued' ? '查看发票' : '申领发票') +
                '</button>' +
                '<button class="order-action-btn order-action-btn--danger" data-action="refund">' +
                    '<svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>' +
                    '申请退款' +
                '</button>';
        } else if (order.status === 'refunding') {
            actions =
                '<button class="order-action-btn" data-action="detail">查看详情</button>' +
                '<button class="order-action-btn" data-action="cancel-refund">撤销退款</button>';
        } else if (order.status === 'refunded') {
            actions =
                '<button class="order-action-btn" data-action="detail">查看详情</button>';
        }

        return '' +
            '<div class="order-card" data-id="' + order.id + '">' +
                '<div class="order-card__header">' +
                    '<span class="order-card__date">' + order.dateLabel + '</span>' +
                    '<span class="order-card__status ' + statusClass + '">' + statusText + '</span>' +
                '</div>' +
                '<div class="order-card__body">' +
                    '<div class="order-card__icon">' +
                        '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="#9B7ED8" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>' +
                    '</div>' +
                    '<div class="order-card__info">' +
                        '<div class="order-card__name">' + order.productName + '</div>' +
                        '<div class="order-card__id">' + order.id + '</div>' +
                    '</div>' +
                    '<div class="order-card__amount">' +
                        '<span class="order-card__price"><span class="order-card__price-symbol">¥</span>' + order.amount.toFixed(2) + '</span>' +
                    '</div>' +
                '</div>' +
                '<div class="order-card__actions">' + actions + '</div>' +
            '</div>';
    }

    // ========================================================
    //  3. 更新计数 & 汇总
    // ========================================================
    function updateCounts() {
        els.countAll.textContent = state.orders.length;
        els.countCompleted.textContent = state.orders.filter(function (o) { return o.status === 'completed'; }).length;
        els.countRefunding.textContent = state.orders.filter(function (o) { return o.status === 'refunding'; }).length;
    }

    function updateFooter() {
        var total = 0;
        var valid = 0;
        state.orders.forEach(function (o) {
            if (o.status === 'completed') {
                total += o.amount;
                valid++;
            }
        });
        els.totalSpent.textContent = '¥' + total.toFixed(2);
        els.validCount.textContent = valid;
    }

    // ========================================================
    //  4. 卡片事件绑定
    // ========================================================
    function bindCardEvents() {
        var cards = els.ordersList.querySelectorAll('.order-card');
        cards.forEach(function (card) {
            var id = card.getAttribute('data-id');

            card.querySelectorAll('[data-action]').forEach(function (btn) {
                btn.addEventListener('click', function (e) {
                    e.stopPropagation();
                    var action = btn.getAttribute('data-action');
                    handleAction(action, id);
                });
            });
        });
    }

    function handleAction(action, id) {
        switch (action) {
            case 'detail':
                openDetail(id);
                break;
            case 'invoice':
                openInvoice(id);
                break;
            case 'refund':
                openRefund(id);
                break;
            case 'cancel-refund':
                cancelRefund(id);
                break;
        }
    }

    // ========================================================
    //  5. 筛选标签
    // ========================================================
    function initTabs() {
        var tabs = els.tabs.querySelectorAll('.orders-tab');
        tabs.forEach(function (tab) {
            tab.addEventListener('click', function () {
                tabs.forEach(function (t) { t.classList.remove('orders-tab--active'); });
                tab.classList.add('orders-tab--active');
                state.currentFilter = tab.getAttribute('data-filter');
                renderOrders();
                trackEvent('order_filter', { filter: state.currentFilter });
            });
        });
    }

    // ========================================================
    //  6. 订单详情
    // ========================================================
    function openDetail(id) {
        var order = findOrder(id);
        if (!order) return;

        state.currentDetailId = id;

        var statusText = {
            'completed': '已完成',
            'refunding': '退款中',
            'refunded': '已退款'
        }[order.status];

        var html = '';

        // 订单信息
        html += '<div class="detail-section">';
        html += '<h4 class="detail-section__title">订单信息</h4>';
        html += detailRow('订单编号', order.id, 'mono');
        html += detailRow('下单时间', order.dateLabel);
        html += detailRow('商品名称', order.productName);
        html += detailRow('订单状态', statusText);
        html += '</div>';

        // 支付信息
        html += '<div class="detail-section">';
        html += '<h4 class="detail-section__title">支付信息</h4>';
        html += detailRow('支付方式', order.payMethod);
        html += detailRow('原价', '¥' + order.originalAmount.toFixed(2));
        html += detailRow('实付金额', '¥' + order.amount.toFixed(2), 'price');
        html += '</div>';

        // 退款信息（如有）
        if (order.status === 'refunding' || order.status === 'refunded') {
            html += '<div class="detail-section">';
            html += '<h4 class="detail-section__title">退款信息</h4>';
            html += detailRow('退款原因', order.refundReason || '—');
            html += detailRow('申请时间', order.refundTime || '—');
            if (order.status === 'refunding') {
                html += detailRow('预计到账', '1-3 个工作日');
            }
            if (order.status === 'refunded') {
                html += detailRow('退款金额', '¥' + order.amount.toFixed(2), 'price');
            }
            html += '</div>';
        }

        // 发票信息
        html += '<div class="detail-section">';
        html += '<h4 class="detail-section__title">发票信息</h4>';
        var invoiceText = order.invoiceStatus === 'issued' ? '已开具' : '未申领';
        html += detailRow('发票状态', invoiceText);
        html += '</div>';

        // 操作入口
        html += '<div class="detail-actions">';
        if (order.status === 'completed') {
            html += detailAction('purple', '查看深度报告', '跳转至报告阅读页', 'view-report');
            html += detailAction('gold', order.invoiceStatus === 'issued' ? '查看发票' : '申领发票', '电子发票 PDF', 'invoice');
            html += detailAction('danger', '申请退款', '7 天内可退款', 'refund');
        }
        html += '</div>';

        els.detailBody.innerHTML = html;

        // 绑定详情操作
        els.detailBody.querySelectorAll('[data-detail-action]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var action = btn.getAttribute('data-detail-action');
                closeModal(els.detailModal);
                setTimeout(function () {
                    if (action === 'view-report') {
                        window.location.href = order.reportUrl;
                    } else if (action === 'invoice') {
                        openInvoice(id);
                    } else if (action === 'refund') {
                        openRefund(id);
                    }
                }, 200);
            });
        });

        openModal(els.detailModal);
        trackEvent('order_detail_view', { id: id });
    }

    function detailRow(label, value, modifier) {
        var valueClass = 'detail-row__value';
        if (modifier) valueClass += ' detail-row__value--' + modifier;
        return '<div class="detail-row"><span class="detail-row__label">' + label +
            '</span><span class="' + valueClass + '">' + value + '</span></div>';
    }

    function detailAction(iconColor, title, desc, action) {
        var icons = {
            'purple': '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="#9B7ED8" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>',
            'gold': '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="#deb45c" stroke-width="2"><rect x="3" y="4" width="18" height="16" rx="2"/><line x1="8" y1="10" x2="16" y2="10"/><line x1="8" y1="14" x2="14" y2="14"/></svg>',
            'danger': '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="#e17055" stroke-width="2"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>'
        };
        return '<button class="detail-action" data-detail-action="' + action + '">' +
            '<div class="detail-action__icon detail-action__icon--' + iconColor + '">' + (icons[iconColor] || '') + '</div>' +
            '<div class="detail-action__body"><div class="detail-action__title">' + title + '</div><div class="detail-action__desc">' + desc + '</div></div>' +
            '<svg class="detail-action__arrow" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>' +
            '</button>';
    }

    // ========================================================
    //  7. 退款申请
    // ========================================================
    function openRefund(id) {
        var order = findOrder(id);
        if (!order) return;
        if (order.status !== 'completed') {
            showToast('该订单状态不支持退款');
            return;
        }

        // 检查是否在退款期限内
        var orderDate = new Date(order.date);
        var daysDiff = (Date.now() - orderDate.getTime()) / (1000 * 60 * 60 * 24);
        if (daysDiff > CONFIG.refundableDays) {
            showToast('超过 ' + CONFIG.refundableDays + ' 天，无法退款');
            return;
        }

        state.currentRefundId = id;

        els.refundInfo.innerHTML =
            '<div class="refund-info__row"><span class="refund-info__label">商品名称</span><span class="refund-info__value">' + order.productName + '</span></div>' +
            '<div class="refund-info__row"><span class="refund-info__label">订单编号</span><span class="refund-info__value">' + order.id + '</span></div>' +
            '<div class="refund-info__row"><span class="refund-info__label">退款金额</span><span class="refund-info__value refund-info__value--price">¥' + order.amount.toFixed(2) + '</span></div>';

        els.refundReason.value = '';
        els.refundDesc.value = '';
        els.refundConfirm.disabled = true;

        openModal(els.refundModal);
        trackEvent('refund_modal_open', { id: id });
    }

    function initRefund() {
        // 选中原因后启用按钮
        els.refundReason.addEventListener('change', function () {
            els.refundConfirm.disabled = !els.refundReason.value;
        });

        els.refundConfirm.addEventListener('click', function () {
            if (!state.currentRefundId) return;
            var reason = els.refundReason.value;
            if (!reason) {
                showToast('请选择退款原因');
                return;
            }

            var order = findOrder(state.currentRefundId);
            if (!order) return;

            order.status = 'refunding';
            order.refundReason = reason;
            order.refundTime = new Date().toISOString().substring(0, 16).replace('T', ' ');
            saveOrders();
            renderOrders();
            closeModal(els.refundModal);

            showToast('退款申请已提交');
            trackEvent('refund_submit', {
                id: order.id,
                reason: reason,
                amount: order.amount
            });
        });

        els.refundCancel.addEventListener('click', function () {
            closeModal(els.refundModal);
        });

        els.refundOverlay.addEventListener('click', function () {
            closeModal(els.refundModal);
        });
    }

    function cancelRefund(id) {
        var order = findOrder(id);
        if (!order || order.status !== 'refunding') return;

        if (!confirm('确认撤销退款申请？')) return;

        order.status = 'completed';
        delete order.refundReason;
        delete order.refundTime;
        saveOrders();
        renderOrders();

        showToast('退款已撤销');
        trackEvent('refund_cancel', { id: id });
    }

    // ========================================================
    //  8. 发票申领
    // ========================================================
    function openInvoice(id) {
        var order = findOrder(id);
        if (!order) return;

        state.currentInvoiceId = id;

        // 预览信息
        els.invoicePreview.innerHTML =
            '<div class="invoice-preview__row"><span class="invoice-preview__label">订单编号</span><span class="invoice-preview__value">' + order.id + '</span></div>' +
            '<div class="invoice-preview__row"><span class="invoice-preview__label">商品名称</span><span class="invoice-preview__value">' + order.productName + '</span></div>' +
            '<div class="invoice-preview__row"><span class="invoice-preview__label">金额</span><span class="invoice-preview__value">¥' + order.amount.toFixed(2) + '</span></div>';

        els.invoiceTitle.value = '';
        els.taxNumber.value = '';
        els.invoiceEmail.value = '';

        // 重置为个人
        var personalRadio = els.invoiceModal.querySelector('input[value="personal"]');
        if (personalRadio) personalRadio.checked = true;
        els.taxField.style.display = 'none';

        openModal(els.invoiceModal);
        trackEvent('invoice_modal_open', { id: id });
    }

    function initInvoice() {
        // 抬头类型切换
        var radios = els.invoiceModal.querySelectorAll('input[name="invoiceType"]');
        radios.forEach(function (radio) {
            radio.addEventListener('change', function () {
                els.taxField.style.display = radio.value === 'enterprise' && radio.checked ? 'block' : 'none';
            });
        });

        els.invoiceConfirm.addEventListener('click', function () {
            if (!state.currentInvoiceId) return;

            var title = els.invoiceTitle.value.trim();
            var email = els.invoiceEmail.value.trim();
            var type = els.invoiceModal.querySelector('input[name="invoiceType"]:checked').value;

            if (!title) {
                showToast('请输入发票抬头');
                return;
            }
            if (type === 'enterprise' && !els.taxNumber.value.trim()) {
                showToast('请输入企业税号');
                return;
            }
            if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
                showToast('请输入正确的邮箱地址');
                return;
            }

            var order = findOrder(state.currentInvoiceId);
            if (!order) return;

            order.invoiceStatus = 'issued';
            order.invoiceTitle = title;
            order.invoiceType = type;
            saveOrders();
            renderOrders();
            closeModal(els.invoiceModal);

            showToast('发票申领成功，PDF 将发送至邮箱');
            trackEvent('invoice_submit', {
                id: order.id,
                type: type,
                title: title
            });
        });

        els.invoiceCancel.addEventListener('click', function () {
            closeModal(els.invoiceModal);
        });

        els.invoiceClose.addEventListener('click', function () {
            closeModal(els.invoiceModal);
        });

        els.invoiceOverlay.addEventListener('click', function () {
            closeModal(els.invoiceModal);
        });
    }

    // ========================================================
    //  9. PDF 导出
    // ========================================================
    function initExport() {
        els.exportPdfBtn.addEventListener('click', startExport);
        els.exportAllBtn.addEventListener('click', startExport);
    }

    function startExport() {
        if (state.orders.length === 0) {
            showToast('暂无订单可导出');
            return;
        }

        openModal(els.exportModal);

        var step = 0;
        els.exportProgressFill.style.width = '0%';
        els.exportProgressText.textContent = CONFIG.exportSteps[0];

        var progress = 0;
        var interval = setInterval(function () {
            progress += Math.random() * 18 + 8;
            if (progress >= 100) {
                progress = 100;
                clearInterval(interval);
            }

            els.exportProgressFill.style.width = progress + '%';

            var newStep = Math.min(Math.floor(progress / 25), CONFIG.exportSteps.length - 1);
            if (newStep !== step) {
                step = newStep;
                els.exportProgressText.textContent = CONFIG.exportSteps[step];
            }

            if (progress >= 100) {
                setTimeout(function () {
                    closeModal(els.exportModal);

                    // 生成 PDF 账单（模拟 — 生成文本文件）
                    var content = generateBillContent();
                    var blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
                    var url = URL.createObjectURL(blob);
                    var a = document.createElement('a');
                    a.href = url;
                    a.download = 'career_test_bill_' + new Date().toISOString().substring(0, 10) + '.txt';
                    a.click();
                    URL.revokeObjectURL(url);

                    showToast('PDF 账单已生成并下载');
                    trackEvent('bill_export', { orderCount: state.orders.length });
                }, 500);
            }
        }, 200);
    }

    function generateBillContent() {
        var lines = [];
        lines.push('================================');
        lines.push('   画己职测 消费账单');
        lines.push('   生成日期：' + new Date().toLocaleString('zh-CN'));
        lines.push('================================');
        lines.push('');

        var total = 0;
        state.orders.forEach(function (o, i) {
            lines.push('【订单 ' + (i + 1) + '】');
            lines.push('  订单编号：' + o.id);
            lines.push('  下单时间：' + o.dateLabel);
            lines.push('  商品名称：' + o.productName);
            lines.push('  支付方式：' + o.payMethod);
            lines.push('  实付金额：¥' + o.amount.toFixed(2));
            lines.push('  订单状态：' + ({ completed: '已完成', refunding: '退款中', refunded: '已退款' }[o.status]));
            lines.push('');

            if (o.status === 'completed') {
                total += o.amount;
            }
        });

        lines.push('--------------------------------');
        lines.push('累计消费：¥' + total.toFixed(2));
        lines.push('有效订单：' + state.orders.filter(function (o) { return o.status === 'completed'; }).length + ' 笔');
        lines.push('--------------------------------');

        return lines.join('\n');
    }

    // ========================================================
    // 10. 详情弹窗关闭
    // ========================================================
    function initDetailClose() {
        els.detailClose.addEventListener('click', function () {
            closeModal(els.detailModal);
        });
        els.detailOverlay.addEventListener('click', function () {
            closeModal(els.detailModal);
        });
    }

    // ========================================================
    // 11. 返回按钮
    // ========================================================
    function initBackBtn() {
        els.backBtn.addEventListener('click', function () {
            if (window.history.length > 1) {
                window.history.back();
            } else {
                window.location.href = 'index.html';
            }
        });
    }

    // ========================================================
    // 12. ESC 关闭弹窗
    // ========================================================
    function initKeyboard() {
        document.addEventListener('keydown', function (e) {
            if (e.key !== 'Escape') return;

            var modals = [els.detailModal, els.refundModal, els.invoiceModal, els.exportModal];
            for (var i = 0; i < modals.length; i++) {
                if (modals[i].classList.contains('modal--open')) {
                    closeModal(modals[i]);
                    return;
                }
            }
        });
    }

    // ========================================================
    // 工具函数
    // ========================================================
    function findOrder(id) {
        return state.orders.find(function (o) {
            return o.id === id;
        });
    }

    function openModal(modalEl) {
        modalEl.classList.add('modal--open');
        document.body.style.overflow = 'hidden';
    }

    function closeModal(modalEl) {
        modalEl.classList.remove('modal--open');
        document.body.style.overflow = '';
    }

    function trackEvent(eventName, data) {
        console.log('[Track]', eventName, data || {});
        // 后端接入后替换为真实埋点 API
        // fetch('/api/stats/track/', {
        //     method: 'POST',
        //     headers: { 'Content-Type': 'application/json' },
        //     body: JSON.stringify({ event: eventName, ...data })
        // });
    }

    var toastTimer = null;
    function showToast(message) {
        if (toastTimer) {
            clearTimeout(toastTimer);
        }

        els.toast.textContent = message;
        els.toast.classList.add('orders-toast--visible');

        toastTimer = setTimeout(function () {
            els.toast.classList.remove('orders-toast--visible');
        }, 2500);
    }

    // ========================================================
    // 初始化
    // ========================================================
    function init() {
        loadOrders();
        renderOrders();
        initTabs();
        initDetailClose();
        initRefund();
        initInvoice();
        initExport();
        initBackBtn();
        initKeyboard();

        trackEvent('orders_page_view', {
            orderCount: state.orders.length
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
