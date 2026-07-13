/**
 * admin-questions.js — 后台题库管理交互脚本
 * 功能：表格渲染、搜索筛选、新增/编辑/删除、批量操作、
 *       Excel 导入导出、版本控制、灰度发布配置
 */

(function () {
    'use strict';

    // ============== 配置 ==============
    var CONFIG = {
        storageKey: 'admin_questions',
        versionKey: 'admin_questions_version',   // 版本检测：数据版本不匹配时清除旧数据
        dataVersion: '2.0',
        versionsKey: 'admin_question_versions',  // 版本历史记录存储
        grayscaleKey: 'admin_grayscale_config',
        pageSize: 10
    };

    // ============== 模拟题目数据 ==============
    var MOCK_QUESTIONS = [
        { id: 'Q001', question: '我喜欢思考新的想法和可能性。', optionA: '非常不符合', optionB: '非常符合', weight: 3, category: 'BO', status: 'published', logs: [{ time: '2026-07-10 14:30', author: '陈管理', action: '创建题目' }] },
        { id: 'Q002', question: '我会提前制定计划并按计划执行。', optionA: '非常不符合', optionB: '非常符合', weight: 3, category: 'BC', status: 'published', logs: [{ time: '2026-07-10 14:35', author: '陈管理', action: '创建题目' }] },
        { id: 'Q003', question: '在社交场合中我通常是主动交谈的人。', optionA: '非常不符合', optionB: '非常符合', weight: 2, category: 'BE', status: 'published', logs: [{ time: '2026-07-10 14:40', author: '陈管理', action: '创建题目' }] },
        { id: 'Q004', question: '即使意见不同，我也能理解对方的立场。', optionA: '非常不符合', optionB: '非常符合', weight: 3, category: 'BA', status: 'published', logs: [{ time: '2026-07-10 14:42', author: '陈管理', action: '创建题目' }] },
        { id: 'Q005', question: '我经常感到焦虑或不安。', optionA: '非常不符合', optionB: '非常符合', weight: 3, category: 'BN', status: 'published', logs: [{ time: '2026-07-10 14:45', author: '陈管理', action: '创建题目' }] },
        { id: 'Q006', question: '我更倾向于按部就班而非尝试新方法。', optionA: '非常不符合', optionB: '非常符合', weight: 2, category: 'BO', status: 'draft', logs: [{ time: '2026-07-10 14:48', author: '陈管理', action: '创建题目' }] },
        { id: 'Q007', question: '我经常在最后一刻才完成任务。', optionA: '非常不符合', optionB: '非常符合', weight: 2, category: 'BC', status: 'draft', logs: [{ time: '2026-07-11 09:00', author: '陈管理', action: '创建题目' }] },
        { id: 'Q008', question: '我比群体活动更喜欢独处的爱好。', optionA: '非常不符合', optionB: '非常符合', weight: 2, category: 'BE', status: 'published', logs: [{ time: '2026-07-11 09:15', author: '陈管理', action: '创建题目' }] },
        { id: 'Q009', question: '我喜欢动手修理或组装物品。', optionA: '非常不符合', optionB: '非常符合', weight: 3, category: 'RR', status: 'published', logs: [{ time: '2026-07-11 09:20', author: '陈管理', action: '创建题目' }] },
        { id: 'Q010', question: '我喜欢分析复杂数据寻找规律。', optionA: '非常不符合', optionB: '非常符合', weight: 3, category: 'RI', status: 'published', logs: [{ time: '2026-07-11 09:25', author: '陈管理', action: '创建题目' }] },
        { id: 'Q011', question: '我喜欢通过创意作品表达自我。', optionA: '非常不符合', optionB: '非常符合', weight: 3, category: 'RA', status: 'draft', logs: [{ time: '2026-07-11 09:30', author: '陈管理', action: '创建题目' }] },
        { id: 'Q012', question: '帮助他人成长让我感到充实。', optionA: '非常不符合', optionB: '非常符合', weight: 3, category: 'RS', status: 'published', logs: [{ time: '2026-07-11 10:00', author: '陈管理', action: '创建题目' }] }
    ];

    var MOCK_VERSIONS = [
        { version: 'v2.3', desc: '新增 3 道宜人性(BA)维度灰度题目，优化外向性(BE)维度权重分配', author: '陈管理', time: '2026-07-11 10:30', isCurrent: true },
        { version: 'v2.2', desc: '修正 Q005 题干表述歧义，调整 Q007 权重至 4', author: '陈管理', time: '2026-07-05 16:20', isCurrent: false },
        { version: 'v2.1', desc: '批量导入 15 道尽责性(BC)维度新题目，替换旧版题库', author: '编辑员A', time: '2026-06-28 14:00', isCurrent: false },
        { version: 'v2.0', desc: '题库架构升级至 5 点李克特量表架构', author: '陈管理', time: '2026-06-15 09:00', isCurrent: false }
    ];

    // ============== DOM 引用 ==============
    var els = {
        logoutBtn: document.getElementById('logoutBtn'),
        searchInput: document.getElementById('searchInput'),
        filterCategory: document.getElementById('filterCategory'),
        filterStatus: document.getElementById('filterStatus'),
        importBtn: document.getElementById('importBtn'),
        exportBtn: document.getElementById('exportBtn'),
        batchDeleteBtn: document.getElementById('batchDeleteBtn'),
        addQuestionBtn: document.getElementById('addQuestionBtn'),
        selectAll: document.getElementById('selectAll'),
        tableBody: document.getElementById('tableBody'),
        paginationInfo: document.getElementById('paginationInfo'),
        prevPage: document.getElementById('prevPage'),
        nextPage: document.getElementById('nextPage'),
        versionTimeline: document.getElementById('versionTimeline'),
        createVersionBtn: document.getElementById('createVersionBtn'),
        grayscaleSlider: document.getElementById('grayscaleSlider'),
        grayscaleValue: document.getElementById('grayscaleValue'),
        saveGrayscaleBtn: document.getElementById('saveGrayscaleBtn'),
        statTotal: document.getElementById('statTotal'),
        statActive: document.getElementById('statActive'),
        statGrayscale: document.getElementById('statGrayscale'),
        // 抽屉
        editDrawer: document.getElementById('editDrawer'),
        drawerOverlay: document.getElementById('drawerOverlay'),
        drawerTitle: document.getElementById('drawerTitle'),
        drawerClose: document.getElementById('drawerClose'),
        drawerCancel: document.getElementById('drawerCancel'),
        drawerSave: document.getElementById('drawerSave'),
        editId: document.getElementById('editId'),
        editQuestion: document.getElementById('editQuestion'),
        editOptionA: document.getElementById('editOptionA'),
        editOptionB: document.getElementById('editOptionB'),
        editWeight: document.getElementById('editWeight'),
        editCategory: document.getElementById('editCategory'),
        editLogSection: document.getElementById('editLogSection'),
        editLog: document.getElementById('editLog'),
        // 导入弹窗
        importModal: document.getElementById('importModal'),
        importOverlay: document.getElementById('importOverlay'),
        importZone: document.getElementById('importZone'),
        importFile: document.getElementById('importFile'),
        importCancel: document.getElementById('importCancel'),
        importConfirm: document.getElementById('importConfirm'),
        downloadTemplate: document.getElementById('downloadTemplate'),
        // 删除弹窗
        deleteModal: document.getElementById('deleteModal'),
        deleteOverlay: document.getElementById('deleteOverlay'),
        deleteTitle: document.getElementById('deleteTitle'),
        deleteDesc: document.getElementById('deleteDesc'),
        deleteCancel: document.getElementById('deleteCancel'),
        deleteConfirm: document.getElementById('deleteConfirm'),
        // Toast
        toast: document.getElementById('adminToast')
    };

    // ============== 状态 ==============
    var state = {
        questions: [],
        versions: [],
        currentPage: 1,
        selectedIds: new Set(),
        editingId: null,
        pendingDeleteIds: null,
        importFile: null
    };

    // ========================================================
    //  1. 数据加载
    // ========================================================
    function loadQuestions() {
        // 版本检测：数据版本不匹配时清除旧数据
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
                    state.questions = parsed;
                    return;
                }
            } catch (e) {}
        }
        state.questions = MOCK_QUESTIONS.slice();
        saveQuestions();
    }

    function saveQuestions() {
        localStorage.setItem(CONFIG.storageKey, JSON.stringify(state.questions));
    }

    function loadVersions() {
        var saved = localStorage.getItem(CONFIG.versionsKey);
        if (saved) {
            try {
                state.versions = JSON.parse(saved);
                return;
            } catch (e) {}
        }
        state.versions = MOCK_VERSIONS.slice();
        saveVersions();
    }

    function saveVersions() {
        localStorage.setItem(CONFIG.versionsKey, JSON.stringify(state.versions));
    }

    // ========================================================
    //  2. 表格渲染
    // ========================================================
    function renderTable() {
        var filtered = getFilteredQuestions();
        var totalPages = Math.ceil(filtered.length / CONFIG.pageSize) || 1;
        if (state.currentPage > totalPages) state.currentPage = totalPages;

        var start = (state.currentPage - 1) * CONFIG.pageSize;
        var pageData = filtered.slice(start, start + CONFIG.pageSize);

        if (pageData.length === 0) {
            els.tableBody.innerHTML = '<tr><td colspan="9" style="text-align:center;padding:40px;color:#9B9BAB;">暂无匹配的题目</td></tr>';
        } else {
            els.tableBody.innerHTML = pageData.map(renderRow).join('');
            bindRowEvents();
        }

        // 分页信息
        var end = Math.min(start + CONFIG.pageSize, filtered.length);
        els.paginationInfo.textContent = '共 ' + filtered.length + ' 条，第 ' + (start + 1) + '-' + end + ' 条';
        els.prevPage.disabled = state.currentPage <= 1;
        els.nextPage.disabled = state.currentPage >= totalPages;

        // 更新统计
        updateStats();

        // 更新批量删除按钮
        updateBatchDeleteBtn();
    }

    function renderRow(q) {
        var weightClass = q.weight <= 2 ? 'low' : q.weight <= 3 ? 'mid' : q.weight === 4 ? 'high' : 'key';
        var statusClass = 'status-dot--' + q.status;
        var statusText = { published: '已发布', draft: '草稿', active: '启用', inactive: '禁用', grayscale: '灰度中' }[q.status];
        var isChecked = state.selectedIds.has(q.id);

        return '<tr data-id="' + q.id + '">' +
            '<td class="col-check"><input type="checkbox" class="row-check"' + (isChecked ? ' checked' : '') + '></td>' +
            '<td><span class="table-id">' + q.id + '</span></td>' +
            '<td><div class="table-question" title="' + escapeHtml(q.question) + '">' + escapeHtml(q.question) + '</div></td>' +
            '<td><span class="table-option">' + escapeHtml(q.optionA) + '</span></td>' +
            '<td><span class="table-option">' + escapeHtml(q.optionB) + '</span></td>' +
            '<td><span class="weight-badge weight-badge--' + weightClass + '">' + q.weight + '</span></td>' +
            '<td><span class="category-tag category-tag--' + q.category + '">' + q.category + '</span></td>' +
            '<td><span class="status-dot ' + statusClass + '">' + statusText + '</span></td>' +
            '<td><div class="table-actions">' +
                '<button class="table-action-btn" data-action="edit" title="编辑"><svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg></button>' +
                '<button class="table-action-btn table-action-btn--danger" data-action="delete" title="删除"><svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-2 14a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2L5 6"/></svg></button>' +
            '</div></td>' +
        '</tr>';
    }

    function bindRowEvents() {
        var rows = els.tableBody.querySelectorAll('tr[data-id]');
        rows.forEach(function (row) {
            var id = row.getAttribute('data-id');

            row.querySelectorAll('[data-action]').forEach(function (btn) {
                btn.addEventListener('click', function (e) {
                    e.stopPropagation();
                    var action = btn.getAttribute('data-action');
                    if (action === 'edit') openEditDrawer(id);
                    else if (action === 'delete') openDeleteModal([id]);
                });
            });

            var checkbox = row.querySelector('.row-check');
            if (checkbox) {
                checkbox.addEventListener('change', function () {
                    if (checkbox.checked) {
                        state.selectedIds.add(id);
                    } else {
                        state.selectedIds.delete(id);
                    }
                    updateBatchDeleteBtn();
                    updateSelectAllState();
                });
            }
        });
    }

    // ========================================================
    //  3. 搜索与筛选
    // ========================================================
    function getFilteredQuestions() {
        var search = els.searchInput.value.trim().toLowerCase();
        var category = els.filterCategory.value;
        var status = els.filterStatus.value;

        return state.questions.filter(function (q) {
            var matchSearch = !search || q.question.toLowerCase().indexOf(search) >= 0 || q.id.toLowerCase().indexOf(search) >= 0;
            var matchCategory = !category || q.category === category;
            var matchStatus = !status || q.status === status;
            return matchSearch && matchCategory && matchStatus;
        });
    }

    function initFilters() {
        var searchTimer = null;
        els.searchInput.addEventListener('input', function () {
            if (searchTimer) clearTimeout(searchTimer);
            searchTimer = setTimeout(function () {
                state.currentPage = 1;
                renderTable();
            }, 300);
        });

        els.filterCategory.addEventListener('change', function () {
            state.currentPage = 1;
            renderTable();
        });

        els.filterStatus.addEventListener('change', function () {
            state.currentPage = 1;
            renderTable();
        });
    }

    // ========================================================
    //  4. 统计更新
    // ========================================================
    function updateStats() {
        els.statTotal.textContent = state.questions.length;
        els.statActive.textContent = state.questions.filter(function (q) { return q.status === 'published' || q.status === 'active'; }).length;
        els.statGrayscale.textContent = state.questions.filter(function (q) { return q.status === 'draft' || q.status === 'grayscale'; }).length;
    }

    // ========================================================
    //  5. 全选 & 批量操作
    // ========================================================
    function initSelectAll() {
        els.selectAll.addEventListener('change', function () {
            var pageData = getFilteredQuestions().slice((state.currentPage - 1) * CONFIG.pageSize, state.currentPage * CONFIG.pageSize);
            if (els.selectAll.checked) {
                pageData.forEach(function (q) { state.selectedIds.add(q.id); });
            } else {
                pageData.forEach(function (q) { state.selectedIds.delete(q.id); });
            }
            renderTable();
        });
    }

    function updateSelectAllState() {
        var pageData = getFilteredQuestions().slice((state.currentPage - 1) * CONFIG.pageSize, state.currentPage * CONFIG.pageSize);
        var allChecked = pageData.length > 0 && pageData.every(function (q) { return state.selectedIds.has(q.id); });
        els.selectAll.checked = allChecked;
    }

    function updateBatchDeleteBtn() {
        els.batchDeleteBtn.disabled = state.selectedIds.size === 0;
    }

    function initBatchDelete() {
        els.batchDeleteBtn.addEventListener('click', function () {
            if (state.selectedIds.size === 0) return;
            openDeleteModal(Array.from(state.selectedIds));
        });
    }

    // ========================================================
    //  6. 新增/编辑抽屉
    // ========================================================
    function openEditDrawer(id) {
        state.editingId = id || null;

        if (id) {
            var q = findQuestion(id);
            if (!q) return;
            els.drawerTitle.textContent = '编辑题目';
            els.editId.value = q.id;
            els.editQuestion.value = q.question;
            els.editOptionA.value = q.optionA;
            els.editOptionB.value = q.optionB;
            els.editWeight.value = String(q.weight);
            els.editCategory.value = q.category;
            setRadioValue('editStatus', q.status);

            // 修改日志
            if (q.logs && q.logs.length > 0) {
                els.editLogSection.style.display = 'block';
                els.editLog.innerHTML = q.logs.map(function (log) {
                    return '<div class="edit-log__item"><span class="edit-log__time">' + log.time +
                        '</span><span class="edit-log__content"><strong>' + log.author + '</strong> ' + log.action + '</span></div>';
                }).join('');
            } else {
                els.editLogSection.style.display = 'none';
            }
        } else {
            els.drawerTitle.textContent = '新增题目';
            els.editId.value = '';
            els.editQuestion.value = '';
            els.editOptionA.value = '';
            els.editOptionB.value = '';
            els.editWeight.value = '3';
            els.editCategory.value = 'BO';
            setRadioValue('editStatus', 'published');
            els.editLogSection.style.display = 'none';
        }

        els.editDrawer.classList.add('drawer--open');
        document.body.style.overflow = 'hidden';
    }

    function closeDrawer() {
        els.editDrawer.classList.remove('drawer--open');
        document.body.style.overflow = '';
        state.editingId = null;
    }

    function initDrawer() {
        els.drawerClose.addEventListener('click', closeDrawer);
        els.drawerCancel.addEventListener('click', closeDrawer);
        els.drawerOverlay.addEventListener('click', closeDrawer);

        els.drawerSave.addEventListener('click', function () {
            var question = els.editQuestion.value.trim();
            var optionA = els.editOptionA.value.trim();
            var optionB = els.editOptionB.value.trim();

            if (!question) { showToast('请输入题干内容'); return; }
            if (!optionA) { showToast('请输入选项 A'); return; }
            if (!optionB) { showToast('请输入选项 B'); return; }

            var weight = parseInt(els.editWeight.value, 10);
            var category = els.editCategory.value;
            var status = getRadioValue('editStatus');
            var now = new Date();
            var timeStr = now.getFullYear() + '-' + pad(now.getMonth() + 1) + '-' + pad(now.getDate()) + ' ' + pad(now.getHours()) + ':' + pad(now.getMinutes());

            if (state.editingId) {
                // 编辑
                var q = findQuestion(state.editingId);
                if (q) {
                    q.question = question;
                    q.optionA = optionA;
                    q.optionB = optionB;
                    q.weight = weight;
                    q.category = category;
                    q.status = status;
                    if (!q.logs) q.logs = [];
                    q.logs.push({ time: timeStr, author: '陈管理', action: '编辑题目内容' });
                }
                showToast('题目已更新');
                trackEvent('question_edit', { id: state.editingId });
            } else {
                // 新增
                var newId = 'Q' + String(state.questions.length + 1).padStart(3, '0');
                state.questions.push({
                    id: newId,
                    question: question,
                    optionA: optionA,
                    optionB: optionB,
                    weight: weight,
                    category: category,
                    status: status,
                    logs: [{ time: timeStr, author: '陈管理', action: '创建题目' }]
                });
                showToast('题目已新增');
                trackEvent('question_create', { id: newId });
            }

            saveQuestions();
            renderTable();
            closeDrawer();
        });

        els.addQuestionBtn.addEventListener('click', function () {
            openEditDrawer(null);
        });
    }

    // ========================================================
    //  7. 删除
    // ========================================================
    function openDeleteModal(ids) {
        state.pendingDeleteIds = ids;
        if (ids.length === 1) {
            els.deleteTitle.textContent = '确认删除该题目？';
            els.deleteDesc.textContent = '删除后该题目将立即下线，此操作可在版本记录中回滚';
        } else {
            els.deleteTitle.textContent = '确认删除 ' + ids.length + ' 道题目？';
            els.deleteDesc.textContent = '删除后这些题目将立即下线，此操作可在版本记录中回滚';
        }
        els.deleteModal.classList.add('modal--open');
    }

    function initDelete() {
        els.deleteCancel.addEventListener('click', function () {
            els.deleteModal.classList.remove('modal--open');
        });
        els.deleteOverlay.addEventListener('click', function () {
            els.deleteModal.classList.remove('modal--open');
        });
        els.deleteConfirm.addEventListener('click', function () {
            if (!state.pendingDeleteIds) return;

            state.questions = state.questions.filter(function (q) {
                return state.pendingDeleteIds.indexOf(q.id) < 0;
            });

            state.pendingDeleteIds.forEach(function (id) {
                state.selectedIds.delete(id);
            });

            saveQuestions();
            renderTable();
            els.deleteModal.classList.remove('modal--open');

            showToast('已删除 ' + state.pendingDeleteIds.length + ' 道题目');
            trackEvent('question_delete', { count: state.pendingDeleteIds.length });

            state.pendingDeleteIds = null;
        });
    }

    // ========================================================
    //  8. 批量导入
    // ========================================================
    function initImport() {
        els.importBtn.addEventListener('click', function () {
            els.importFile.value = '';
            state.importFile = null;
            els.importConfirm.disabled = true;
            els.importModal.classList.add('modal--open');
        });

        els.importCancel.addEventListener('click', function () {
            els.importModal.classList.remove('modal--open');
        });
        els.importOverlay.addEventListener('click', function () {
            els.importModal.classList.remove('modal--open');
        });

        els.importZone.addEventListener('click', function () {
            els.importFile.click();
        });

        els.importZone.addEventListener('dragover', function (e) {
            e.preventDefault();
            els.importZone.classList.add('import-zone--dragover');
        });

        els.importZone.addEventListener('dragleave', function () {
            els.importZone.classList.remove('import-zone--dragover');
        });

        els.importZone.addEventListener('drop', function (e) {
            e.preventDefault();
            els.importZone.classList.remove('import-zone--dragover');
            if (e.dataTransfer.files.length > 0) {
                handleImportFile(e.dataTransfer.files[0]);
            }
        });

        els.importFile.addEventListener('change', function (e) {
            if (e.target.files.length > 0) {
                handleImportFile(e.target.files[0]);
            }
        });

        els.importConfirm.addEventListener('click', function () {
            if (!state.importFile) return;

            // 模拟导入 5 条新题目
            var baseLen = state.questions.length;
            for (var i = 1; i <= 5; i++) {
                var newId = 'Q' + String(baseLen + i).padStart(3, '0');
                state.questions.push({
                    id: newId,
                    question: '（导入）第 ' + i + ' 道题目示例内容',
                    optionA: '选项 A',
                    optionB: '选项 B',
                    weight: 3,
                    category: ['BO', 'BC', 'BE', 'BA', 'BN', 'RR', 'RI', 'RA', 'RS', 'RE', 'RC'][i % 11],
                    status: 'inactive',
                    logs: [{ time: getCurrentTimeStr(), author: '陈管理', action: '批量导入' }]
                });
            }

            saveQuestions();
            renderTable();
            els.importModal.classList.remove('modal--open');

            showToast('成功导入 5 道题目');
            trackEvent('question_import', { count: 5 });
        });

        // 下载模板
        els.downloadTemplate.addEventListener('click', function (e) {
            e.preventDefault();
            var csv = 'ID,题干,选项A,选项B,权重,分类,状态\nQ001,示例题干,非常不符合,非常符合,3,BO,published\n';
            var blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' });
            var url = URL.createObjectURL(blob);
            var a = document.createElement('a');
            a.href = url;
            a.download = 'question_import_template.csv';
            a.click();
            URL.revokeObjectURL(url);
            showToast('模板已下载');
        });
    }

    function handleImportFile(file) {
        var name = file.name;
        var ext = name.substring(name.lastIndexOf('.')).toLowerCase();
        if (ext !== '.xlsx' && ext !== '.csv') {
            showToast('仅支持 .xlsx / .csv 格式');
            return;
        }
        if (file.size > 5 * 1024 * 1024) {
            showToast('文件大小不能超过 5MB');
            return;
        }

        state.importFile = file;
        els.importConfirm.disabled = false;

        // 更新导入区域显示
        var textEl = els.importZone.querySelector('.import-zone__text');
        var hintEl = els.importZone.querySelector('.import-zone__hint');
        if (textEl) textEl.textContent = name;
        if (hintEl) hintEl.textContent = '文件大小：' + (file.size / 1024).toFixed(1) + ' KB';
    }

    // ========================================================
    //  9. 导出
    // ========================================================
    function initExport() {
        els.exportBtn.addEventListener('click', function () {
            var filtered = getFilteredQuestions();
            var csv = 'ID,题干,选项A,选项B,权重,分类,状态\n';
            filtered.forEach(function (q) {
                csv += [q.id, '"' + q.question + '"', '"' + q.optionA + '"', '"' + q.optionB + '"', q.weight, q.category, q.status].join(',') + '\n';
            });

            var blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' });
            var url = URL.createObjectURL(blob);
            var a = document.createElement('a');
            a.href = url;
            a.download = 'questions_export_' + new Date().toISOString().substring(0, 10) + '.csv';
            a.click();
            URL.revokeObjectURL(url);

            showToast('已导出 ' + filtered.length + ' 道题目');
            trackEvent('question_export', { count: filtered.length });
        });
    }

    // ========================================================
    // 10. 版本控制
    // ========================================================
    function renderVersions() {
        els.versionTimeline.innerHTML = state.versions.map(function (v) {
            return '<div class="version-item' + (v.isCurrent ? ' version-item--current' : '') + '">' +
                '<div class="version-item__dot"></div>' +
                '<div class="version-item__body">' +
                    '<div class="version-item__header">' +
                        '<span class="version-item__version">' + v.version + '</span>' +
                        (v.isCurrent ? '<span class="version-item__tag">当前版本</span>' : '') +
                        '<span class="version-item__time">' + v.time + '</span>' +
                    '</div>' +
                    '<p class="version-item__desc">' + v.desc + '</p>' +
                    '<span class="version-item__author">操作人：' + v.author + '</span>' +
                    (!v.isCurrent ? '<br><button class="version-item__rollback" data-version="' + v.version + '">回滚至此版本</button>' : '') +
                '</div>' +
            '</div>';
        }).join('');

        // 绑定回滚事件
        els.versionTimeline.querySelectorAll('.version-item__rollback').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var version = btn.getAttribute('data-version');
                if (!confirm('确认回滚至 ' + version + '？当前修改将丢失。')) return;
                showToast('已回滚至 ' + version);
                trackEvent('version_rollback', { version: version });
            });
        });
    }

    function initVersionControl() {
        els.createVersionBtn.addEventListener('click', function () {
            var now = new Date();
            var timeStr = now.getFullYear() + '-' + pad(now.getMonth() + 1) + '-' + pad(now.getDate()) + ' ' + pad(now.getHours()) + ':' + pad(now.getMinutes());
            var major = 2;
            var minor = state.versions.length;
            var newVersion = 'v' + major + '.' + (minor + 1);

            // 取消当前版本标记
            state.versions.forEach(function (v) { v.isCurrent = false; });

            state.versions.unshift({
                version: newVersion,
                desc: '手动发布新版本，包含 ' + state.questions.length + ' 道题目',
                author: '陈管理',
                time: timeStr,
                isCurrent: true
            });

            saveVersions();
            renderVersions();
            showToast('新版本 ' + newVersion + ' 已发布');
            trackEvent('version_publish', { version: newVersion });
        });
    }

    // ========================================================
    // 11. 灰度发布配置
    // ========================================================
    function initGrayscale() {
        // 加载已保存的灰度比例
        var savedGrayscale = localStorage.getItem(CONFIG.grayscaleKey);
        var grayscaleValue = 15;
        if (savedGrayscale) {
            try {
                var config = JSON.parse(savedGrayscale);
                grayscaleValue = config.percentage || 15;
            } catch (e) {}
        }
        els.grayscaleSlider.value = grayscaleValue;
        els.grayscaleValue.textContent = grayscaleValue + '%';

        // 滑块实时更新
        els.grayscaleSlider.addEventListener('input', function () {
            els.grayscaleValue.textContent = els.grayscaleSlider.value + '%';
        });

        els.saveGrayscaleBtn.addEventListener('click', function () {
            var percentage = parseInt(els.grayscaleSlider.value, 10);
            var groups = [];
            els.grayscaleSlider.closest('.admin-panel').querySelectorAll('.grayscale-group input:checked').forEach(function (cb) {
                groups.push(cb.value);
            });

            var config = { percentage: percentage, groups: groups, savedAt: getCurrentTimeStr() };
            localStorage.setItem(CONFIG.grayscaleKey, JSON.stringify(config));

            showToast('灰度配置已保存：' + percentage + '% 流量');
            trackEvent('grayscale_save', { percentage: percentage, groups: groups });
        });
    }

    // ========================================================
    // 12. 分页
    // ========================================================
    function initPagination() {
        els.prevPage.addEventListener('click', function () {
            if (state.currentPage > 1) {
                state.currentPage--;
                renderTable();
            }
        });

        els.nextPage.addEventListener('click', function () {
            var total = Math.ceil(getFilteredQuestions().length / CONFIG.pageSize);
            if (state.currentPage < total) {
                state.currentPage++;
                renderTable();
            }
        });
    }

    // ========================================================
    // 13. 退出 & 侧边栏
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

        // 侧边栏菜单切换
        document.querySelectorAll('.admin-menu__item').forEach(function (item) {
            item.addEventListener('click', function (e) {
                e.preventDefault();
                var page = item.getAttribute('data-page');
                if (page === 'questions') return;
                showToast('「' + item.querySelector('span').textContent + '」页面开发中');
            });
        });
    }

    // ========================================================
    // 14. ESC 关闭
    // ========================================================
    function initKeyboard() {
        document.addEventListener('keydown', function (e) {
            if (e.key !== 'Escape') return;

            if (els.editDrawer.classList.contains('drawer--open')) {
                closeDrawer();
                return;
            }
            if (els.importModal.classList.contains('modal--open')) {
                els.importModal.classList.remove('modal--open');
                return;
            }
            if (els.deleteModal.classList.contains('modal--open')) {
                els.deleteModal.classList.remove('modal--open');
                return;
            }
        });
    }

    // ========================================================
    // 工具函数
    // ========================================================
    function findQuestion(id) {
        return state.questions.find(function (q) { return q.id === id; });
    }

    function getRadioValue(name) {
        var checked = document.querySelector('input[name="' + name + '"]:checked');
        return checked ? checked.value : null;
    }

    function setRadioValue(name, value) {
        var radio = document.querySelector('input[name="' + name + '"][value="' + value + '"]');
        if (radio) radio.checked = true;
    }

    function escapeHtml(str) {
        if (!str) return '';
        return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function pad(n) {
        return n < 10 ? '0' + n : '' + n;
    }

    function getCurrentTimeStr() {
        var now = new Date();
        return now.getFullYear() + '-' + pad(now.getMonth() + 1) + '-' + pad(now.getDate()) + ' ' + pad(now.getHours()) + ':' + pad(now.getMinutes());
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
        loadQuestions();
        loadVersions();

        renderTable();
        renderVersions();

        initFilters();
        initSelectAll();
        initBatchDelete();
        initDrawer();
        initDelete();
        initImport();
        initExport();
        initVersionControl();
        initGrayscale();
        initPagination();
        initMisc();
        initKeyboard();

        trackEvent('admin_questions_page_view');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
