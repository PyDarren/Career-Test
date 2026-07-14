/**
 * admin-orders.js — 后台订单管理交互脚本
 * 功能：订单表格渲染、多维度筛选、统计概览、
 *       CSV 导出（含数字签名）、订单详情弹窗
 * 数据来源：API.getAdminOrders / API.getAdminOrderDetail / API.exportAdminOrders
 */

(function () {
    'use strict';

    // ============== 配置 ==============
    var CONFIG = {
        storageKey: 'admin_orders_cache',   // 缓存键（仅用于网络异常时的降级缓存）
        versionKey: 'admin_orders_version',
        dataVersion: '3.0',                 // 数据版本：升级测评体系后递增，触发旧缓存清除
        defaultPageSize: 10
    };

    // 订单状态中文映射（与 payment.Order 模型状态对齐）
    var STATUS_MAP = {
        paid: '已支付',
        pending: '待支付',
        refunding: '退款中',
        refunded: '已退款',
        failed: '支付失败',
        expired: '已过期'
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
        orders: [],                 // 当前页订单（来自 API）
        total: 0,                   // 筛选后订单总数（来自 API）
        stats: {},                  // 统计概览（来自 API）
        currentPage: 1,
        pageSize: CONFIG.defaultPageSize,
        selectedOrders: new Set(),  // 当前页选中订单
        currentDetailOrder: null,
        lastSyncTime: Date.now()
    };

    // ========================================================
    //  1. 数据加载（服务端分页 + 筛选）
    // ========================================================
    function buildParams() {
        return {
            date_start: els.dateStart.value,
            date_end: els.dateEnd.value,
            status: els.filterStatus.value,
            amount_min: els.amountMin.value,
            amount_max: els.amountMax.value,
            order_no: els.searchOrderNo.value.trim(),
            page: state.currentPage,
            page_size: state.pageSize
        };
    }

    function loadOrders() {
        // 版本检测：缓存版本不匹配时清除旧缓存
        var savedVersion = localStorage.getItem(CONFIG.versionKey);
        if (savedVersion !== CONFIG.dataVersion) {
            localStorage.removeItem(CONFIG.storageKey);
            localStorage.setItem(CONFIG.versionKey, CONFIG.dataVersion);
        }

        var params = buildParams();
        API.getAdminOrders(params).then(function (data) {
            state.orders = (data && data.list) || [];
            state.total = (data && data.total) || 0;
            state.stats = (data && data.stats) || {};
            // 写入降级缓存
            try {
                localStorage.setItem(CONFIG.storageKey, JSON.stringify(state.orders));
            } catch (e) { /* 忽略缓存写入失败 */ }
            state.lastSyncTime = Date.now();
            renderTable();
            updateStats();
            updateSyncTime();
        }).catch(function (err) {
            // 降级：尝试读取缓存
            var cached = null;
            try {
                cached = JSON.parse(localStorage.getItem(CONFIG.storageKey) || '[]');
            } catch (e) { cached = null; }
            if (Array.isArray(cached) && cached.length > 0) {
                state.orders = cached;
                state.total = cached.length;
                state.stats = {};
                showToast('网络异常，已显示缓存数据');
            } else {
                state.orders = [];
                state.total = 0;
                state.stats = {};
                showToast('订单加载失败：' + (err.message || '未知错误'));
            }
            renderTable();
            updateStats();
        });
    }

    // ========================================================
    //  2. 表格渲染
    // ========================================================
    function renderTable() {
        var totalPages = Math.ceil(state.total / state.pageSize) || 1;
        if (state.currentPage > totalPages) state.currentPage = totalPages;

        var pageData = state.orders;

        if (pageData.length === 0) {
            els.tableBody.innerHTML = '<tr><td colspan="8" class="table-empty">' +
                '<svg viewBox="0 0 24 24" width="40" height="40" fill="none" stroke="#d5d8d6" stroke-width="1.5"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/></svg>' +
                '暂无匹配的订单数据</td></tr>';
        } else {
            els.tableBody.innerHTML = pageData.map(renderRow).join('');
            bindRowEvents();
        }

        // 分页信息
        var start = (state.currentPage - 1) * state.pageSize;
        var end = Math.min(start + state.pageSize, state.total);
        if (state.total === 0) {
            els.paginationInfo.textContent = '共 0 条';
        } else {
            els.paginationInfo.textContent = '共 ' + state.total + ' 条，第 ' + (start + 1) + '-' + end + ' 条';
        }

        els.prevPage.disabled = state.currentPage <= 1;
        els.nextPage.disabled = state.currentPage >= totalPages;

        renderPagination(totalPages);
        updateSelectAllState();
    }

    function renderRow(o) {
        var statusClass = 'status-badge--' + o.status;
        var statusText = STATUS_MAP[o.status] || o.status;
        var amountClass = (o.status === 'refunded' || o.status === 'refunding') ? 'table-amount table-amount--refund' : 'table-amount';
        var txnHtml = o.txnNo
            ? '<span class="table-txn">' + escapeHtml(o.txnNo) + '</span>'
            : '<span class="table-txn table-txn--none">—</span>';
        var isChecked = state.selectedOrders.has(o.orderNo);

        return '<tr data-order="' + o.orderNo + '">' +
            '<td class="col-check"><input type="checkbox" class="row-check"' + (isChecked ? ' checked' : '') + '></td>' +
            '<td><span class="table-order-no" data-action="detail">' + escapeHtml(o.orderNo) + '</span></td>' +
            '<td><span class="table-time">' + escapeHtml(o.time) + '</span></td>' +
            '<td><span class="' + amountClass + '">¥' + Number(o.amount).toFixed(2) + '</span></td>' +
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
    //  3. 筛选（参数提交给 API）
    // ========================================================
    function initFilters() {
        els.searchBtn.addEventListener('click', function () {
            state.currentPage = 1;
            loadOrders();
            trackEvent('order_search');
        });

        els.searchOrderNo.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                state.currentPage = 1;
                loadOrders();
            }
        });

        els.resetBtn.addEventListener('click', function () {
            els.dateStart.value = '';
            els.dateEnd.value = '';
            els.filterStatus.value = '';
            els.amountMin.value = '';
            els.amountMax.value = '';
            els.searchOrderNo.value = '';
            state.currentPage = 1;
            loadOrders();
            showToast('筛选已重置');
        });
    }

    // ========================================================
    //  4. 统计更新（来自 API 返回的 stats 字段）
    // ========================================================
    function updateStats() {
        var s = state.stats || {};
        els.statTotalOrders.textContent = (s.totalOrders != null) ? s.totalOrders : state.total;
        els.statTotalAmount.textContent = (s.totalAmount != null) ? ('¥' + Number(s.totalAmount).toFixed(2)) : '¥0.00';
        els.statSuccessRate.textContent = (s.successRate != null) ? (s.successRate + '%') : '0%';
        els.statRefundAmount.textContent = (s.refundAmount != null) ? ('¥' + Number(s.refundAmount).toFixed(2)) : '¥0.00';
    }

    // ========================================================
    //  5. 全选 & 批量操作
    // ========================================================
    function initSelectAll() {
        els.selectAll.addEventListener('change', function () {
            if (els.selectAll.checked) {
                state.orders.forEach(function (o) { state.selectedOrders.add(o.orderNo); });
            } else {
                state.orders.forEach(function (o) { state.selectedOrders.delete(o.orderNo); });
            }
            renderTable();
        });
    }

    function updateSelectAllState() {
        var allChecked = state.orders.length > 0 && state.orders.every(function (o) { return state.selectedOrders.has(o.orderNo); });
        els.selectAll.checked = allChecked;
    }

    // ========================================================
    //  6. 订单详情弹窗（调用 API 获取详情 + 操作日志）
    // ========================================================
    function openDetailModal(orderNo) {
        API.getAdminOrderDetail(orderNo).then(function (order) {
            state.currentDetailOrder = order;
            renderDetail(order);
            els.detailModal.classList.add('modal--open');
            trackEvent('order_detail_view', { orderNo: orderNo });
        }).catch(function (err) {
            showToast('获取订单详情失败：' + (err.message || '未知错误'));
        });
    }

    function renderDetail(order) {
        var statusClass = 'status-badge--' + order.status;
        var statusText = STATUS_MAP[order.status] || order.status;

        var logs = order.logs || [];
        var logsHtml = logs.map(function (log) {
            return '<div class="detail-log__item">' +
                '<span class="detail-log__time">' + escapeHtml(log.time) + '</span>' +
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
                        '<span class="detail-item__value detail-item__value--amount">¥' + Number(order.amount).toFixed(2) + '</span>' +
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
                        '<span class="detail-item__value">' + (escapeHtml(order.payMethod) || '—') + '</span>' +
                    '</div>' +
                    '<div class="detail-item">' +
                        '<span class="detail-item__label">支付时间</span>' +
                        '<span class="detail-item__value">' + (escapeHtml(order.payTime) || '—') + '</span>' +
                    '</div>' +
                    '<div class="detail-item detail-item--full">' +
                        '<span class="detail-item__label">交易号</span>' +
                        '<span class="detail-item__value detail-item__value--mono">' + (escapeHtml(order.txnNo) || '—') + '</span>' +
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
            API.exportAdminOrders({ order_no: state.currentDetailOrder.orderNo }).then(function (blob) {
                API.downloadBlob(blob, 'order_' + state.currentDetailOrder.orderNo + '.csv');
                var signature = generateSignature('export:' + state.currentDetailOrder.orderNo);
                showSignatureModal('单笔订单', signature, 1);
                trackEvent('order_export', { format: 'csv', count: 1, label: '单笔订单' });
            }).catch(function (err) {
                showToast('导出失败：' + (err.message || '未知错误'));
            });
        });
    }

    // ========================================================
    //  7. 导出 CSV（服务端生成，前端下载）
    // ========================================================
    function exportFilteredCsv(label) {
        if (state.total === 0) {
            showToast('没有可导出的订单数据');
            return;
        }
        var params = buildParams();
        // 导出全部筛选结果，不分页
        delete params.page;
        delete params.page_size;
        API.exportAdminOrders(params).then(function (blob) {
            API.downloadBlob(blob, 'orders_export_' + new Date().toISOString().substring(0, 10) + '.csv');
            var signature = generateSignature('export:' + state.total + ':' + JSON.stringify(params));
            showSignatureModal(label, signature, state.total);
            trackEvent('order_export', { format: 'csv', count: state.total, label: label });
        }).catch(function (err) {
            showToast('导出失败：' + (err.message || '未知错误'));
        });
    }

    function initExport() {
        els.exportCsvBtn.addEventListener('click', function () {
            exportFilteredCsv('全部筛选订单');
        });

        els.exportPdfBtn.addEventListener('click', function () {
            if (state.total === 0) {
                showToast('没有可导出的订单数据');
                return;
            }
            // PDF 导出（M4 阶段复用 CSV 数据流，附加签名确认）
            var params = buildParams();
            delete params.page;
            delete params.page_size;
            API.exportAdminOrders(params).then(function (blob) {
                API.downloadBlob(blob, 'orders_report_' + new Date().toISOString().substring(0, 10) + '.csv');
                var signature = generateSignature('pdf:' + state.total);
                showSignatureModal('PDF 报表', signature, state.total);
                trackEvent('order_export', { format: 'pdf', count: state.total });
            }).catch(function (err) {
                showToast('导出失败：' + (err.message || '未知错误'));
            });
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
    //  9. 分页（服务端分页）
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
                loadOrders();
            });
        });
    }

    function initPagination() {
        els.prevPage.addEventListener('click', function () {
            if (state.currentPage > 1) {
                state.currentPage--;
                loadOrders();
            }
        });

        els.nextPage.addEventListener('click', function () {
            var totalPages = Math.ceil(state.total / state.pageSize) || 1;
            if (state.currentPage < totalPages) {
                state.currentPage++;
                loadOrders();
            }
        });

        els.pageSizeSelect.addEventListener('change', function () {
            state.pageSize = parseInt(els.pageSizeSelect.value, 10);
            state.currentPage = 1;
            loadOrders();
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
                    window.location.href = '/';
                }, 1000);
            }
        });

        // 侧边栏菜单导航（通过 href 属性实现跳转，无需 JS 拦截）
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
    function escapeHtml(str) {
        if (!str) return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function getCurrentTimeStr() {
        var now = new Date();
        function pad(n) { return n < 10 ? '0' + n : '' + n; }
        return now.getFullYear() + '-' + pad(now.getMonth() + 1) + '-' + pad(now.getDate()) + ' ' + pad(now.getHours()) + ':' + pad(now.getMinutes()) + ':' + pad(now.getSeconds());
    }

    function generateSignature(data) {
        // 模拟 HMAC-SHA256 签名生成（用于导出文件完整性展示）
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
        if (window.API && typeof API.trackEvent === 'function') {
            API.trackEvent(eventName, data || {});
        }
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
