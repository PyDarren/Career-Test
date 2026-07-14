/**
 * deep-report.js — 深度报告详情页交互脚本
 * 功能：目录抽屉、锚点跳转、阅读进度条、章节高亮、底部操作栏、
 *       分享报告、返回顶部、阅读时长追踪、埋点事件、进度自动保存
 */

(function () {
    'use strict';

    // ============== 配置 ==============
    var CONFIG = {
        navbarHeight: 56,           // 固定导航栏高度（px）
        actionbarShowOffset: 400,   // 底部操作栏出现的滚动阈值（px）
        // 以下 key 会在 loadReport 后追加 assessment_id 后缀
        scrollRestoreKey: 'deep_report_scroll',  // 阅读进度 localStorage key
        checklistKey: 'deep_report_checklist',   // 清单状态 localStorage key
        readStartKey: 'deep_report_read_start',  // 阅读开始时间 localStorage key
        durationKey: 'deep_report_duration',     // 累计阅读时长 localStorage key
        // 从 API 返回数据填充
        code: '',
        title: ''
    };

    // ============== DOM 元素引用 ==============
    var els = {
        navbar:        document.getElementById('reportNavbar'),
        backBtn:       document.getElementById('backBtn'),
        tocToggle:     document.getElementById('tocToggle'),
        tocDrawer:     document.getElementById('tocDrawer'),
        tocOverlay:    document.getElementById('tocOverlay'),
        tocClose:      document.getElementById('tocClose'),
        tocLinks:      document.querySelectorAll('.toc-link'),
        tocModuleLinks:document.querySelectorAll('.toc-module-link'),
        progressFill:  document.getElementById('readingProgress'),
        chapters:      document.querySelectorAll('.report-chapter'),
        actionbar:     document.getElementById('reportActionbar'),
        shareBtn:      document.getElementById('shareReportBtn'),
        backToTopBtn:  document.getElementById('backToTopBtn'),
        readDuration:  document.getElementById('readDuration'),
        actionItems:   document.querySelectorAll('.action-item input[type="checkbox"]'),
        reportEnd:     document.querySelector('.report-end')
    };

    // ============== 内部状态 ==============
    var state = {
        tocOpen: false,
        readStart: null,
        accumulatedDuration: 0,
        bottomTracked: false,
        activeChapter: null,
        assessmentId: null,
        reportLoaded: false
    };

    // ========================================================
    //  1. 目录抽屉开关
    // ========================================================
    function initTocDrawer() {
        if (!els.tocToggle || !els.tocDrawer) return;

        els.tocToggle.addEventListener('click', function () {
            openToc();
        });

        if (els.tocClose) {
            els.tocClose.addEventListener('click', function () {
                closeToc();
            });
        }

        if (els.tocOverlay) {
            els.tocOverlay.addEventListener('click', function () {
                closeToc();
            });
        }

        // ESC 关闭
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && state.tocOpen) {
                closeToc();
            }
        });
    }

    function openToc() {
        els.tocDrawer.classList.add('report-toc-drawer--open');
        state.tocOpen = true;
        document.body.style.overflow = 'hidden';
    }

    function closeToc() {
        els.tocDrawer.classList.remove('report-toc-drawer--open');
        state.tocOpen = false;
        document.body.style.overflow = '';
    }

    // ========================================================
    //  2. 锚点跳转（平滑滚动，考虑固定导航栏偏移）
    // ========================================================
    function initAnchorNav() {
        // 章节链接
        els.tocLinks.forEach(function (link) {
            link.addEventListener('click', function (e) {
                e.preventDefault();
                var targetId = link.getAttribute('href');
                scrollToElement(targetId);
                closeToc();
                highlightTocLink(link);
            });
        });

        // 模块链接
        els.tocModuleLinks.forEach(function (link) {
            link.addEventListener('click', function (e) {
                e.preventDefault();
                var targetId = link.getAttribute('href');
                scrollToElement(targetId);
                closeToc();
            });
        });
    }

    function scrollToElement(selector) {
        var target = document.querySelector(selector);
        if (!target) return;

        var rect = target.getBoundingClientRect();
        var scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        var offset = rect.top + scrollTop - CONFIG.navbarHeight - 16;

        window.scrollTo({
            top: offset,
            behavior: 'smooth'
        });
    }

    function highlightTocLink(activeLink) {
        els.tocLinks.forEach(function (l) {
            l.classList.remove('toc-link--active');
        });
        if (activeLink) {
            activeLink.classList.add('toc-link--active');
        }
    }

    // ========================================================
    //  3. 阅读进度条
    // ========================================================
    function updateReadingProgress() {
        if (!els.progressFill) return;

        var scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        var scrollHeight = document.documentElement.scrollHeight - window.innerHeight;
        var progress = scrollHeight > 0 ? (scrollTop / scrollHeight) * 100 : 0;

        // 限制范围 0~100
        progress = Math.min(100, Math.max(0, progress));
        els.progressFill.style.width = progress + '%';
    }

    // ========================================================
    //  4. 章节高亮（IntersectionObserver）
    // ========================================================
    function initChapterHighlight() {
        if (!els.chapters.length || !('IntersectionObserver' in window)) return;

        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    var chapterId = entry.target.id;
                    var chapterNum = chapterId.replace('chapter-', '');
                    var activeLink = document.querySelector('.toc-link[data-chapter="' + chapterNum + '"]');

                    if (activeLink && state.activeChapter !== chapterNum) {
                        state.activeChapter = chapterNum;
                        highlightTocLink(activeLink);
                    }
                }
            });
        }, {
            rootMargin: '-' + CONFIG.navbarHeight + 'px 0px -60% 0px',
            threshold: 0
        });

        els.chapters.forEach(function (chapter) {
            observer.observe(chapter);
        });
    }

    // ========================================================
    //  5. 底部操作栏显隐
    // ========================================================
    function updateActionbarVisibility() {
        if (!els.actionbar) return;

        var scrollTop = window.pageYOffset || document.documentElement.scrollTop;

        if (scrollTop > CONFIG.actionbarShowOffset) {
            els.actionbar.classList.add('report-actionbar--visible');
        } else {
            els.actionbar.classList.remove('report-actionbar--visible');
        }
    }

    // ========================================================
    //  6. 返回顶部
    // ========================================================
    function initBackToTop() {
        if (!els.backToTopBtn) return;

        els.backToTopBtn.addEventListener('click', function () {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
            trackEvent('back_to_top_click');
        });
    }

    // ========================================================
    //  7. 返回按钮
    // ========================================================
    function initBackBtn() {
        if (!els.backBtn) return;

        els.backBtn.addEventListener('click', function () {
            if (window.history.length > 1) {
                window.history.back();
            } else {
                window.location.href = '/result-free/';
            }
        });
    }

    // ========================================================
    //  8. 分享报告
    // ========================================================
    function initShare() {
        if (!els.shareBtn) return;

        els.shareBtn.addEventListener('click', function () {
            var shareData = {
                title: '我的职业人格深度报告 — ' + CONFIG.code + ' ' + CONFIG.title,
                text: '我刚完成了职业性格测试，获得了万字级深度报告！来测测你的吧～',
                url: window.location.href
            };

            trackEvent('report_share_click', { code: CONFIG.code });

            // 优先使用 Web Share API
            if (navigator.share) {
                navigator.share(shareData).then(function () {
                    trackEvent('report_share_success', { method: 'native' });
                }).catch(function () {
                    // 用户取消分享，不做处理
                });
            } else if (navigator.clipboard) {
                // 降级：复制链接到剪贴板
                navigator.clipboard.writeText(window.location.href).then(function () {
                    showToast('报告链接已复制，快去分享给好友吧');
                    trackEvent('report_share_success', { method: 'clipboard' });
                }).catch(function () {
                    // 最终降级
                    promptCopyFallback(window.location.href);
                });
            } else {
                promptCopyFallback(window.location.href);
            }
        });
    }

    function promptCopyFallback(url) {
        var input = document.createElement('input');
        input.value = url;
        input.style.position = 'fixed';
        input.style.opacity = '0';
        document.body.appendChild(input);
        input.select();
        try {
            document.execCommand('copy');
            showToast('报告链接已复制，快去分享给好友吧');
        } catch (err) {
            showToast('请手动复制链接分享');
        }
        input.remove();
    }

    // ========================================================
    //  9. 阅读时长追踪
    // ========================================================
    function initReadingDuration() {
        // 读取已累计时长（支持跨设备/跨会话）
        var saved = localStorage.getItem(CONFIG.durationKey);
        state.accumulatedDuration = saved ? parseInt(saved, 10) || 0 : 0;

        // 记录本次开始时间
        state.readStart = Date.now();

        // 每分钟更新显示
        setInterval(function () {
            updateDuration();
        }, 60000);

        // 页面卸载时保存
        window.addEventListener('beforeunload', function () {
            updateDuration(true);
        });

        // 页面可见性变化 — 后台不计入时长
        document.addEventListener('visibilitychange', function () {
            if (document.hidden) {
                // 页面隐藏，保存当前累计
                updateDuration(true);
                state.readStart = null;
            } else {
                // 页面恢复，重新计时
                state.readStart = Date.now();
            }
        });

        // 首次显示
        updateDuration();
    }

    function updateDuration(save) {
        if (state.readStart === null) return;

        var sessionDuration = Math.floor((Date.now() - state.readStart) / 1000); // 秒
        var totalSeconds = state.accumulatedDuration + sessionDuration;
        var displayMinutes = Math.max(1, Math.floor(totalSeconds / 60));

        if (els.readDuration) {
            if (displayMinutes < 60) {
                els.readDuration.textContent = '阅读时长：' + displayMinutes + ' 分钟';
            } else {
                var hours = Math.floor(displayMinutes / 60);
                var mins = displayMinutes % 60;
                els.readDuration.textContent = '阅读时长：' + hours + ' 小时 ' + mins + ' 分钟';
            }
        }

        if (save) {
            state.accumulatedDuration = totalSeconds;
            localStorage.setItem(CONFIG.durationKey, String(state.accumulatedDuration));
            // 重置本次开始时间
            state.readStart = Date.now();
        }
    }

    // ========================================================
    // 10. 滚动至底部埋点
    // ========================================================
    function checkBottomReached() {
        if (state.bottomTracked) return;

        var scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        var scrollHeight = document.documentElement.scrollHeight;
        var windowHeight = window.innerHeight;

        // 滚动到底部（允许 50px 误差）
        if (scrollTop + windowHeight >= scrollHeight - 50) {
            state.bottomTracked = true;
            trackEvent('report_read_complete', {
                code: CONFIG.code,
                duration: Math.floor((Date.now() - (state.readStart || Date.now())) / 1000)
            });

            // 报告结尾卡片高亮动画
            if (els.reportEnd) {
                els.reportEnd.classList.add('report-end--reached');
            }
        }
    }

    // ========================================================
    // 11. 阅读进度自动保存与恢复
    // ========================================================
    function initScrollProgress() {
        // 恢复上次阅读位置
        var savedScroll = localStorage.getItem(CONFIG.scrollRestoreKey);
        if (savedScroll) {
            var scrollPos = parseInt(savedScroll, 10);
            if (scrollPos > 100) {
                // 延迟执行，等待页面完全渲染
                setTimeout(function () {
                    window.scrollTo(0, scrollPos);
                    showToast('已恢复上次阅读位置');
                }, 300);
            }
        }

        // 节流保存滚动位置
        var saveTimer = null;
        window.addEventListener('scroll', function () {
            if (saveTimer) return;
            saveTimer = setTimeout(function () {
                var scrollTop = window.pageYOffset || document.documentElement.scrollTop;
                localStorage.setItem(CONFIG.scrollRestoreKey, String(scrollTop));
                saveTimer = null;
            }, 800);
        }, { passive: true });
    }

    // ========================================================
    // 12. 行动清单勾选状态持久化
    // ========================================================
    function initActionChecklist() {
        if (!els.actionItems.length) return;

        // 恢复已勾选状态
        var saved = localStorage.getItem(CONFIG.checklistKey);
        var checkedSet = new Set();
        if (saved) {
            try {
                checkedSet = new Set(JSON.parse(saved));
            } catch (e) {
                // ignore parse error
            }
        }

        els.actionItems.forEach(function (item, index) {
            if (checkedSet.has(index)) {
                item.checked = true;
            }

            item.addEventListener('change', function () {
                var currentSet = new Set();
                els.actionItems.forEach(function (cb, i) {
                    if (cb.checked) currentSet.add(i);
                });
                localStorage.setItem(CONFIG.checklistKey, JSON.stringify(Array.from(currentSet)));

                // 全部完成时埋点
                if (currentSet.size === els.actionItems.length) {
                    trackEvent('checklist_all_complete', {
                        code: CONFIG.code,
                        total: els.actionItems.length
                    });
                    showToast('90 天行动计划已全部完成，恭喜你！');
                }
            });
        });
    }

    // ========================================================
    // 13. 滚动事件统一处理（节流）
    // ========================================================
    function initScrollHandler() {
        var ticking = false;

        window.addEventListener('scroll', function () {
            if (!ticking) {
                requestAnimationFrame(function () {
                    updateReadingProgress();
                    updateActionbarVisibility();
                    checkBottomReached();
                    ticking = false;
                });
                ticking = true;
            }
        }, { passive: true });
    }

    // ========================================================
    // 工具函数
    // ========================================================
    function trackEvent(eventName, data) {
        if (typeof API !== 'undefined' && API.trackEvent) {
            API.trackEvent(eventName, data || {}, 'deep_report');
        }
    }

    function showToast(message) {
        var toast = document.createElement('div');
        toast.style.cssText = 'position:fixed;bottom:30%;left:50%;transform:translateX(-50%);' +
            'background:rgba(0,0,0,0.75);color:#fff;padding:12px 24px;border-radius:24px;' +
            'font-size:14px;z-index:9999;pointer-events:none;' +
            'animation:drFadeIn 0.3s ease;white-space:nowrap;max-width:90vw;';

        // 注入动画样式（仅一次）
        if (!document.getElementById('dr-toast-style')) {
            var style = document.createElement('style');
            style.id = 'dr-toast-style';
            style.textContent = '@keyframes drFadeIn{from{opacity:0;transform:translateX(-50%) translateY(10px)}to{opacity:1;transform:translateX(-50%) translateY(0)}}';
            document.head.appendChild(style);
        }

        toast.textContent = message;
        document.body.appendChild(toast);

        setTimeout(function () {
            toast.style.opacity = '0';
            toast.style.transition = 'opacity 0.3s';
            setTimeout(function () {
                if (toast.parentNode) toast.remove();
            }, 300);
        }, 2500);
    }

    // ========================================================
    // 报告加载（检查付费状态，动态填充数据）
    // ========================================================

    // 从 URL 参数获取 assessment_id
    function getAssessmentId() {
        var params = new URLSearchParams(window.location.search);
        var id = params.get('assessment_id') || params.get('session_token') || '';
        if (id) return id;

        // 从 localStorage 获取
        if (typeof API !== 'undefined' && API.getSessionToken) {
            id = API.getSessionToken();
            if (id) return id;
        }
        try {
            id = localStorage.getItem('last_assessment_id') || '';
        } catch (e) {
            id = '';
        }
        return id;
    }

    // 刷新 DOM 引用（动态渲染后需要重新查询）
    function refreshEls() {
        els.tocLinks = document.querySelectorAll('.toc-link');
        els.tocModuleLinks = document.querySelectorAll('.toc-module-link');
        els.chapters = document.querySelectorAll('.report-chapter');
        els.actionItems = document.querySelectorAll('.action-item input[type="checkbox"]');
        els.reportEnd = document.querySelector('.report-end');
    }

    // 更新 localStorage key 为按 assessment_id 区分
    function updateStorageKeys() {
        var suffix = state.assessmentId ? '_' + state.assessmentId : '';
        CONFIG.scrollRestoreKey = 'deep_report_scroll' + suffix;
        CONFIG.checklistKey = 'deep_report_checklist' + suffix;
        CONFIG.readStartKey = 'deep_report_read_start' + suffix;
        CONFIG.durationKey = 'deep_report_duration' + suffix;
    }

    // 动态渲染报告标题区
    function renderReportHeader(data) {
        // 填充画像名和 RIASEC 码
        var codeEl = document.querySelector('.report-header__code');
        var titleEl = document.querySelector('.report-header__title');
        var sloganEl = document.querySelector('.report-header__slogan');

        if (data.code) {
            CONFIG.code = data.code;
            if (codeEl) codeEl.textContent = data.code;
        }
        if (data.title || data.archetype_name) {
            CONFIG.title = data.title || data.archetype_name;
            if (titleEl) titleEl.textContent = CONFIG.title;
        }
        if (data.slogan && sloganEl) {
            sloganEl.textContent = data.slogan;
        }

        // 更新页面标题
        if (data.code) {
            document.title = '深度报告 · ' + data.code + ' | 画己职测';
        }
    }

    // 根据 API 返回的 chapters 动态生成目录导航
    function renderTocNav(chapters) {
        if (!chapters || !chapters.length) return;
        var navEl = document.querySelector('.report-toc-drawer__nav');
        if (!navEl) return;

        var html = chapters.map(function (ch, i) {
            var num = String(ch.number || (i + 1)).padStart(2, '0');
            var title = ch.title || ('第 ' + (i + 1) + ' 章');
            var highlight = ch.highlight ? ' toc-link--highlight' : '';
            return '<a href="#chapter-' + (ch.number || (i + 1)) + '" class="toc-link' + highlight + '" data-chapter="' + (ch.number || (i + 1)) + '">' +
                '<span class="toc-link__num">' + num + '</span>' +
                '<span class="toc-link__text">' + title + '</span>' +
                '</a>';
        }).join('');

        navEl.innerHTML = html;
    }

    // 根据 API 返回的 chapters 动态更新章节标题
    function renderChapters(chapters) {
        if (!chapters || !chapters.length) return;

        chapters.forEach(function (ch, i) {
            var num = ch.number || (i + 1);
            var chapterEl = document.getElementById('chapter-' + num);
            if (!chapterEl) return;

            // 更新章节标题
            if (ch.title) {
                var titleEl = chapterEl.querySelector('.chapter-marker__title');
                if (titleEl) titleEl.textContent = ch.title;
            }

            // 如果有 HTML 内容，替换章节正文
            if (ch.html) {
                var bodyEl = chapterEl.querySelector('.chapter-body');
                if (bodyEl) bodyEl.innerHTML = ch.html;
            }
        });
    }

    function loadReport() {
        state.assessmentId = getAssessmentId();

        if (!state.assessmentId) {
            // 没有找到 assessment_id，跳转到首页
            showToast('未找到测评记录，请先完成测评');
            setTimeout(function () {
                window.location.href = '/';
            }, 2000);
            return;
        }

        // 更新 localStorage key
        updateStorageKeys();

        // 如果 API 不可用，使用静态内容初始化
        if (typeof API === 'undefined' || !API.getDeepReport) {
            initInteractions();
            return;
        }

        API.getDeepReport(state.assessmentId).then(function (data) {
            if (!data) {
                initInteractions();
                return;
            }

            // 检查付费状态
            if (data.is_paid === false) {
                // 未付费，重定向到支付页
                showToast('请先解锁深度报告');
                setTimeout(function () {
                    window.location.href = '/payment/?assessment_id=' + encodeURIComponent(state.assessmentId);
                }, 1500);
                return;
            }

            // 已付费，渲染报告
            state.reportLoaded = true;
            renderReportHeader(data);

            // 动态渲染目录和章节
            if (data.chapters && data.chapters.length) {
                renderTocNav(data.chapters);
                renderChapters(data.chapters);
            }

            // 刷新 DOM 引用并初始化交互
            refreshEls();
            initInteractions();
        }).catch(function () {
            // API 失败时使用静态内容初始化（降级）
            initInteractions();
        });
    }

    // ========================================================
    // 初始化交互（报告加载后调用）
    // ========================================================
    function initInteractions() {
        initTocDrawer();
        initAnchorNav();
        initChapterHighlight();
        initBackToTop();
        initBackBtn();
        initShare();
        initReadingDuration();
        initScrollProgress();
        initActionChecklist();
        initScrollHandler();

        // 初次更新进度条和操作栏
        updateReadingProgress();
        updateActionbarVisibility();

        // 页面加载埋点
        trackEvent('report_page_view', { code: CONFIG.code });
    }

    // ========================================================
    // 初始化入口
    // ========================================================
    function init() {
        loadReport();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
