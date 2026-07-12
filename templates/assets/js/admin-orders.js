/**
 * admin-orders.js — 后台订单管理交互脚本
 * 功能：订单表格渲染、多维度筛选、统计概览、
 *       CSV/PDF 导出（含数字签名）、订单详情弹窗
 */

(function () {
    'use strict';

    // ============== 配置 ==============
    var CONFIG = {
        storageKey: 'admin_orders',
        pageSize: 10
    };

    // ============== 模拟订单数据 ==============
    var MOCK_ORDERS = [
        { orderNo: 'ORD20260712001', time: '2026-07-12 09:15:23', amount: 2.99, product: 'MBTI 深度职业报告', status: 'paid', txnNo: 'WX4200071209152310001', payMethod: '微信支付', payTime: '2026-07-12 09:15:28', user: 'user_8a3f2c', logs: [{ time: '2026-07-12 09:15:23', author: '系统', action: '创建订单' }, { time: '2026-07-12 09:15:28', author: '微信回调', action: '支付成功' }] },
        { orderNo: 'ORD20260712002', time: '2026-07-12 09:32:11', amount: 2.99, product: 'MBTI 深度职业报告', status: 'paid', txnNo: 'AL202607120932110002', payMethod: '支付宝', payTime: '2026-07-12 09:32:15', user: 'user_3b7e1d', logs: [{ time: '2026-07-12 09:32:11', author: '系统', action: '创建订单' }, { time: '2026-07-12 09:32:15', author: '支付宝回调', action: '支付成功' }] },
        { orderNo: 'ORD20260712003', time: '2026-07-12 10:05:47', amount: 2.99, product: 'MBTI 深度职业报告', status: 'refunding', txnNo: 'WX4200071210054710003', payMethod: '微信支付', payTime: '2026-07-12 10:05:52', user: 'user_5c2a9e', logs: [{ time: '2026-07-12 10:05:47', author: '系统', action: '创建订单' }, { time: '2026-07-12 10:05:52', author: '微信回调', action: '支付成功' }, { time: '2026-07-12 11:20:33', author: '王财务', action: '发起退款' }] },
        { orderNo: 'ORD20260712004', time: '2026-07-12 10:18:39', amount: 2.99, product: 'MBTI 深度职业报告', status: 'paid', txnNo: 'WX4200071210183910004', payMethod: '微信支付', payTime: '2026-07-12 10:18:44', user: 'user_9f4b3a', logs: [{ time: '2026-07-12 10:18:39', author: '系统', action: '创建订单' }, { time: '2026-07-12 10:18:44', author: '微信回调', action: '支付成功' }] },
        { orderNo: 'ORD20260712005', time: '2026-07-12 10:42:15', amount: 2.99, product: 'MBTI 深度职业报告', status: 'paid', txnNo: 'AL202607121042150005', payMethod: '支付宝', payTime: '2026-07-12 10:42:19', user: 'user_1d8c6f', logs: [{ time: '2026-07-12 10:42:15', author: '系统', action: '创建订单' }, { time: '2026-07-12 10:42:19', author: '支付宝回调', action: '支付成功' }] },
        { orderNo: 'ORD20260712006', time: '2026-07-12 11:03:28', amount: 2.99, product: 'MBTI 深度职业报告', status: 'failed', txnNo: '', payMethod: '微信支付', payTime: '', user: 'user_6e2a7b', logs: [{ time: '2026-07-12 11:03:28', author: '系统', action: '创建订单' }, { time: '2026-07-12 11:03:58', author: '微信回调', action: '支付超时' }] },
        { orderNo: 'ORD20260712007', time: '2026-07-12 11:25:52', amount: 2.99, product: 'MBTI 深度职业报告', status: 'paid', txnNo: 'WX4200071211255210007', payMethod: '微信支付', payTime: '2026-07-12 11:25:57', user: 'user_4a9f3c', logs: [{ time: '2026-07-12 11:25:52', author: '系统', action: '创建订单' }, { time: '2026-07-12 11:25:57', author: '微信回调', action: '支付成功' }] },
        { orderNo: 'ORD20260712008', time: '2026-07-12 11:48:30', amount: 2.99, product: 'MBTI 深度职业报告', status: 'refunded', txnNo: 'AL202607121148300008', payMethod: '支付宝', payTime: '2026-07-12 11:48:35', user: 'user_7b3d1e', logs: [{ time: '2026-07-12 11:48:30', author: '系统', action: '创建订单' }, { time: '2026-07-12 11:48:35', author: '支付宝回调', action: '支付成功' }, { time: '2026-07-12 14:20:11', author: '王财务', action: '发起退款' }, { time: '2026-07-12 14:22:45', author: '支付宝回调', action: '退款成功' }] },
        { orderNo: 'ORD20260712009', time: '2026-07-12 12:15:44', amount: 2.99, product: 'MBTI 深度职业报告', status: 'paid', txnNo: 'WX4200071212154410009', payMethod: '微信支付', payTime: '2026-07-12 12:15:49', user: 'user_2c5e8a', logs: [{ time: '2026-07-12 12:15:44', author: '系统', action: '创建订单' }, { time: '2026-07-12 12:15:49', author: '微信回调', action: '支付成功' }] },
        { orderNo: 'ORD20260712010', time: '2026-07-12 12:38:19', amount: 2.99, product: 'MBTI 深度职业报告', status: 'pending', txnNo: '', payMethod: '', payTime: '', user: 'user_8d1f4b', logs: [{ time: '2026-07-12 12:38:19', author: '系统', action: '创建订单，等待支付' }] },
        { orderNo: 'ORD20260712011', time: '2026-07-12 13:02:57', amount: 2.99, product: 'MBTI 深度职业报告', status: 'paid', txnNo: 'AL202607121302570011', payMethod: '支付宝', payTime: '2026-07-12 13:03:01', user: 'user_3e7c2d', logs: [{ time: '2026-07-12 13:02:57', author: '系统', action: '创建订单' }, { time: '2026-07-12 13:03:01', author: '支付宝回调', action: '支付成功' }] },
        { orderNo: 'ORD20260712012', time: '2026-07-12 13:25:33', amount: 2.99, product: 'MBTI 深度职业报告', status: 'paid', txnNo: 'WX4200071213253310012', payMethod: '微信支付', payTime: '2026-07-12 13:25:38', user: 'user_6a9b5f', logs: [{ time: '2026-07-12 13:25:33', author: '系统', action: '创建订单' }, { time: '2026-07-12 13:25:38', author: '微信回调', action: '支付成功' }] },
        { orderNo: 'ORD20260711001', time: '2026-07-11 08:45:12', amount: 2.99, product: 'MBTI 深度职业报告', status: 'paid', txnNo: 'WX420007110845120001', payMethod: '微信支付', payTime: '2026-07-11 08:45:17', user: 'user_5f3a8c', logs: [{ time: '2026-07-11 08:45:12', author: '系统', action: '创建订单' }, { time: '2026-07-11 08:45:17', author: '微信回调', action: '支付成功' }] },
        { orderNo: 'ORD20260711002', time: '2026-07-11 09:20:45', amount: 2.99, product: 'MBTI 深度职业报告', status: 'refunded', txnNo: 'AL202607110920450002', payMethod: '支付宝', payTime: '2026-07-11 09:20:50', user: 'user_9b4e7d', logs: [{ time: '2026-07-11 09:20:45', author: '系统', action: '创建订单' }, { time: '2026-07-11 09:20:50', author: '支付宝回调', action: '支付成功' }, { time: '2026-07-11 15:30:22', author: '王财务', action: '发起退款' }, { time: '2026-07-11 15:33:08', author: '支付宝回调', action: '退款成功' }] },
        { orderNo: 'ORD20260711003', time: '2026-07-11 10:15:08', amount: 2.99, product: 'MBTI 深度职业报告', status: 'paid', txnNo: 'WX420007111015080003', payMethod: '微信支付', payTime: '2026-07-11 10:15:13', user: 'user_1c6f3a', logs: [{ time: '2026-07-11 10:15:08', author: '系统', action: '创建订单' }, { time: '2026-07-11 10:15:13', author: '微信回调', action: '支付成功' }] },
        { orderNo: 'ORD20260711004', time: '2026-07-11 10:48:32', amount: 2.99, product: 'MBTI 深度职业报告', status: 'failed', txnNo: '', payMethod: '支付宝', payTime: '', user: 'user_4d8e2b', logs: [{ time: '2026-07-11 10:48:32', author: '系统', action: '创建订单' }, { time: '2026-07-11 10:49:02', author: '支付宝回调', action: '支付失败：余额不足' }] },
        { orderNo: 'ORD20260711005', time: '2026-07-11 11:30:15', amount: 2.99, product: 'MBTI 深度职业报告', status: 'paid', txnNo: 'WX420007111130150005', payMethod: '微信支付', payTime: '2026-07-11 11:30:20', user: 'user_7e2c9f', logs: [{ time: '2026-07-11 11:30:15', author: '系统', action: '创建订单' }, { time: '2026-07-11 11:30:20', author: '微信回调', action: '支付成功' }] },
        { orderNo: 'ORD20260710001', time: '2026-07-10 14:22:48', amount: 2.99, product: 'MBTI 深度职业报告', status: 'paid', txnNo: 'AL202607101422480001', payMethod: '支付宝', payTime: '2026-07-10 14:22:53', user: 'user_2f5a8d', logs: [{ time: '2026-07-10 14:22:48', author: '系统', action: '创建订单' }, { time: '2026-07-10 14:22:53', author: '支付宝回调', action: '支付成功' }] },
        { orderNo: 'ORD20260710002', time: '2026-07-10 15:05:19', amount: 2.99, product: 'MBTI 深度职业报告', status: 'refunding', txnNo: 'WX420007101505190002', payMethod: '微信支付', payTime: '2026-07-10 15:05:24', user: 'user_8a3d6c', logs: [{ time: '2026-07-10 15:05:19', author: '系统', action: '创建订单' }, { time: '2026-07-10 15:05:24', author: '微信回调', action: '支付成功' }, { time: '2026-07-11 09:15:40', author: '王财务', action: '发起退款' }] },
        { orderNo: 'ORD20260709001', time: '2026-07-09 16:40:55', amount: 2.99, product: 'MBTI 深度职业报告', status: 'paid', txnNo: 'WX420007091640550001', payMethod: '微信支付', payTime: '2026-07-09 16:41:00', user: 'user_6c9e3b', logs: [{ time: '2026-07-09 16:40:55', author: '系统', action: '创建订单' }, { time: '2026-07-09 16:41:00', author: '微信回调', action: '支付成功' }] }
    ];

    var STATUS_MAP = {
        paid: '已支付',
        pending: '待支付',
        refunding: '退款中',
        refunded: '已退款',
        failed: '支付失败'
    };

    // ============== DOM 引用 ==============
    var els = {
        logoutBtn: document.getElementById('logoutBtn'),
        // 统计
        statTotalOrders: document.getElementById('statTotalOrders'),
        statTotalAmount: document.getElementById('statTotalAmount'),
        statSuccessRate: document.getElementById('statSuccessRate'),
        statRefundAmount: document.getElementById('statRefundAmount'),
        // 筛选
        dateStart: document.getElementById('dateStart'),
        dateEnd: document.getElementById('dateEnd'),
        filterStatus: document.getElementById('filterStatus'),
        amountMin: document.getElementById('amountMin'),
        amountMax: document.getElementById('amountMax'),
        searchOrderNo: document.getElementById('searchOrderNo'),
        searchBtn: document.getElementById('searchBtn'),
        resetBtn: document.getElementById('resetBtn'),
        exportCsvBtn: document.getElementById('exportCsvBtn'),
        exportPdfBtn: document.getElementById('exportPdfBtn'),
        // 表格
        selectAll: document.getElementById('selectAll'),
        tableBody: document.getElementById('tableBody'),
        // 分页
        paginationInfo: document.getElementById('paginationInfo'),
        paginationPages: document.getElementById('paginationPages'),
        prevPage: document.getElementById('prevPage'),
        nextPage: document.getElementById('nextPage'),
        pageSizeSelect: document.getElementById('pageSizeSelect'),
        // 详情弹窗
        detailModal: document.getElementById('detailModal'),
        detailOverlay: document.getElementById('detailOverlay'),
        detailBody: document.getElementById('detailBody'),
        detailClose: document.getElementById('detailClose'),
        detailCloseBtn: document.getElementById('detailCloseBtn'),
        detailExportBtn: document.getElementById('detailExportBtn'),
        // 签名弹窗
        signatureModal: document.getElementById('signatureModal'),
        signatureOverlay: document.getElementById('signatureOverlay'),
        signatureDesc: document.getElementById('signatureDesc'),
        signatureInfo: document.getElementById('signatureInfo'),
        signatureConfirm: document.getElementById('signatureConfirm'),
        // 同步信息
        syncInfo: document.getElementById('syncInfo'),
        // Toast
        toast: document.getElementById('adminToast')
    };

    // ============== 状态 ==============
    var state = {
        orders: [],
        currentPage: 1,
        pageSize: 10,
        selectedOrders: new Set(),
        currentDetailOrder: null,
        lastSyncTime: Date.now()
    };

    // ========================================================
    //  1. 数据加载
    // ========================================================
    function loadOrders() {
        var saved = localStorage.getItem(CONFIG.storageKey);
        if (saved) {
            try {
                var parsed = JSON.parse(saved);
                if (Array.isArray(parsed) && parsed.length > 0) {
                    state.orders = parsed;
                    return;
                }
            } catch (e) {}
        }
        state.orders = MOCK_ORDERS.slice();
        saveOrders();
    }

    function saveOrders() {
        localStorage.setItem(CONFIG.storageKey, JSON.stringify(state.orders));
    }

    // ========================================================
    //  2. 表格渲染
    // ========================================================
    function renderTable() {
        var filtered = getFilteredOrders();
        var totalPages = Math.ceil(filtered.length / state.pageSize) || 1;
        if (state.currentPage > totalPages) state.currentPage = totalPages;

        var start = (state.currentPage - 1) * state.pageSize;
        var pageData = filtered.slice(start, start + state.pageSize);

        if (pageData.length === 0) {
            els.tableBody.innerHTML = '<tr><td colspan="8" class="table-empty">' +
                '<svg viewBox="0 0 24 24" width="40" height="40" fill="none" stroke="#d5d8d6" stroke-width="1.5"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/></svg>' +
                '暂无匹配的订单数据</td></tr>';
        } else {
            els.tableBody.innerHTML = pageData.map(renderRow).join('');
            bindRowEvents();
        }

        // 分页信息
        var end = Math.min(start + state.pageSize, filtered.length);
        if (filtered.length === 0) {
            els.paginationInfo.textContent = '共 0 条';
        } else {
            els.paginationInfo.textContent = '共 ' + filtered.length + ' 条，第 ' + (start + 1) + '-' + end + ' 条';
        }

        els.prevPage.disabled = state.currentPage <= 1;
        els.nextPage.disabled = state.currentPage >= totalPages;

        renderPagination(totalPages);
        updateStats();
        updateSelectAllState();
    }

    function renderRow(o) {
        var statusClass = 'status-badge--' + o.status;
        var statusText = STATUS_MAP[o.status] || o.status;
        var amountClass = o.status === 'refunded' || o.status === 'refunding' ? 'table-amount table-amount--refund' : 'table-amount';
        var txnHtml = o.txnNo
            ? '<span class="table-txn">' + escapeHtml(o.txnNo) + '</span>'
            : '<span class="table-txn table-txn--none">—</span>';
        var isChecked = state.selectedOrders.has(o.orderNo);

        return '<tr data-order="' + o.orderNo + '">' +
            '<td class="col-check"><input type="checkbox" class="row-check"' + (isChecked ? ' checked' : '') + '></td>' +
            '<td><span class="table-order-no" data-action="detail">' + escapeHtml(o.orderNo) + '</span></td>' +
            '<td><span class="table-time">' + escapeHtml(o.time) + '</span></td>' +
            '<td><span class="' + amountClass + '">¥' + o.amount.toFixed(2) + '</span></td>' +
            '<td><span class="table-product">' + escapeHtml(o.product) + '</span></td>' +
            '<td><span class="status-badge ' + statusClass + '">' + statusText + '</span></td>' +
            '<td>' + txnHtml + '</td>' +
            '<td class="col-actions"><button class="table-action-btn" data-action="detail" title="查看详情"><svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg></button></td>' +
        '</tr>';
    }

    function bindRowEvents() {
        var rows = els.tableBody.querySelectorAll('tr[data-order]');
        rows.forEach(function (row) {
            var orderNo = row.getAttribute('data-order');

            row.querySelectorAll('[data-action="detail"]').forEach(function (el) {
                el.addEventListener('click', function (e) {
                    e.stopPropagation();
                    openDetailModal(orderNo);
                });
            });

            var checkbox = row.querySelector('.row-check');
            if (checkbox) {
                checkbox.addEventListener('change', function () {
                    if (checkbox.checked) {
                        state.selectedOrders.add(orderNo);
                    } else {
                        state.selectedOrders.delete(orderNo);
                    }
                    updateSelectAllState();
                });
            }
        });
    }

    // ========================================================
    //  3. 筛选
    // ========================================================
    function getFilteredOrders() {
        var dateStart = els.dateStart.value;
        var dateEnd = els.dateEnd.value;
        var status = els.filterStatus.value;
        var amountMin = parseFloat(els.amountMin.value);
        var amountMax = parseFloat(els.amountMax.value);
        var searchNo = els.searchOrderNo.value.trim().toLowerCase();

        return state.orders.filter(function (o) {
            // 时间范围筛选
            var orderDate = o.time.substring(0, 10);
            if (dateStart && orderDate < dateStart) return false;
            if (dateEnd && orderDate > dateEnd) return false;

            // 状态筛选
            if (status && o.status !== status) return false;

            // 金额区间
            if (!isNaN(amountMin) && o.amount < amountMin) return false;
            if (!isNaN(amountMax) && o.amount > amountMax) return false;

            // 订单号精确搜索
            if (searchNo && o.orderNo.toLowerCase().indexOf(searchNo) < 0) return false;

            return true;
        });
    }

    function initFilters() {
        els.searchBtn.addEventListener('click', function () {
            state.currentPage = 1;
            renderTable();
            showToast('查询完成');
            trackEvent('order_search');
        });

        els.searchOrderNo.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                state.currentPage = 1;
                renderTable();
            }
        });

        els.resetBtn.addEventListener('click', function () {
            els.dateStart.value = '2026-07-01';
            els.dateEnd.value = '2026-07-12';
            els.filterStatus.value = '';
            els.amountMin.value = '';
            els.amountMax.value = '';
            els.searchOrderNo.value = '';
            state.currentPage = 1;
            renderTable();
            showToast('筛选已重置');
        });
    }

    // ========================================================
    //  4. 统计更新
    // ========================================================
    function updateStats() {
        var filtered = getFilteredOrders();
        var totalOrders = filtered.length;
        var totalAmount = 0;
        var paidCount = 0;
        var refundAmount = 0;

        filtered.forEach(function (o) {
            if (o.status === 'paid') {
                totalAmount += o.amount;
                paidCount++;
            } else if (o.status === 'refunding' || o.status === 'refunded') {
                refundAmount += o.amount;
            }
        });

        var successRate = totalOrders > 0 ? Math.round((paidCount / totalOrders) * 100) : 0;

        els.statTotalOrders.textContent = totalOrders;
        els.statTotalAmount.textContent = '¥' + totalAmount.toFixed(2);
        els.statSuccessRate.textContent = successRate + '%';
        els.statRefundAmount.textContent = '¥' + refundAmount.toFixed(2);
    }

    // ========================================================
    //  5. 全选 & 批量操作
    // ========================================================
    function initSelectAll() {
        els.selectAll.addEventListener('change', function () {
            var pageData = getFilteredOrders().slice((state.currentPage - 1) * state.pageSize, state.currentPage * state.pageSize);
            if (els.selectAll.checked) {
                pageData.forEach(function (o) { state.selectedOrders.add(o.orderNo); });
            } else {
                pageData.forEach(function (o) { state.selectedOrders.delete(o.orderNo); });
            }
            renderTable();
        });
    }

    function updateSelectAllState() {
        var pageData = getFilteredOrders().slice((state.currentPage - 1) * state.pageSize, state.currentPage * state.pageSize);
        var allChecked = pageData.length > 0 && pageData.every(function (o) { return state.selectedOrders.has(o.orderNo); });
        els.selectAll.checked = allChecked;
    }

    // ========================================================
    //  6. 订单详情弹窗
    // ========================================================
    function openDetailModal(orderNo) {
        var order = findOrder(orderNo);
        if (!order) return;

        state.currentDetailOrder = order;

        var statusClass = 'status-badge--' + order.status;
        var statusText = STATUS_MAP[order.status] || order.status;

        var logsHtml = order.logs.map(function (log) {
            return '<div class="detail-log__item">' +
                '<span class="detail-log__time">' + log.time + '</span>' +
                '<span class="detail-log__content"><strong>' + escapeHtml(log.author) + '</strong> ' + escapeHtml(log.action) + '</span>' +
            '</div>';
        }).join('');

        els.detailBody.innerHTML =
            '<div class="detail-section">' +
                '<div class="detail-section__title">' +
                    '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>' +
                    '订单信息' +
                '</div>' +
                '<div class="detail-grid">' +
                    '<div class="detail-item detail-item--full">' +
                        '<span class="detail-item__label">商户订单号</span>' +
                        '<span class="detail-item__value detail-item__value--mono">' + escapeHtml(order.orderNo) + '</span>' +
                    '</div>' +
                    '<div class="detail-item">' +
                        '<span class="detail-item__label">下单时间</span>' +
                        '<span class="detail-item__value">' + escapeHtml(order.time) + '</span>' +
                    '</div>' +
                    '<div class="detail-item">' +
                        '<span class="detail-item__label">订单状态</span>' +
                        '<span class="status-badge ' + statusClass + '">' + statusText + '</span>' +
                    '</div>' +
                    '<div class="detail-item">' +
                        '<span class="detail-item__label">商品名称</span>' +
                        '<span class="detail-item__value">' + escapeHtml(order.product) + '</span>' +
                    '</div>' +
                    '<div class="detail-item">' +
                        '<span class="detail-item__label">支付金额</span>' +
                        '<span class="detail-item__value detail-item__value--amount">¥' + order.amount.toFixed(2) + '</span>' +
                    '</div>' +
                '</div>' +
            '</div>' +
            '<div class="detail-section">' +
                '<div class="detail-section__title">' +
                    '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/></svg>' +
                    '支付信息' +
                '</div>' +
                '<div class="detail-grid">' +
                    '<div class="detail-item">' +
                        '<span class="detail-item__label">支付方式</span>' +
                        '<span class="detail-item__value">' + (order.payMethod || '—') + '</span>' +
                    '</div>' +
                    '<div class="detail-item">' +
                        '<span class="detail-item__label">支付时间</span>' +
                        '<span class="detail-item__value">' + (order.payTime || '—') + '</span>' +
                    '</div>' +
                    '<div class="detail-item detail-item--full">' +
                        '<span class="detail-item__label">交易号</span>' +
                        '<span class="detail-item__value detail-item__value--mono">' + (order.txnNo || '—') + '</span>' +
                    '</div>' +
                    '<div class="detail-item">' +
                        '<span class="detail-item__label">用户标识</span>' +
                        '<span class="detail-item__value detail-item__value--mono">' + escapeHtml(order.user) + '</span>' +
                    '</div>' +
                '</div>' +
            '</div>' +
            '<div class="detail-section">' +
                '<div class="detail-section__title">' +
                    '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>' +
                    '操作日志' +
                '</div>' +
                '<div class="detail-log">' + logsHtml + '</div>' +
            '</div>';

        els.detailModal.classList.add('modal--open');
        trackEvent('order_detail_view', { orderNo: orderNo });
    }

    function closeDetailModal() {
        els.detailModal.classList.remove('modal--open');
        state.currentDetailOrder = null;
    }

    function initDetailModal() {
        els.detailClose.addEventListener('click', closeDetailModal);
        els.detailCloseBtn.addEventListener('click', closeDetailModal);
        els.detailOverlay.addEventListener('click', closeDetailModal);

        els.detailExportBtn.addEventListener('click', function () {
            if (!state.currentDetailOrder) return;
            exportOrders([state.currentDetailOrder], '单笔订单');
        });
    }

    // ========================================================
    //  7. 导出 CSV
    // ========================================================
    function exportOrders(orders, label) {
        var csv = '商户订单号,下单时间,支付金额,商品名称,订单状态,支付方式,交易号,支付时间,用户标识\n';
        orders.forEach(function (o) {
            csv += [
                o.orderNo,
                o.time,
                o.amount.toFixed(2),
                '"' + o.product + '"',
                STATUS_MAP[o.status] || o.status,
                o.payMethod || '',
                o.txnNo || '',
                o.payTime || '',
                o.user
            ].join(',') + '\n';
        });

        // 生成数字签名（模拟 HMAC-SHA256）
        var signature = generateSignature(csv);
        csv += '\n--- 数字签名 ---\n';
        csv += '算法：HMAC-SHA256\n';
        csv += '签名：' + signature + '\n';
        csv += '生成时间：' + getCurrentTimeStr() + '\n';
        csv += '导出人：王财务\n';

        var blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' });
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = 'orders_export_' + new Date().toISOString().substring(0, 10) + '.csv';
        a.click();
        URL.revokeObjectURL(url);

        // 显示签名确认弹窗
        showSignatureModal(label, signature, orders.length);
        trackEvent('order_export', { format: 'csv', count: orders.length, label: label });
    }

    function initExport() {
        els.exportCsvBtn.addEventListener('click', function () {
            var filtered = getFilteredOrders();
            if (filtered.length === 0) {
                showToast('没有可导出的订单数据');
                return;
            }
            exportOrders(filtered, '全部筛选订单');
        });

        els.exportPdfBtn.addEventListener('click', function () {
            var filtered = getFilteredOrders();
            if (filtered.length === 0) {
                showToast('没有可导出的订单数据');
                return;
            }

            // 模拟 PDF 导出（实际使用打印）
            var signature = generateSignature('pdf:' + filtered.length);
            showToast('PDF 导出中...');

            setTimeout(function () {
                showSignatureModal('PDF 报表', signature, filtered.length);
                trackEvent('order_export', { format: 'pdf', count: filtered.length });
            }, 800);
        });
    }

    // ========================================================
    //  8. 签名确认弹窗
    // ========================================================
    function showSignatureModal(label, signature, count) {
        els.signatureDesc.textContent = label + '（共 ' + count + ' 条）已添加数字签名，可用于验证文件完整性';
        els.signatureInfo.innerHTML =
            '<div class="signature-info__row">' +
                '<span class="signature-info__label">签名算法</span>' +
                '<span class="signature-info__value">HMAC-SHA256</span>' +
            '</div>' +
            '<div class="signature-info__row">' +
                '<span class="signature-info__label">数字签名</span>' +
                '<span class="signature-info__value">' + signature + '</span>' +
            '</div>' +
            '<div class="signature-info__row">' +
                '<span class="signature-info__label">生成时间</span>' +
                '<span class="signature-info__value">' + getCurrentTimeStr() + '</span>' +
            '</div>' +
            '<div class="signature-info__row">' +
                '<span class="signature-info__label">文件记录数</span>' +
                '<span class="signature-info__value">' + count + ' 条</span>' +
            '</div>';

        els.signatureModal.classList.add('modal--open');
    }

    function initSignatureModal() {
        els.signatureConfirm.addEventListener('click', function () {
            els.signatureModal.classList.remove('modal--open');
        });
        els.signatureOverlay.addEventListener('click', function () {
            els.signatureModal.classList.remove('modal--open');
        });
    }

    // ========================================================
    //  9. 分页
    // ========================================================
    function renderPagination(totalPages) {
        var html = '';
        var maxVisible = 5;
        var start = Math.max(1, state.currentPage - 2);
        var end = Math.min(totalPages, start + maxVisible - 1);
        if (end - start < maxVisible - 1) {
            start = Math.max(1, end - maxVisible + 1);
        }

        if (start > 1) {
            html += '<button class="pagination__page" data-page="1">1</button>';
            if (start > 2) html += '<span class="pagination__ellipsis">...</span>';
        }

        for (var i = start; i <= end; i++) {
            html += '<button class="pagination__page' + (i === state.currentPage ? ' pagination__page--active' : '') + '" data-page="' + i + '">' + i + '</button>';
        }

        if (end < totalPages) {
            if (end < totalPages - 1) html += '<span class="pagination__ellipsis">...</span>';
            html += '<button class="pagination__page" data-page="' + totalPages + '">' + totalPages + '</button>';
        }

        els.paginationPages.innerHTML = html;

        els.paginationPages.querySelectorAll('[data-page]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                state.currentPage = parseInt(btn.getAttribute('data-page'), 10);
                renderTable();
            });
        });
    }

    function initPagination() {
        els.prevPage.addEventListener('click', function () {
            if (state.currentPage > 1) {
                state.currentPage--;
                renderTable();
            }
        });

        els.nextPage.addEventListener('click', function () {
            var total = Math.ceil(getFilteredOrders().length / state.pageSize);
            if (state.currentPage < total) {
                state.currentPage++;
                renderTable();
            }
        });

        els.pageSizeSelect.addEventListener('change', function () {
            state.pageSize = parseInt(els.pageSizeSelect.value, 10);
            state.currentPage = 1;
            renderTable();
        });
    }

    // ========================================================
    // 10. 数据同步时间更新
    // ========================================================
    function initSyncInfo() {
        updateSyncTime();
        setInterval(updateSyncTime, 60000);
    }

    function updateSyncTime() {
        var elapsed = Math.floor((Date.now() - state.lastSyncTime) / 1000);
        var text;
        if (elapsed < 60) {
            text = '刚刚';
        } else if (elapsed < 300) {
            text = Math.floor(elapsed / 60) + ' 分钟前';
        } else {
            text = '已超 5 分钟';
        }
        els.syncInfo.querySelector('span').textContent = '数据同步：' + text;
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
                if (page === 'orders') return;
                showToast('「' + item.querySelector('span').textContent + '」页面开发中');
            });
        });
    }

    // ========================================================
    // 12. ESC 键关闭
    // ========================================================
    function initKeyboard() {
        document.addEventListener('keydown', function (e) {
            if (e.key !== 'Escape') return;

            if (els.signatureModal.classList.contains('modal--open')) {
                els.signatureModal.classList.remove('modal--open');
                return;
            }
            if (els.detailModal.classList.contains('modal--open')) {
                closeDetailModal();
                return;
            }
        });
    }

    // ========================================================
    // 工具函数
    // ========================================================
    function findOrder(orderNo) {
        return state.orders.find(function (o) { return o.orderNo === orderNo; });
    }

    function escapeHtml(str) {
        if (!str) return '';
        return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function getCurrentTimeStr() {
        var now = new Date();
        function pad(n) { return n < 10 ? '0' + n : '' + n; }
        return now.getFullYear() + '-' + pad(now.getMonth() + 1) + '-' + pad(now.getDate()) + ' ' + pad(now.getHours()) + ':' + pad(now.getMinutes()) + ':' + pad(now.getSeconds());
    }

    function generateSignature(data) {
        // 模拟 HMAC-SHA256 签名生成
        var hash = 0;
        for (var i = 0; i < data.length; i++) {
            hash = ((hash << 5) - hash) + data.charCodeAt(i);
            hash = hash & hash;
        }
        var hex = Math.abs(hash).toString(16);
        // 扩展为 64 字符伪签名
        while (hex.length < 64) {
            hex += (Math.abs(hash * (hex.length + 1))).toString(16);
        }
        return hex.substring(0, 64);
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
        loadOrders();
        renderTable();

        initFilters();
        initSelectAll();
        initDetailModal();
        initExport();
        initSignatureModal();
        initPagination();
        initSyncInfo();
        initMisc();
        initKeyboard();

        trackEvent('admin_orders_page_view');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
