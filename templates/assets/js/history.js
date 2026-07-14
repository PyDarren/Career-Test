/**
 * history.js — 测评历史页交互脚本
 * 功能：记录渲染、查看报告、编辑模式、批量删除、二次确认弹窗、
 *       空状态切换、变化趋势计算、localStorage 持久化
 */

(function () {
    'use strict';

    // ============== 配置 ==============
    var CONFIG = {
        maxRecords: 3,
        storageKey: 'career_test_history_cache',
        versionKey: 'career_test_history_version',
        dataVersion: '3.0',  // 数据版本：升级测评体系后递增，触发缓存清除
        badgeColors: {
            // RIASEC 首字母 → 徽标颜色
            'R': 'gold', 'I': 'blue', 'A': 'purple',
            'S': 'green', 'E': 'gold', 'C': 'green'
        }
    };

    // ============== DOM 元素引用 ==============
    var els = {
        backBtn:        document.getElementById('backBtn'),
        manageBtn:      document.getElementById('manageBtn'),
        historyList:    document.getElementById('historyList'),
        historyEmpty:   document.getElementById('historyEmpty'),
        historySummary: document.getElementById('historySummary'),
        historyHint:    document.getElementById('historyHint'),
        recordCount:    document.getElementById('recordCount'),
        trendText:      document.getElementById('trendText'),
        trendInfo:      document.getElementById('trendInfo'),
        actionbar:      document.getElementById('historyActionbar'),
        selectAll:      document.getElementById('selectAllCheckbox'),
        batchDelete:    document.getElementById('batchDeleteBtn'),
        selectedCount:  document.getElementById('selectedCount'),
        confirmModal:   document.getElementById('confirmModal'),
        confirmOverlay: document.getElementById('confirmOverlay'),
        confirmTitle:   document.getElementById('confirmTitle'),
        confirmDesc:    document.getElementById('confirmDesc'),
        confirmCancel:  document.getElementById('confirmCancel'),
        confirmOk:      document.getElementById('confirmOk'),
        toast:          document.getElementById('historyToast')
    };

    // ============== 内部状态 ==============
    var state = {
        records: [],
        editMode: false,
        selectedIds: new Set(),
        pendingDelete: null  // 'single' | 'batch'
    };

    // ========================================================
    //  1. 数据加载（从后端 API 获取，localStorage 用于缓存）
    // ========================================================
    function loadRecords() {
        // 版本检测：数据版本不匹配时清除缓存
        var savedVersion = localStorage.getItem(CONFIG.versionKey);
        if (savedVersion !== CONFIG.dataVersion) {
            localStorage.removeItem(CONFIG.storageKey);
            localStorage.setItem(CONFIG.versionKey, CONFIG.dataVersion);
        }

        // 先尝试从缓存加载（快速渲染）
        var cached = localStorage.getItem(CONFIG.storageKey);
        if (cached) {
            try {
                var parsed = JSON.parse(cached);
                if (Array.isArray(parsed)) {
                    state.records = parsed;
                    renderRecords();
                }
            } catch (e) {
                // ignore
            }
        }

        // 从后端 API 获取最新数据
        if (typeof API === 'undefined' || !API.getAssessmentHistory) {
            return;
        }

        API.getAssessmentHistory().then(function (res) {
            var records = (res && res.list) || [];
            state.records = records;
            saveRecords();
            renderRecords();
        }).catch(function () {
            // API 失败时使用缓存数据（已在上面的缓存逻辑中处理）
            if (state.records.length === 0) {
                renderRecords();
            }
        });
    }

    function saveRecords() {
        // 用于缓存
        try {
            localStorage.setItem(CONFIG.storageKey, JSON.stringify(state.records));
        } catch (e) {
            // ignore
        }
    }

    // ========================================================
    //  2. 渲染记录列表
    // ========================================================
    function renderRecords() {
        if (state.records.length === 0) {
            els.historyList.style.display = 'none';
            els.historyEmpty.style.display = 'flex';
            els.historySummary.style.display = 'none';
            els.historyHint.style.display = 'none';
            return;
        }

        els.historyList.style.display = 'flex';
        els.historyEmpty.style.display = 'none';
        els.historySummary.style.display = 'flex';
        els.historyHint.style.display = 'flex';

        // 更新汇总
        els.recordCount.textContent = state.records.length;
        updateTrend();

        // 按时间倒序排列
        var sorted = state.records.slice().sort(function (a, b) {
            return new Date(b.date) - new Date(a.date);
        });

        // 渲染卡片
        var html = sorted.map(function (record, index) {
            return renderCard(record, index === 0);
        }).join('');

        els.historyList.innerHTML = html;

        // 绑定卡片事件
        bindCardEvents();
    }

    function renderCard(record, isLatest) {
        var badgeColor = CONFIG.badgeColors[record.baseCode.charAt(0)] || 'purple';
        var paidTag = record.isPaid
            ? '<span class="record-tag record-tag--paid"><span class="record-tag__dot"></span>付费报告</span>'
            : '<span class="record-tag record-tag--free"><span class="record-tag__dot"></span>免费报告</span>';

        var latestBadge = isLatest ? '<span class="record-card__latest">最新</span>' : '';

        var isSelected = state.selectedIds.has(record.id);
        var selectedClass = isSelected ? ' record-card--selected' : '';
        var editClass = state.editMode ? ' record-card--edit' : '';
        var checkedClass = isSelected ? ' record-card__checkbox--checked' : '';

        return '' +
            '<div class="record-card' + editClass + selectedClass + '" data-id="' + record.id + '">' +
                latestBadge +
                // 编辑模式下的 checkbox
                '<div class="record-card__checkbox' + checkedClass + '" data-action="toggle">' +
                    '<svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="#fff" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>' +
                '</div>' +
                // 类型徽标
                '<div class="record-card__badge record-card__badge--' + badgeColor + '">' +
                    record.baseCode +
                '</div>' +
                // 信息区
                '<div class="record-card__body">' +
                    '<div class="record-card__header">' +
                        '<span class="record-card__code">' + record.code + '</span>' +
                        '<span class="record-card__name">' + record.typeName + '</span>' +
                    '</div>' +
                    '<div class="record-card__meta">' +
                        '<span class="record-card__date">' + record.dateLabel + '</span>' +
                        paidTag +
                    '</div>' +
                '</div>' +
                // 查看按钮（非编辑模式）
                '<button class="record-card__view" data-action="view">' +
                    '<span>查看</span>' +
                    '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>' +
                '</button>' +
            '</div>';
    }

    // ========================================================
    //  3. 变化趋势计算
    // ========================================================
    function updateTrend() {
        if (state.records.length < 2) {
            els.trendText.textContent = state.records.length === 1 ? '首次测评' : '暂无变化趋势';
            return;
        }

        var sorted = state.records.slice().sort(function (a, b) {
            return new Date(b.date) - new Date(a.date);
        });

        var latest = sorted[0];
        var previous = sorted[1];

        if (latest.baseCode === previous.baseCode) {
            els.trendText.textContent = '画像稳定 · ' + latest.typeName;
            els.trendInfo.style.color = '#5ea67e';
            els.trendInfo.style.background = 'rgba(94, 166, 126, 0.08)';
        } else {
            els.trendText.textContent = previous.baseCode + ' → ' + latest.baseCode;
            els.trendInfo.style.color = '#deb45c';
            els.trendInfo.style.background = 'rgba(222, 180, 92, 0.08)';
        }
    }

    // ========================================================
    //  4. 卡片事件绑定
    // ========================================================
    function bindCardEvents() {
        var cards = els.historyList.querySelectorAll('.record-card');

        cards.forEach(function (card) {
            var id = card.getAttribute('data-id');

            card.addEventListener('click', function (e) {
                var actionEl = e.target.closest('[data-action]');
                var action = actionEl ? actionEl.getAttribute('data-action') : null;

                if (state.editMode) {
                    // 编辑模式：点击卡片切换选中
                    toggleSelection(id);
                } else if (action === 'view' || !action) {
                    // 非编辑模式：查看报告
                    viewReport(id);
                }
            });
        });
    }

    // ========================================================
    //  5. 查看报告
    // ========================================================
    function viewReport(id) {
        var record = findRecord(id);
        if (!record) return;

        trackEvent('history_view_click', {
            id: id,
            code: record.code,
            isPaid: record.isPaid
        });

        // 根据付费状态跳转，并带 assessment_id 参数
        var assessmentId = record.assessment_id || record.session_token || record.id || '';
        if (record.isPaid) {
            var url = record.reportUrl || '/deep-report/';
            if (assessmentId) {
                url += '?assessment_id=' + encodeURIComponent(assessmentId);
            }
            window.location.href = url;
        } else {
            // 未付费，跳转到支付页
            var payUrl = '/payment/';
            if (assessmentId) {
                payUrl += '?assessment_id=' + encodeURIComponent(assessmentId);
            }
            window.location.href = payUrl;
        }
    }

    // ========================================================
    //  6. 编辑模式开关
    // ========================================================
    function toggleEditMode() {
        state.editMode = !state.editMode;

        if (!state.editMode) {
            // 退出编辑模式时清空选中
            state.selectedIds.clear();
        }

        // 更新管理按钮文字
        if (state.editMode) {
            els.manageBtn.textContent = '完成';
            els.manageBtn.classList.add('edit-mode');
            els.actionbar.classList.add('history-actionbar--visible');
        } else {
            els.manageBtn.textContent = '管理';
            els.manageBtn.classList.remove('edit-mode');
            els.actionbar.classList.remove('history-actionbar--visible');
            els.selectAll.checked = false;
        }

        renderRecords();
        updateBatchUI();
    }

    // ========================================================
    //  7. 选中/取消选中
    // ========================================================
    function toggleSelection(id) {
        if (state.selectedIds.has(id)) {
            state.selectedIds.delete(id);
        } else {
            state.selectedIds.add(id);
        }
        renderRecords();
        updateBatchUI();
    }

    function updateBatchUI() {
        var count = state.selectedIds.size;
        els.selectedCount.textContent = count;
        els.batchDelete.disabled = count === 0;

        // 更新全选状态
        var total = state.records.length;
        els.selectAll.checked = (count === total && total > 0);
    }

    // ========================================================
    //  8. 全选/取消全选
    // ========================================================
    function initSelectAll() {
        els.selectAll.addEventListener('change', function () {
            if (els.selectAll.checked) {
                state.records.forEach(function (r) {
                    state.selectedIds.add(r.id);
                });
            } else {
                state.selectedIds.clear();
            }
            renderRecords();
            updateBatchUI();
        });
    }

    // ========================================================
    //  9. 删除操作（单条 + 批量）
    // ========================================================
    function initDelete() {
        // 批量删除按钮
        els.batchDelete.addEventListener('click', function () {
            if (state.selectedIds.size === 0) return;
            state.pendingDelete = 'batch';
            var count = state.selectedIds.size;
            els.confirmTitle.textContent = '确认删除 ' + count + ' 条记录？';
            els.confirmDesc.textContent = '删除后无法恢复，免费报告也将一并移除';
            openConfirm();
        });

        // 确认删除
        els.confirmOk.addEventListener('click', function () {
            if (state.pendingDelete === 'batch') {
                executeBatchDelete();
            }
            closeConfirm();
        });

        // 取消
        els.confirmCancel.addEventListener('click', closeConfirm);
        els.confirmOverlay.addEventListener('click', closeConfirm);

        // ESC 关闭
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                if (els.confirmModal.classList.contains('confirm-modal--open')) {
                    closeConfirm();
                } else if (state.editMode) {
                    toggleEditMode();
                }
            }
        });
    }

    function executeBatchDelete() {
        var idsToDelete = Array.from(state.selectedIds);
        var count = idsToDelete.length;

        // 添加删除动画
        idsToDelete.forEach(function (id) {
            var card = els.historyList.querySelector('.record-card[data-id="' + id + '"]');
            if (card) {
                card.classList.add('record-card--removing');
            }
        });

        // 调用 API 删除（如果后端已实现）
        var deletePromises = idsToDelete.map(function (id) {
            if (typeof API !== 'undefined' && API.deleteAssessment) {
                return API.deleteAssessment(id).catch(function () {
                    // API 失败时静默处理，后续本地删除
                });
            }
            return Promise.resolve();
        });

        Promise.all(deletePromises).then(function () {
            // 动画结束后移除数据
            setTimeout(function () {
                state.records = state.records.filter(function (r) {
                    return !state.selectedIds.has(r.id);
                });
                state.selectedIds.clear();
                saveRecords();
                renderRecords();
                updateBatchUI();

                // 如果删除后没有记录，退出编辑模式
                if (state.records.length === 0) {
                    toggleEditMode();
                }

                showToast('已删除 ' + count + ' 条记录');
                trackEvent('history_delete', { count: count });
            }, 300);
        });
    }

    // ========================================================
    // 10. 确认弹窗开关
    // ========================================================
    function openConfirm() {
        els.confirmModal.classList.add('confirm-modal--open');
        document.body.style.overflow = 'hidden';
    }

    function closeConfirm() {
        els.confirmModal.classList.remove('confirm-modal--open');
        document.body.style.overflow = '';
        state.pendingDelete = null;
    }

    // ========================================================
    // 11. 返回按钮
    // ========================================================
    function initBackBtn() {
        els.backBtn.addEventListener('click', function () {
            if (window.history.length > 1) {
                window.history.back();
            } else {
                window.location.href = '/';
            }
        });
    }

    // ========================================================
    // 12. 管理按钮
    // ========================================================
    function initManageBtn() {
        els.manageBtn.addEventListener('click', function () {
            if (state.records.length === 0) return;
            toggleEditMode();
        });
    }

    // ========================================================
    // 工具函数
    // ========================================================
    function findRecord(id) {
        return state.records.find(function (r) {
            return r.id === id;
        });
    }

    function trackEvent(eventName, data) {
        if (typeof API !== 'undefined' && API.trackEvent) {
            API.trackEvent(eventName, data || {}, 'history');
        }
    }

    var toastTimer = null;
    function showToast(message) {
        if (toastTimer) {
            clearTimeout(toastTimer);
        }

        els.toast.textContent = message;
        els.toast.classList.add('history-toast--visible');

        toastTimer = setTimeout(function () {
            els.toast.classList.remove('history-toast--visible');
        }, 2500);
    }

    // ========================================================
    // 初始化
    // ========================================================
    function init() {
        loadRecords();
        initBackBtn();
        initManageBtn();
        initSelectAll();
        initDelete();

        // 页面加载埋点
        trackEvent('history_page_view', {
            recordCount: state.records.length
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
