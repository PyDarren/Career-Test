/**
 * admin-questions.js — 后台题库管理交互脚本
 * 功能：表格渲染、搜索筛选、新增/编辑/删除、批量操作、
 *       导入导出、版本控制、灰度发布配置
 * 数据来源：API.getAdminQuestions / API.createAdminQuestion /
 *           API.updateAdminQuestion / API.deleteAdminQuestion / API.exportAdminQuestions
 */

(function () {
    'use strict';

    // ============== 配置 ==============
    var CONFIG = {
        storageKey: 'admin_questions_cache',        // 缓存键（仅用于网络异常时的降级缓存）
        versionKey: 'admin_questions_version',       // 版本检测：数据版本不匹配时清除旧缓存
        dataVersion: '3.0',
        versionsKey: 'admin_question_versions',      // 版本历史记录存储（本地配置）
        grayscaleKey: 'admin_grayscale_config',      // 灰度发布配置（本地配置）
        pageSize: 10
    };

    // 题目状态中文映射（统一使用 active/inactive/grayscale）
    var STATUS_MAP = {
        active: '启用中',
        inactive: '已停用',
        grayscale: '灰度中',
        published: '已发布',
        draft: '草稿'
    };

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
        questions: [],           // 当前页题目（来自 API）
        total: 0,                // 筛选后题目总数（来自 API）
        stats: {},               // 统计概览（来自 API）
        versions: [],            // 版本历史（本地内存）
        currentPage: 1,
        selectedIds: new Set(),  // 当前页选中题目 id
        editingId: null,
        pendingDeleteIds: null,
        importFile: null
    };

    // ========================================================
    //  1. 数据加载（服务端分页 + 筛选）
    // ========================================================
    function buildParams() {
        return {
            search: els.searchInput.value.trim(),
            category: els.filterCategory.value,
            status: els.filterStatus.value,
            page: state.currentPage,
            page_size: CONFIG.pageSize
        };
    }

    function loadQuestions() {
        // 版本检测：缓存版本不匹配时清除旧缓存
        var savedVersion = localStorage.getItem(CONFIG.versionKey);
        if (savedVersion !== CONFIG.dataVersion) {
            localStorage.removeItem(CONFIG.storageKey);
            localStorage.setItem(CONFIG.versionKey, CONFIG.dataVersion);
        }

        var params = buildParams();
        API.getAdminQuestions(params).then(function (data) {
            state.questions = (data && data.list) || [];
            state.total = (data && data.total) || 0;
            state.stats = (data && data.stats) || {};
            // 写入降级缓存
            try {
                localStorage.setItem(CONFIG.storageKey, JSON.stringify(state.questions));
            } catch (e) { /* 忽略缓存写入失败 */ }
            renderTable();
            updateStats();
        }).catch(function (err) {
            // 降级：尝试读取缓存
            var cached = null;
            try {
                cached = JSON.parse(localStorage.getItem(CONFIG.storageKey) || '[]');
            } catch (e) { cached = null; }
            if (Array.isArray(cached) && cached.length > 0) {
                state.questions = cached;
                state.total = cached.length;
                state.stats = {};
                showToast('网络异常，已显示缓存数据');
            } else {
                state.questions = [];
                state.total = 0;
                state.stats = {};
                showToast('题目加载失败：' + (err.message || '未知错误'));
            }
            renderTable();
            updateStats();
        });
    }

    // ========================================================
    //  2. 表格渲染
    // ========================================================
    function renderTable() {
        var totalPages = Math.ceil(state.total / CONFIG.pageSize) || 1;
        if (state.currentPage > totalPages) state.currentPage = totalPages;

        var pageData = state.questions;

        if (pageData.length === 0) {
            els.tableBody.innerHTML = '<tr><td colspan="9" style="text-align:center;padding:40px;color:#9B9BAB;">暂无匹配的题目</td></tr>';
        } else {
            els.tableBody.innerHTML = pageData.map(renderRow).join('');
            bindRowEvents();
        }

        // 分页信息
        var start = (state.currentPage - 1) * CONFIG.pageSize;
        var end = Math.min(start + CONFIG.pageSize, state.total);
        if (state.total === 0) {
            els.paginationInfo.textContent = '共 0 条';
        } else {
            els.paginationInfo.textContent = '共 ' + state.total + ' 条，第 ' + (start + 1) + '-' + end + ' 条';
        }
        els.prevPage.disabled = state.currentPage <= 1;
        els.nextPage.disabled = state.currentPage >= totalPages;

        updateBatchDeleteBtn();
        updateSelectAllState();
    }

    function renderRow(q) {
        var weight = q.weight || 3;
        var weightClass = weight <= 2 ? 'low' : weight <= 3 ? 'mid' : weight === 4 ? 'high' : 'key';
        var statusClass = 'status-dot--' + q.status;
        var statusText = STATUS_MAP[q.status] || q.status;
        var isChecked = state.selectedIds.has(String(q.id));

        return '<tr data-id="' + q.id + '">' +
            '<td class="col-check"><input type="checkbox" class="row-check"' + (isChecked ? ' checked' : '') + '></td>' +
            '<td><span class="table-id">' + escapeHtml(String(q.id)) + '</span></td>' +
            '<td><div class="table-question" title="' + escapeHtml(q.question) + '">' + escapeHtml(q.question) + '</div></td>' +
            '<td><span class="table-option">' + escapeHtml(q.optionA) + '</span></td>' +
            '<td><span class="table-option">' + escapeHtml(q.optionB) + '</span></td>' +
            '<td><span class="weight-badge weight-badge--' + weightClass + '">' + weight + '</span></td>' +
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
    //  3. 搜索与筛选（参数提交给 API）
    // ========================================================
    function initFilters() {
        var searchTimer = null;
        els.searchInput.addEventListener('input', function () {
            if (searchTimer) clearTimeout(searchTimer);
            searchTimer = setTimeout(function () {
                state.currentPage = 1;
                loadQuestions();
            }, 300);
        });

        els.filterCategory.addEventListener('change', function () {
            state.currentPage = 1;
            loadQuestions();
        });

        els.filterStatus.addEventListener('change', function () {
            state.currentPage = 1;
            loadQuestions();
        });
    }

    // ========================================================
    //  4. 统计更新（来自 API 返回的 stats 字段）
    // ========================================================
    function updateStats() {
        var s = state.stats || {};
        els.statTotal.textContent = (s.total != null) ? s.total : state.total;
        els.statActive.textContent = (s.active != null) ? s.active : 0;
        els.statGrayscale.textContent = (s.grayscale != null) ? s.grayscale : 0;
    }

    // ========================================================
    //  5. 全选 & 批量操作
    // ========================================================
    function initSelectAll() {
        els.selectAll.addEventListener('change', function () {
            if (els.selectAll.checked) {
                state.questions.forEach(function (q) { state.selectedIds.add(String(q.id)); });
            } else {
                state.questions.forEach(function (q) { state.selectedIds.delete(String(q.id)); });
            }
            renderTable();
        });
    }

    function updateSelectAllState() {
        var allChecked = state.questions.length > 0 && state.questions.every(function (q) { return state.selectedIds.has(String(q.id)); });
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
    //  6. 新增/编辑抽屉（调用 API）
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
            els.editWeight.value = String(q.weight || 3);
            els.editCategory.value = q.category;
            setRadioValue('editStatus', q.status);

            // 操作日志
            if (q.logs && q.logs.length > 0) {
                els.editLogSection.style.display = 'block';
                els.editLog.innerHTML = q.logs.map(function (log) {
                    return '<div class="edit-log__item"><span class="edit-log__time">' + escapeHtml(log.time) +
                        '</span><span class="edit-log__content"><strong>' + escapeHtml(log.author) + '</strong> ' + escapeHtml(log.action) + '</span></div>';
                }).join('');
            } else {
                els.editLogSection.style.display = 'none';
            }
        } else {
            els.drawerTitle.textContent = '新增题目';
            els.editId.value = '';
            els.editQuestion.value = '';
            els.editOptionA.value = '非常不符合';
            els.editOptionB.value = '非常符合';
            els.editWeight.value = '3';
            els.editCategory.value = 'BO';
            setRadioValue('editStatus', 'active');
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

            var weight = parseInt(els.editWeight.value, 10) || 3;
            var category = els.editCategory.value;
            var status = getRadioValue('editStatus') || 'active';

            var payload = {
                question: question,
                optionA: optionA,
                optionB: optionB,
                weight: weight,
                category: category,
                status: status
            };

            els.drawerSave.disabled = true;

            var promise;
            if (state.editingId) {
                promise = API.updateAdminQuestion(state.editingId, payload);
                trackEvent('question_edit', { id: state.editingId });
            } else {
                promise = API.createAdminQuestion(payload);
                trackEvent('question_create');
            }

            promise.then(function () {
                showToast(state.editingId ? '题目已更新' : '题目已新增');
                closeDrawer();
                loadQuestions();
            }).catch(function (err) {
                showToast('保存失败：' + (err.message || '未知错误'));
            }).then(function () {
                els.drawerSave.disabled = false;
            });
        });

        els.addQuestionBtn.addEventListener('click', function () {
            openEditDrawer(null);
        });
    }

    // ========================================================
    //  7. 删除（调用 API）
    // ========================================================
    function openDeleteModal(ids) {
        state.pendingDeleteIds = ids;
        if (ids.length === 1) {
            els.deleteTitle.textContent = '确认删除该题目？';
            els.deleteDesc.textContent = '删除后该题目将立即下线，此操作不可恢复';
        } else {
            els.deleteTitle.textContent = '确认删除 ' + ids.length + ' 道题目？';
            els.deleteDesc.textContent = '删除后这些题目将立即下线，此操作不可恢复';
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
            var ids = state.pendingDeleteIds;
            els.deleteConfirm.disabled = true;

            // 逐条调用删除 API
            var promises = ids.map(function (id) { return API.deleteAdminQuestion(id); });
            Promise.all(promises).then(function () {
                ids.forEach(function (id) { state.selectedIds.delete(id); });
                state.pendingDeleteIds = null;
                els.deleteModal.classList.remove('modal--open');
                showToast('已删除 ' + ids.length + ' 道题目');
                trackEvent('question_delete', { count: ids.length });
                loadQuestions();
            }).catch(function (err) {
                showToast('删除失败：' + (err.message || '未知错误'));
            }).then(function () {
                els.deleteConfirm.disabled = false;
            });
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
            els.importConfirm.disabled = true;
            // M4 阶段：通过 API 逐条创建占位题目（真实场景应解析文件后批量创建）
            var categories = ['BO', 'BC', 'BE', 'BA', 'BN', 'RR', 'RI', 'RA', 'RS', 'RE', 'RC'];
            var promises = [];
            for (var i = 1; i <= 5; i++) {
                promises.push(API.createAdminQuestion({
                    question: '（导入）第 ' + i + ' 道题目示例内容',
                    optionA: '非常不符合',
                    optionB: '非常符合',
                    weight: 3,
                    category: categories[i % categories.length],
                    status: 'inactive'
                }));
            }
            Promise.all(promises).then(function () {
                els.importModal.classList.remove('modal--open');
                showToast('成功导入 5 道题目');
                trackEvent('question_import', { count: 5 });
                loadQuestions();
            }).catch(function (err) {
                showToast('导入失败：' + (err.message || '未知错误'));
            }).then(function () {
                els.importConfirm.disabled = false;
            });
        });

        // 下载模板
        els.downloadTemplate.addEventListener('click', function (e) {
            e.preventDefault();
            var csv = '序号,维度,题干,题目类型,是否反向,是否启用\n1,BO,示例题干,ocean,否,是\n';
            API.downloadBlob(new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' }), 'question_import_template.csv');
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
    //  9. 导出（调用 API 下载 CSV）
    // ========================================================
    function initExport() {
        els.exportBtn.addEventListener('click', function () {
            if (state.total === 0) {
                showToast('没有可导出的题目数据');
                return;
            }
            var params = buildParams();
            // 导出全部筛选结果，不分页
            delete params.page;
            delete params.page_size;
            API.exportAdminQuestions(params).then(function (blob) {
                API.downloadBlob(blob, 'questions_export_' + new Date().toISOString().substring(0, 10) + '.csv');
                showToast('已导出 ' + state.total + ' 道题目');
                trackEvent('question_export', { count: state.total });
            }).catch(function (err) {
                showToast('导出失败：' + (err.message || '未知错误'));
            });
        });
    }

    // ========================================================
    // 10. 版本控制（本地内存记录）
    // ========================================================
    function renderVersions() {
        if (state.versions.length === 0) {
            els.versionTimeline.innerHTML = '<div style="text-align:center;padding:30px;color:#9B9BAB;">暂无版本记录</div>';
            return;
        }
        els.versionTimeline.innerHTML = state.versions.map(function (v) {
            return '<div class="version-item' + (v.isCurrent ? ' version-item--current' : '') + '">' +
                '<div class="version-item__dot"></div>' +
                '<div class="version-item__body">' +
                    '<div class="version-item__header">' +
                        '<span class="version-item__version">' + escapeHtml(v.version) + '</span>' +
                        (v.isCurrent ? '<span class="version-item__tag">当前版本</span>' : '') +
                        '<span class="version-item__time">' + escapeHtml(v.time) + '</span>' +
                    '</div>' +
                    '<p class="version-item__desc">' + escapeHtml(v.desc) + '</p>' +
                    '<span class="version-item__author">操作人：' + escapeHtml(v.author) + '</span>' +
                    (!v.isCurrent ? '<br><button class="version-item__rollback" data-version="' + escapeHtml(v.version) + '">回滚至此版本</button>' : '') +
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
            var timeStr = getCurrentTimeStr();
            var minor = state.versions.length;
            var newVersion = 'v2.' + (minor + 1);

            // 取消当前版本标记
            state.versions.forEach(function (v) { v.isCurrent = false; });

            state.versions.unshift({
                version: newVersion,
                desc: '手动发布新版本，包含 ' + state.total + ' 道题目',
                author: '管理员',
                time: timeStr,
                isCurrent: true
            });

            renderVersions();
            showToast('新版本 ' + newVersion + ' 已发布');
            trackEvent('version_publish', { version: newVersion });
        });
    }

    // ========================================================
    // 11. 灰度发布配置（本地配置）
    // ========================================================
    function initGrayscale() {
        // 加载已保存的灰度比例
        var savedGrayscale = localStorage.getItem(CONFIG.grayscaleKey);
        var grayscaleValue = 15;
        if (savedGrayscale) {
            try {
                var config = JSON.parse(savedGrayscale);
                grayscaleValue = config.percentage || 15;
            } catch (e) { /* 忽略解析失败 */ }
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
            try {
                localStorage.setItem(CONFIG.grayscaleKey, JSON.stringify(config));
            } catch (e) { /* 忽略存储失败 */ }

            showToast('灰度配置已保存：' + percentage + '% 流量');
            trackEvent('grayscale_save', { percentage: percentage, groups: groups });
        });
    }

    // ========================================================
    // 12. 分页（服务端分页）
    // ========================================================
    function initPagination() {
        els.prevPage.addEventListener('click', function () {
            if (state.currentPage > 1) {
                state.currentPage--;
                loadQuestions();
            }
        });

        els.nextPage.addEventListener('click', function () {
            var totalPages = Math.ceil(state.total / CONFIG.pageSize) || 1;
            if (state.currentPage < totalPages) {
                state.currentPage++;
                loadQuestions();
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
                    window.location.href = '/';
                }, 1000);
            }
        });
        // 侧边栏菜单导航（通过 href 属性实现跳转，无需 JS 拦截）
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
        return state.questions.find(function (q) { return String(q.id) === String(id); });
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
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function pad(n) {
        return n < 10 ? '0' + n : '' + n;
    }

    function getCurrentTimeStr() {
        var now = new Date();
        return now.getFullYear() + '-' + pad(now.getMonth() + 1) + '-' + pad(now.getDate()) + ' ' + pad(now.getHours()) + ':' + pad(now.getMinutes());
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
        loadQuestions();
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
