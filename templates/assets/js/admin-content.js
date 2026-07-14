/**
 * admin-content.js — 后台内容配置交互脚本
 * 功能：画像列表、富文本编辑器、推荐职业管理、CTA 文案配置、
 *       A/B 测试配置、版本历史回滚、审批流程
 * 数据来源：API.getAdminArchetypes / API.updateAdminArchetype /
 *           API.getAdminCareers / API.updateAdminCareer
 */

(function () {
    'use strict';

    // ============== 配置 ==============
    var CONFIG = {
        storageKey: 'admin_content_cache',      // 缓存键（仅用于网络异常时的降级缓存）
        versionKey: 'admin_content_version',
        dataVersion: '3.0',                      // 数据版本：升级测评体系后递增，触发旧缓存清除
        abTestKey: 'admin_ab_test_config'        // A/B 测试配置（本地配置，无 API）
    };

    var STATUS_MAP = {
        published: { label: '已发布', class: 'template-header__status--published', dot: 'template-item__status--published' },
        draft: { label: '草稿', class: 'template-header__status--draft', dot: 'template-item__status--draft' },
        review: { label: '审核中', class: 'template-header__status--review', dot: 'template-item__status--review' }
    };

    // ============== DOM 引用 ==============
    var els = {
        logoutBtn: document.getElementById('logoutBtn'),
        syncInfo: document.getElementById('syncInfo'),
        // 操作按钮
        previewBtn: document.getElementById('previewBtn'),
        saveDraftBtn: document.getElementById('saveDraftBtn'),
        publishBtn: document.getElementById('publishBtn'),
        // 模板列表
        addTemplateBtn: document.getElementById('addTemplateBtn'),
        templateSearch: document.getElementById('templateSearch'),
        templateList: document.getElementById('templateList'),
        // 模板信息
        templateName: document.getElementById('templateName'),
        templateType: document.getElementById('templateType'),
        templateId: document.getElementById('templateId'),
        templateStatus: document.getElementById('templateStatus'),
        // 编辑器
        editorContent: document.getElementById('editorContent'),
        charCount: document.getElementById('charCount'),
        // 推荐职位
        jobList: document.getElementById('jobList'),
        addJobBtn: document.getElementById('addJobBtn'),
        // CTA
        ctaPrimary: document.getElementById('ctaPrimary'),
        ctaSecondary: document.getElementById('ctaSecondary'),
        ctaHint: document.getElementById('ctaHint'),
        // A/B 测试抽屉
        abBtn: document.getElementById('abTestBtn'),
        abDrawer: document.getElementById('abDrawer'),
        abOverlay: document.getElementById('abOverlay'),
        abClose: document.getElementById('abClose'),
        abBody: document.getElementById('abBody'),
        abCancel: document.getElementById('abCancel'),
        abSave: document.getElementById('abSave'),
        // 版本历史抽屉
        historyBtn: document.getElementById('historyBtn'),
        historyDrawer: document.getElementById('historyDrawer'),
        historyOverlay: document.getElementById('historyOverlay'),
        historyClose: document.getElementById('historyClose'),
        historyBody: document.getElementById('historyBody'),
        // 审批弹窗
        approvalModal: document.getElementById('approvalModal'),
        approvalOverlay: document.getElementById('approvalOverlay'),
        approvalClose: document.getElementById('approvalClose'),
        approvalFlow: document.getElementById('approvalFlow'),
        approvalNote: document.getElementById('approvalNote'),
        approvalCancel: document.getElementById('approvalCancel'),
        approvalSubmit: document.getElementById('approvalSubmit'),
        // 回滚弹窗
        rollbackModal: document.getElementById('rollbackModal'),
        rollbackOverlay: document.getElementById('rollbackOverlay'),
        rollbackDesc: document.getElementById('rollbackDesc'),
        rollbackCancel: document.getElementById('rollbackCancel'),
        rollbackConfirm: document.getElementById('rollbackConfirm'),
        // Toast
        toast: document.getElementById('adminToast')
    };

    // ============== 状态 ==============
    var state = {
        templates: [],           // 画像列表（来自 API）
        currentTemplateId: null,
        jobs: [],                // 职业列表（来自 API）
        versions: [],            // 版本历史（本地内存）
        abTest: {
            control: { label: 'A 版本', tag: 'control', content: '立即解锁深度报告，了解你的完整职业发展路径', ctr: '12.3%', conv: '15.7%' },
            test: { label: 'B 版本', tag: 'test', content: '限时 ¥2.99 解锁万字深度报告，发现你的职业优势', ctr: '14.1%', conv: '17.2%' },
            trafficSplit: 50
        },
        rollbackTarget: null
    };

    // ========================================================
    //  1. 数据加载（调用 API 获取画像列表 + 职业列表）
    // ========================================================
    function loadData() {
        // 版本检测：缓存版本不匹配时清除旧缓存
        var savedVersion = localStorage.getItem(CONFIG.versionKey);
        if (savedVersion !== CONFIG.dataVersion) {
            localStorage.removeItem(CONFIG.storageKey);
            localStorage.setItem(CONFIG.versionKey, CONFIG.dataVersion);
        }

        // 加载 A/B 测试本地配置
        var savedAb = null;
        try {
            savedAb = JSON.parse(localStorage.getItem(CONFIG.abTestKey) || 'null');
        } catch (e) { savedAb = null; }
        if (savedAb && savedAb.control && savedAb.test) {
            state.abTest = savedAb;
        }

        // 并行请求画像列表和职业列表
        Promise.all([
            API.getAdminArchetypes().catch(function () { return null; }),
            API.getAdminCareers().catch(function () { return null; })
        ]).then(function (results) {
            var archetypeData = results[0];
            var careerData = results[1];

            // 画像列表
            if (archetypeData && archetypeData.list && archetypeData.list.length > 0) {
                state.templates = archetypeData.list.map(function (item) {
                    return {
                        id: String(item.id),
                        name: item.name,
                        code: item.code,
                        type: 'chapter',
                        typeLabel: item.typeLabel || '人格画像',
                        status: item.status || 'published',
                        content: item.content || '<p>暂无内容</p>',
                        // 扩展配置字段
                        slogan: item.slogan,
                        rarity: item.rarity,
                        rarityPercent: item.rarityPercent,
                        famous: item.famous,
                        partners: item.partners,
                        careers: item.careers,
                        dimensions: item.dimensions,
                        dimensionText: item.dimensionText,
                        mascot: item.mascot
                    };
                });
                // 写入降级缓存
                try {
                    localStorage.setItem(CONFIG.storageKey, JSON.stringify(state.templates));
                } catch (e) { /* 忽略缓存写入失败 */ }
            } else {
                // 降级：尝试读取缓存
                var cached = null;
                try {
                    cached = JSON.parse(localStorage.getItem(CONFIG.storageKey) || '[]');
                } catch (e) { cached = null; }
                if (Array.isArray(cached) && cached.length > 0) {
                    state.templates = cached;
                    showToast('网络异常，已显示缓存数据');
                } else {
                    state.templates = [];
                    showToast('画像列表加载失败');
                }
            }

            // 职业列表
            if (careerData && careerData.list) {
                state.jobs = careerData.list.map(function (item) {
                    return {
                        id: item.id,
                        name: item.name,
                        desc: item.desc,
                        category: item.category,
                        match: item.match || 0,
                        salary: item.salary,
                        growth: item.growth,
                        active: item.active
                    };
                });
            } else {
                state.jobs = [];
            }

            // 选中第一个模板
            if (state.templates.length > 0 && !state.currentTemplateId) {
                state.currentTemplateId = state.templates[0].id;
            }

            renderTemplateList();
            if (state.currentTemplateId) {
                selectTemplate(state.currentTemplateId);
            }
            renderJobs();
        }).catch(function (err) {
            showToast('数据加载失败：' + (err.message || '未知错误'));
            renderTemplateList();
            renderJobs();
        });
    }

    // ========================================================
    //  2. 模板列表渲染
    // ========================================================
    function renderTemplateList() {
        var search = els.templateSearch.value.trim().toLowerCase();
        var filtered = state.templates.filter(function (t) {
            return !search || t.name.toLowerCase().indexOf(search) >= 0 || t.id.toLowerCase().indexOf(search) >= 0;
        });

        if (filtered.length === 0) {
            els.templateList.innerHTML = '<div class="job-empty">未找到匹配的模板</div>';
            return;
        }

        els.templateList.innerHTML = filtered.map(renderTemplateItem).join('');
        bindTemplateItemEvents();
    }

    function renderTemplateItem(t) {
        var iconClass = 'template-item__icon--' + t.type;
        var iconSvg = getTemplateIcon(t.type);
        var statusInfo = STATUS_MAP[t.status] || STATUS_MAP.draft;
        var isActive = t.id === state.currentTemplateId;

        return '<div class="template-item' + (isActive ? ' template-item--active' : '') + '" data-id="' + t.id + '">' +
            '<div class="template-item__icon ' + iconClass + '">' + iconSvg + '</div>' +
            '<div class="template-item__body">' +
                '<div class="template-item__name">' + escapeHtml(t.name) + '</div>' +
                '<div class="template-item__meta">' + t.id + ' · ' + t.typeLabel + '</div>' +
            '</div>' +
            '<span class="template-item__status ' + statusInfo.dot + '"></span>' +
        '</div>';
    }

    function getTemplateIcon(type) {
        var icons = {
            chapter: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="9" y1="13" x2="15" y2="13"/></svg>',
            cta: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>',
            job: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>',
            paragraph: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><line x1="4" y1="6" x2="20" y2="6"/><line x1="4" y1="12" x2="20" y2="12"/><line x1="4" y1="18" x2="14" y2="18"/></svg>'
        };
        return icons[type] || icons.chapter;
    }

    function bindTemplateItemEvents() {
        els.templateList.querySelectorAll('.template-item').forEach(function (item) {
            item.addEventListener('click', function () {
                var id = item.getAttribute('data-id');
                selectTemplate(id);
            });
        });
    }

    // ========================================================
    //  3. 选择模板
    // ========================================================
    function selectTemplate(id) {
        var template = findTemplate(id);
        if (!template) return;

        state.currentTemplateId = id;

        els.templateName.textContent = template.name;
        els.templateType.textContent = template.typeLabel;
        els.templateId.textContent = template.id;

        var statusInfo = STATUS_MAP[template.status] || STATUS_MAP.draft;
        els.templateStatus.textContent = statusInfo.label;
        els.templateStatus.className = 'template-header__status ' + statusInfo.class;

        els.editorContent.innerHTML = template.content;
        updateCharCount();

        renderTemplateList();

        // 根据模板类型显示/隐藏编辑区
        var isChapter = template.type === 'chapter';
        els.editorContent.parentElement.style.display = isChapter ? 'block' : 'none';

        trackEvent('template_select', { id: id, type: template.type });
    }

    // ========================================================
    //  4. 富文本编辑器
    // ========================================================
    function initEditor() {
        // 工具栏按钮
        document.querySelectorAll('.editor-btn').forEach(function (btn) {
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                var cmd = btn.getAttribute('data-cmd');
                var value = btn.getAttribute('data-value');

                if (cmd === 'createLink') {
                    var url = prompt('请输入链接地址：', 'https://');
                    if (url) document.execCommand('createLink', false, url);
                } else if (cmd === 'insertImage') {
                    var imgSrc = prompt('请输入图片地址：', 'https://');
                    if (imgSrc) document.execCommand('insertImage', false, imgSrc);
                } else if (cmd) {
                    document.execCommand(cmd, false, value || null);
                }

                els.editorContent.focus();
                updateCharCount();
            });
        });

        // 字数统计
        els.editorContent.addEventListener('input', updateCharCount);
        els.editorContent.addEventListener('keyup', updateCharCount);
    }

    function updateCharCount() {
        var text = els.editorContent.innerText || '';
        els.charCount.textContent = text.length;
    }

    // ========================================================
    //  5. 推荐职业列表
    // ========================================================
    function renderJobs() {
        if (state.jobs.length === 0) {
            els.jobList.innerHTML = '<div class="job-empty">暂无推荐职位，点击「添加职位」开始配置</div>';
            return;
        }

        els.jobList.innerHTML = state.jobs.map(function (job, i) {
            return '<div class="job-item" data-index="' + i + '">' +
                '<span class="job-item__drag"><svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg></span>' +
                '<div class="job-item__body">' +
                    '<div class="job-item__name">' + escapeHtml(job.name) + '</div>' +
                    '<div class="job-item__desc">' + escapeHtml(job.desc) + '</div>' +
                '</div>' +
                '<span class="job-item__match">' + (job.match || 0) + '%</span>' +
                '<div class="job-item__actions">' +
                    '<button class="job-item__btn" data-action="edit"><svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg></button>' +
                    '<button class="job-item__btn job-item__btn--delete" data-action="delete"><svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-2 14a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2L5 6"/></svg></button>' +
                '</div>' +
            '</div>';
        }).join('');

        bindJobEvents();
    }

    function bindJobEvents() {
        els.jobList.querySelectorAll('.job-item').forEach(function (item) {
            var index = parseInt(item.getAttribute('data-index'), 10);

            item.querySelector('[data-action="edit"]').addEventListener('click', function () {
                editJob(index);
            });

            item.querySelector('[data-action="delete"]').addEventListener('click', function () {
                var job = state.jobs[index];
                if (!job) return;
                // 从本地列表移除（不调用 API 删除，仅标记 inactive）
                if (job.id) {
                    API.updateAdminCareer(job.id, { active: false }).then(function () {
                        state.jobs.splice(index, 1);
                        renderJobs();
                        showToast('职位已停用');
                    }).catch(function (err) {
                        showToast('停用失败：' + (err.message || '未知错误'));
                    });
                } else {
                    state.jobs.splice(index, 1);
                    renderJobs();
                    showToast('职位已删除');
                }
                trackEvent('job_delete', { index: index });
            });
        });
    }

    function editJob(index) {
        var job = state.jobs[index];
        if (!job) return;

        var name = prompt('职位名称：', job.name);
        if (name === null) return;
        var desc = prompt('职位描述：', job.desc);
        if (desc === null) return;
        var matchStr = prompt('匹配度（0-100）：', String(job.match || 0));
        if (matchStr === null) return;
        var match = parseInt(matchStr, 10);
        if (isNaN(match) || match < 0 || match > 100) {
            showToast('匹配度需为 0-100 的数字');
            return;
        }

        // 本地更新
        job.name = name || job.name;
        job.desc = desc || job.desc;
        job.match = match;

        // 调用 API 持久化
        if (job.id) {
            API.updateAdminCareer(job.id, { name: job.name, desc: job.desc }).then(function () {
                renderJobs();
                showToast('职位已更新');
            }).catch(function (err) {
                showToast('更新失败：' + (err.message || '未知错误'));
            });
        } else {
            renderJobs();
            showToast('职位已更新');
        }
        trackEvent('job_edit', { index: index });
    }

    function initJobs() {
        els.addJobBtn.addEventListener('click', function () {
            var name = prompt('职位名称：', '');
            if (!name) return;
            var desc = prompt('职位描述：', '');
            if (desc === null) return;
            var matchStr = prompt('匹配度（0-100）：', '85');
            var match = parseInt(matchStr, 10);
            if (isNaN(match) || match < 0 || match > 100) match = 85;

            state.jobs.push({ name: name, desc: desc, match: match, id: null });
            renderJobs();
            showToast('职位已添加（需通过 API 保存生效）');
            trackEvent('job_add', { name: name });
        });
    }

    // ========================================================
    //  6. CTA 文案
    // ========================================================
    function initCTA() {
        [els.ctaPrimary, els.ctaSecondary, els.ctaHint].forEach(function (input) {
            input.addEventListener('input', function () {
                var max = parseInt(input.getAttribute('maxlength'), 10);
                if (input.value.length > max) {
                    input.value = input.value.substring(0, max);
                }
            });
        });
    }

    // ========================================================
    //  7. A/B 测试配置（本地配置，无 API）
    // ========================================================
    function renderABTest() {
        var ab = state.abTest;

        els.abBody.innerHTML =
            '<div class="ab-section">' +
                '<div class="ab-section__title">版本对比</div>' +
                '<div class="ab-compare">' +
                    '<div class="ab-variant ab-variant--active">' +
                        '<div class="ab-variant__header">' +
                            '<span class="ab-variant__label">A 版本</span>' +
                            '<span class="ab-variant__tag ab-variant__tag--control">对照组</span>' +
                        '</div>' +
                        '<div class="ab-variant__content">' + escapeHtml(ab.control.content) + '</div>' +
                        '<div class="ab-variant__stats">' +
                            '<div class="ab-stat"><span class="ab-stat__value">' + ab.control.ctr + '</span><span class="ab-stat__label">点击率</span></div>' +
                            '<div class="ab-stat"><span class="ab-stat__value">' + ab.control.conv + '</span><span class="ab-stat__label">转化率</span></div>' +
                        '</div>' +
                    '</div>' +
                    '<div class="ab-variant">' +
                        '<div class="ab-variant__header">' +
                            '<span class="ab-variant__label">B 版本</span>' +
                            '<span class="ab-variant__tag ab-variant__tag--test">测试组</span>' +
                        '</div>' +
                        '<div class="ab-variant__content">' + escapeHtml(ab.test.content) + '</div>' +
                        '<div class="ab-variant__stats">' +
                            '<div class="ab-stat"><span class="ab-stat__value ab-stat__value--up">' + ab.test.ctr + '</span><span class="ab-stat__label">点击率 ↑</span></div>' +
                            '<div class="ab-stat"><span class="ab-stat__value ab-stat__value--up">' + ab.test.conv + '</span><span class="ab-stat__label">转化率 ↑</span></div>' +
                        '</div>' +
                    '</div>' +
                '</div>' +
            '</div>' +
            '<div class="ab-section">' +
                '<div class="ab-section__title">流量分配</div>' +
                '<div class="ab-config">' +
                    '<div class="ab-config__field">' +
                        '<label class="ab-config__label">测试组流量比例</label>' +
                        '<div class="ab-config__slider-wrapper">' +
                            '<input type="range" class="ab-config__slider" id="abSlider" min="0" max="100" value="' + ab.trafficSplit + '" step="10">' +
                            '<span class="ab-config__slider-value" id="abSliderValue">' + ab.trafficSplit + '%</span>' +
                        '</div>' +
                    '</div>' +
                    '<div class="ab-config__field">' +
                        '<label class="ab-config__label">测试周期</label>' +
                        '<input type="number" class="ab-config__input" id="abDuration" value="7" min="1" max="30"> 天' +
                    '</div>' +
                    '<div class="ab-config__field">' +
                        '<label class="ab-config__label">获胜条件</label>' +
                        '<select class="ab-config__input" id="abGoal">' +
                            '<option value="conv">转化率最高</option>' +
                            '<option value="ctr">点击率最高</option>' +
                            '<option value="revenue">收入最高</option>' +
                        '</select>' +
                    '</div>' +
                '</div>' +
            '</div>';

        // 滑块交互
        var slider = document.getElementById('abSlider');
        var sliderValue = document.getElementById('abSliderValue');
        if (slider) {
            slider.addEventListener('input', function () {
                sliderValue.textContent = slider.value + '%';
                var pct = slider.value;
                slider.style.background = 'linear-gradient(to right, #9B7ED8 0%, #9B7ED8 ' + pct + '%, #e7eae8 ' + pct + '%, #e7eae8 100%)';
            });
        }
    }

    function initABTest() {
        els.abBtn.addEventListener('click', function () {
            renderABTest();
            els.abDrawer.classList.add('drawer--open');
        });

        els.abClose.addEventListener('click', closeABDrawer);
        els.abOverlay.addEventListener('click', closeABDrawer);
        els.abCancel.addEventListener('click', closeABDrawer);

        els.abSave.addEventListener('click', function () {
            var slider = document.getElementById('abSlider');
            var duration = document.getElementById('abDuration');
            if (slider && duration) {
                state.abTest.trafficSplit = parseInt(slider.value, 10);
                try {
                    localStorage.setItem(CONFIG.abTestKey, JSON.stringify(state.abTest));
                } catch (e) { /* 忽略 */ }
            }
            closeABDrawer();
            showToast('A/B 测试已启动，预计 ' + (duration ? duration.value : 7) + ' 天后出结果');
            trackEvent('ab_test_start', { traffic: state.abTest.trafficSplit });
        });
    }

    function closeABDrawer() {
        els.abDrawer.classList.remove('drawer--open');
    }

    // ========================================================
    //  8. 版本历史（本地内存）
    // ========================================================
    function renderVersions() {
        if (state.versions.length === 0) {
            els.historyBody.innerHTML = '<div class="job-empty">暂无版本历史记录</div>';
            return;
        }

        els.historyBody.innerHTML = '<div class="version-timeline">' +
            state.versions.map(function (v) {
                var isCurrent = v.status === 'current';
                var diffHtml = v.diff
                    ? '<div class="version-entry__diff"><span class="version-entry__diff--add">+' + v.diff.add + '</span> <span class="version-entry__diff--del">-' + v.diff.del + '</span> 字</div>'
                    : '';

                var actions = isCurrent
                    ? ''
                    : '<div class="version-entry__actions"><button class="btn btn--ghost btn--sm" data-rollback="' + v.version + '"><svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 7v6h6"/><path d="M21 17a9 9 0 0 0-9-9 9 9 0 0 0-6 2.3L3 13"/></svg> 回滚至此版本</button></div>';

                return '<div class="version-entry' + (isCurrent ? ' version-entry--current' : '') + '">' +
                    '<div class="version-entry__header">' +
                        '<span class="version-entry__version">' + v.version + '</span>' +
                        '<span class="version-entry__tag version-entry__tag--' + v.status + '">' + v.statusLabel + '</span>' +
                    '</div>' +
                    '<div class="version-entry__time">' + v.time + '</div>' +
                    '<div class="version-entry__author"><strong>' + escapeHtml(v.author) + '</strong></div>' +
                    '<div class="version-entry__note">' + escapeHtml(v.note) + '</div>' +
                    diffHtml +
                    actions +
                '</div>';
            }).join('') +
        '</div>';

        // 绑定回滚按钮
        els.historyBody.querySelectorAll('[data-rollback]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var version = btn.getAttribute('data-rollback');
                state.rollbackTarget = version;
                els.rollbackDesc.textContent = '确认回滚至 ' + version + '？回滚后将覆盖当前内容，此操作不可撤销';
                els.rollbackModal.classList.add('modal--open');
            });
        });
    }

    function initHistory() {
        els.historyBtn.addEventListener('click', function () {
            renderVersions();
            els.historyDrawer.classList.add('drawer--open');
        });

        els.historyClose.addEventListener('click', function () {
            els.historyDrawer.classList.remove('drawer--open');
        });

        els.historyOverlay.addEventListener('click', function () {
            els.historyDrawer.classList.remove('drawer--open');
        });
    }

    // ========================================================
    //  9. 回滚
    // ========================================================
    function initRollback() {
        els.rollbackCancel.addEventListener('click', function () {
            els.rollbackModal.classList.remove('modal--open');
            state.rollbackTarget = null;
        });

        els.rollbackOverlay.addEventListener('click', function () {
            els.rollbackModal.classList.remove('modal--open');
            state.rollbackTarget = null;
        });

        els.rollbackConfirm.addEventListener('click', function () {
            if (!state.rollbackTarget) return;

            var version = state.rollbackTarget;
            els.rollbackModal.classList.remove('modal--open');

            // 添加新版本记录
            state.versions.unshift({
                version: 'v3.2.2',
                time: getCurrentTimeStr(),
                author: '管理员',
                note: '回滚至 ' + version + ' 版本',
                status: 'current',
                statusLabel: '当前版本',
                diff: { add: 0, del: 0 }
            });

            // 将之前的 current 改为 published
            state.versions.forEach(function (v, i) {
                if (i > 0 && v.status === 'current') {
                    v.status = 'published';
                    v.statusLabel = '已发布';
                }
            });

            els.historyDrawer.classList.remove('drawer--open');
            showToast('已回滚至 ' + version);
            trackEvent('version_rollback', { to: version });
            state.rollbackTarget = null;
        });
    }

    // ========================================================
    // 10. 审批流程
    // ========================================================
    function renderApprovalFlow() {
        els.approvalFlow.innerHTML =
            '<div class="approval-step">' +
                '<div class="approval-step__icon approval-step__icon--done"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg></div>' +
                '<div class="approval-step__body">' +
                    '<div class="approval-step__title">提交修改</div>' +
                    '<div class="approval-step__desc">编辑人员提交内容修改请求</div>' +
                    '<div class="approval-step__time">' + getCurrentTimeStr() + '</div>' +
                '</div>' +
                '<span class="approval-step__status approval-step__status--done">已完成</span>' +
            '</div>' +
            '<div class="approval-step">' +
                '<div class="approval-step__icon approval-step__icon--current"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg></div>' +
                '<div class="approval-step__body">' +
                    '<div class="approval-step__title">一级审批：内容主管</div>' +
                    '<div class="approval-step__desc">等待审核中</div>' +
                    '<div class="approval-step__time">预计 2 小时内完成</div>' +
                '</div>' +
                '<span class="approval-step__status approval-step__status--current">审核中</span>' +
            '</div>' +
            '<div class="approval-step">' +
                '<div class="approval-step__icon approval-step__icon--pending"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12" y2="16"/></svg></div>' +
                '<div class="approval-step__body">' +
                    '<div class="approval-step__title">二级审批：产品总监</div>' +
                    '<div class="approval-step__desc">待审</div>' +
                    '<div class="approval-step__time">一级审批通过后开始</div>' +
                '</div>' +
                '<span class="approval-step__status approval-step__status--pending">待审</span>' +
            '</div>' +
            '<div class="approval-step">' +
                '<div class="approval-step__icon approval-step__icon--pending"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 2L11 13"/><path d="M22 2l-7 20-4-9-9-4 20-7z"/></svg></div>' +
                '<div class="approval-step__body">' +
                    '<div class="approval-step__title">发布上线</div>' +
                    '<div class="approval-step__desc">审批通过后自动发布，延迟 < 30 秒</div>' +
                '</div>' +
                '<span class="approval-step__status approval-step__status--pending">待发布</span>' +
            '</div>';
    }

    function initApproval() {
        els.publishBtn.addEventListener('click', function () {
            renderApprovalFlow();
            els.approvalNote.value = '';
            els.approvalModal.classList.add('modal--open');
        });

        els.approvalClose.addEventListener('click', function () {
            els.approvalModal.classList.remove('modal--open');
        });

        els.approvalOverlay.addEventListener('click', function () {
            els.approvalModal.classList.remove('modal--open');
        });

        els.approvalCancel.addEventListener('click', function () {
            els.approvalModal.classList.remove('modal--open');
        });

        els.approvalSubmit.addEventListener('click', function () {
            var note = els.approvalNote.value.trim();
            if (!note) {
                showToast('请填写修改说明');
                els.approvalNote.focus();
                return;
            }

            els.approvalModal.classList.remove('modal--open');

            // 将当前模板状态改为 review
            var template = getCurrentTemplate();
            if (template) {
                template.status = 'review';
                selectTemplate(template.id);
            }

            showToast('已提交审批，等待一级审核');
            trackEvent('approval_submit', { template: state.currentTemplateId, note: note });
        });
    }

    // ========================================================
    // 11. 顶部操作按钮（调用 API 保存画像内容）
    // ========================================================
    function initTopActions() {
        els.previewBtn.addEventListener('click', function () {
            showToast('正在打开预览...');
            trackEvent('content_preview');
        });

        els.saveDraftBtn.addEventListener('click', function () {
            var template = getCurrentTemplate();
            if (!template) {
                showToast('请先选择一个画像');
                return;
            }

            var htmlContent = els.editorContent.innerHTML;
            template.content = htmlContent;

            // 调用 API 保存画像内容
            API.updateAdminArchetype(template.id, { content: htmlContent }).then(function () {
                if (template.status === 'published') {
                    template.status = 'draft';
                }
                selectTemplate(template.id);
                showToast('草稿已保存');
            }).catch(function (err) {
                showToast('保存失败：' + (err.message || '未知错误'));
            });

            trackEvent('content_save_draft');
        });
    }

    // ========================================================
    // 12. 搜索
    // ========================================================
    function initSearch() {
        var timer = null;
        els.templateSearch.addEventListener('input', function () {
            if (timer) clearTimeout(timer);
            timer = setTimeout(renderTemplateList, 200);
        });
    }

    // ========================================================
    // 13. 新增模板（本地内存，无 API 新增画像）
    // ========================================================
    function initAddTemplate() {
        els.addTemplateBtn.addEventListener('click', function () {
            var name = prompt('模板名称：', '');
            if (!name) return;

            var types = ['chapter', 'cta', 'job', 'paragraph'];
            var typeLabels = ['报告章节', 'CTA 文案', '推荐职位', '段落文案'];
            var typeStr = prompt('模板类型（1:报告章节 2:CTA文案 3:推荐职位 4:段落文案）：', '1');
            var typeIdx = parseInt(typeStr, 10) - 1;
            if (typeIdx < 0 || typeIdx >= types.length) typeIdx = 0;

            var newId = 'LOCAL-' + String(state.templates.length + 1).padStart(3, '0');
            var newTemplate = {
                id: newId,
                name: name,
                type: types[typeIdx],
                typeLabel: typeLabels[typeIdx],
                status: 'draft',
                content: '<p>请在此输入内容...</p>'
            };

            state.templates.push(newTemplate);
            renderTemplateList();
            selectTemplate(newId);
            showToast('新模板已创建（本地，需通过 API 同步）');
            trackEvent('template_add', { id: newId, type: types[typeIdx] });
        });
    }

    // ========================================================
    // 14. 退出 & 侧边栏
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
    // 15. ESC 键
    // ========================================================
    function initKeyboard() {
        document.addEventListener('keydown', function (e) {
            if (e.key !== 'Escape') return;

            if (els.approvalModal.classList.contains('modal--open')) {
                els.approvalModal.classList.remove('modal--open');
                return;
            }
            if (els.rollbackModal.classList.contains('modal--open')) {
                els.rollbackModal.classList.remove('modal--open');
                return;
            }
            if (els.abDrawer.classList.contains('drawer--open')) {
                closeABDrawer();
                return;
            }
            if (els.historyDrawer.classList.contains('drawer--open')) {
                els.historyDrawer.classList.remove('drawer--open');
                return;
            }
        });
    }

    // ========================================================
    // 工具函数
    // ========================================================
    function getCurrentTemplate() {
        return findTemplate(state.currentTemplateId);
    }

    function findTemplate(id) {
        return state.templates.find(function (t) { return String(t.id) === String(id); });
    }

    function escapeHtml(str) {
        if (!str) return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function getCurrentTimeStr() {
        var now = new Date();
        function pad(n) { return n < 10 ? '0' + n : '' + n; }
        return now.getFullYear() + '-' + pad(now.getMonth() + 1) + '-' + pad(now.getDate()) + ' ' + pad(now.getHours()) + ':' + pad(now.getMinutes());
    }

    function trackEvent(eventName, data) {
        if (typeof API !== 'undefined' && API.trackEvent) {
            API.trackEvent(eventName, data || {}, 'admin-content');
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
        loadData();

        initEditor();
        initJobs();
        initCTA();
        initABTest();
        initHistory();
        initRollback();
        initApproval();
        initTopActions();
        initSearch();
        initAddTemplate();
        initMisc();
        initKeyboard();

        trackEvent('admin_content_page_view');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
