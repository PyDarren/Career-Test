/* ==========================================================================
   职探 - Main JavaScript
   MBTI 职业性格测评 · 通用工具与模块初始化
   ========================================================================== */

(function () {
    'use strict';

    /* ----------------------------------------------------------------------
       Utility Functions
       ---------------------------------------------------------------------- */

    /**
     * 生成 UUID v4
     * @returns {string} 格式如 xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
     */
    function generateUUID() {
        if (typeof crypto !== 'undefined' && crypto.randomUUID) {
            return crypto.randomUUID();
        }
        // Fallback: 手动生成
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
            var r = (Math.random() * 16) | 0;
            var v = c === 'x' ? r : (r & 0x3) | 0x8;
            return v.toString(16);
        });
    }

    /**
     * 从 localStorage 安全读取 JSON 值
     * @param {string} key - 存储键名
     * @returns {*} 解析后的值，读取失败返回 null
     */
    function getLocalStorage(key) {
        try {
            var raw = localStorage.getItem(key);
            if (raw === null) return null;
            return JSON.parse(raw);
        } catch (e) {
            console.warn('[职探] localStorage 读取失败:', key, e);
            return null;
        }
    }

    /**
     * 向 localStorage 安全写入 JSON 值
     * @param {string} key - 存储键名
     * @param {*} value - 要存储的值（会被 JSON.stringify）
     * @returns {boolean} 是否写入成功
     */
    function setLocalStorage(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
            return true;
        } catch (e) {
            console.warn('[职探] localStorage 写入失败:', key, e);
            return false;
        }
    }

    /**
     * 从 localStorage 删除指定键
     * @param {string} key - 存储键名
     */
    function removeLocalStorage(key) {
        try {
            localStorage.removeItem(key);
            return true;
        } catch (e) {
            console.warn('[职探] localStorage 删除失败:', key, e);
            return false;
        }
    }

    /**
     * 节流函数
     * @param {Function} fn - 要节流的函数
     * @param {number} delay - 延迟毫秒
     * @returns {Function} 节流后的函数
     */
    function throttle(fn, delay) {
        var lastCall = 0;
        return function () {
            var now = Date.now();
            if (now - lastCall >= delay) {
                lastCall = now;
                return fn.apply(this, arguments);
            }
        };
    }

    /**
     * 防抖函数
     * @param {Function} fn - 要防抖的函数
     * @param {number} delay - 延迟毫秒
     * @returns {Function} 防抖后的函数
     */
    function debounce(fn, delay) {
        var timer = null;
        return function () {
            var context = this;
            var args = arguments;
            clearTimeout(timer);
            timer = setTimeout(function () {
                fn.apply(context, args);
            }, delay);
        };
    }

    /**
     * 查询选择器简写
     * @param {string} selector - CSS 选择器
     * @param {Element} [parent=document] - 父元素
     * @returns {Element|null}
     */
    function $(selector, parent) {
        return (parent || document).querySelector(selector);
    }

    /**
     * 查询选择器全部简写
     * @param {string} selector - CSS 选择器
     * @param {Element} [parent=document] - 父元素
     * @returns {NodeList}
     */
    function $$(selector, parent) {
        return (parent || document).querySelectorAll(selector);
    }

    /* ----------------------------------------------------------------------
       Storage Keys
       ---------------------------------------------------------------------- */
    var STORAGE_KEYS = {
        USER_ID: 'caretest_user_id',
        ASSESSMENT_PROGRESS: 'caretest_assessment_progress',
        ASSESSMENT_ANSWERS: 'caretest_assessment_answers',
        RESULT_TYPE: 'caretest_result_type',
        PAID_REPORT: 'caretest_paid_report',
        SETTINGS: 'caretest_settings'
    };

    /* ----------------------------------------------------------------------
       Assessment Module (Placeholder)
       ---------------------------------------------------------------------- */
    var AssessmentModule = {
        totalQuestions: 48,
        currentQuestion: 0,
        answers: [],

        init: function () {
            // 恢复进度
            var saved = getLocalStorage(STORAGE_KEYS.ASSESSMENT_ANSWERS);
            if (saved && Array.isArray(saved)) {
                this.answers = saved;
                this.currentQuestion = saved.length;
            }
            // TODO: 加载题目数据并渲染第一题
            console.info('[职探] Assessment 模块已初始化, 当前进度:', this.currentQuestion + '/' + this.totalQuestions);
        },

        /**
         * 记录答案并自动前进
         * @param {number} questionIndex - 题目索引
         * @param {number} scaleValue - 量表值 (1-6)
         */
        recordAnswer: function (questionIndex, scaleValue) {
            this.answers[questionIndex] = scaleValue;
            setLocalStorage(STORAGE_KEYS.ASSESSMENT_ANSWERS, this.answers);
            // TODO: 自动前进到下一题或提交
        },

        /**
         * 更新进度条
         */
        updateProgress: function () {
            var fill = $('.progress-bar-fill');
            var text = $('.progress-text .progress-current');
            if (fill) {
                var pct = (this.currentQuestion / this.totalQuestions) * 100;
                fill.style.width = pct + '%';
            }
            if (text) {
                text.textContent = this.currentQuestion;
            }
        },

        /**
         * 提交测评答案，获取结果
         */
        submit: function () {
            // TODO: 发送到后端评分或前端降级评分
            console.info('[职探] 测评提交, 共', this.answers.length, '题');
        }
    };

    /* ----------------------------------------------------------------------
       Tracking Module (Placeholder)
       ---------------------------------------------------------------------- */
    var TrackingModule = {
        userId: null,

        init: function () {
            // 获取或生成用户 ID
            this.userId = getLocalStorage(STORAGE_KEYS.USER_ID);
            if (!this.userId) {
                this.userId = generateUUID();
                setLocalStorage(STORAGE_KEYS.USER_ID, this.userId);
            }
            console.info('[职探] Tracking 模块已初始化, UserID:', this.userId);
        },

        /**
         * 发送埋点事件
         * @param {string} eventName - 事件名称
         * @param {Object} [properties] - 事件属性
         */
        track: function (eventName, properties) {
            var data = {
                event: eventName,
                user_id: this.userId,
                timestamp: Date.now(),
                properties: properties || {}
            };
            // TODO: 发送到后端统计接口 (navigator.sendBeacon)
            console.debug('[职探] Track:', data);
        }
    };

    /* ----------------------------------------------------------------------
       UI Module - 全局交互
       ---------------------------------------------------------------------- */
    var UIModule = {
        init: function () {
            this.initMobileNav();
            this.initFAQ();
            this.initScaleSelector();
            this.initReportNav();
            this.initSettingsModal();
            this.initFeedback();
        },

        /* 移动端导航栏切换 */
        initMobileNav: function () {
            var toggle = $('.nav-toggle');
            var links = $('#nav-links');
            if (!toggle || !links) return;

            toggle.addEventListener('click', function () {
                var expanded = toggle.getAttribute('aria-expanded') === 'true';
                toggle.setAttribute('aria-expanded', !expanded);
                links.classList.toggle('active');
            });
        },

        /* FAQ 折叠 */
        initFAQ: function () {
            var items = $$('.faq-item');
            if (!items.length) return;

            items.forEach(function (item) {
                var question = $('.faq-question', item);
                if (!question) return;
                question.addEventListener('click', function () {
                    item.classList.toggle('open');
                });
            });
        },

        /* 量表选择器交互 */
        initScaleSelector: function () {
            var container = $('.scale-container');
            if (!container) return;

            var dots = $$('.scale-dot', container);
            dots.forEach(function (dot) {
                dot.addEventListener('click', function () {
                    // 移除其他选中
                    dots.forEach(function (d) { d.classList.remove('selected'); });
                    dot.classList.add('selected');

                    var value = parseInt(dot.dataset.value, 10);
                    // 触发回调
                    if (typeof window.onScaleSelect === 'function') {
                        window.onScaleSelect(value);
                    }
                });
            });
        },

        /* 报告页侧边栏导航高亮 */
        initReportNav: function () {
            var navLinks = $$('.report-nav a');
            var chapters = $$('.report-chapter');
            if (!navLinks.length || !chapters.length) return;

            // 使用 IntersectionObserver 实现滚动高亮
            if ('IntersectionObserver' in window) {
                var observer = new IntersectionObserver(function (entries) {
                    entries.forEach(function (entry) {
                        if (entry.isIntersecting) {
                            var id = entry.target.id;
                            navLinks.forEach(function (link) {
                                var isActive = link.getAttribute('href') === '#' + id;
                                link.classList.toggle('active', isActive);
                            });
                        }
                    });
                }, { rootMargin: '-80px 0px -70% 0px' });

                chapters.forEach(function (ch) { observer.observe(ch); });
            }
        },

        /* 设置页 - 清除数据确认弹窗 */
        initSettingsModal: function () {
            var triggerBtn = $('#clear-data-btn');
            var modal = $('#clear-data-modal');
            if (!triggerBtn || !modal) return;

            var cancelBtn = $('.modal-cancel', modal);
            var confirmBtn = $('.modal-confirm', modal);

            triggerBtn.addEventListener('click', function () {
                modal.classList.add('active');
            });

            function closeModal() {
                modal.classList.remove('active');
            }

            if (cancelBtn) {
                cancelBtn.addEventListener('click', closeModal);
            }

            modal.addEventListener('click', function (e) {
                if (e.target === modal) closeModal();
            });

            if (confirmBtn) {
                confirmBtn.addEventListener('click', function () {
                    // 清除所有本地数据
                    Object.keys(STORAGE_KEYS).forEach(function (key) {
                        removeLocalStorage(STORAGE_KEYS[key]);
                    });
                    closeModal();
                    // 显示成功提示
                    alert('数据已清除');
                    // 刷新页面
                    window.location.reload();
                });
            }
        },

        /* 报告页反馈 */
        initFeedback: function () {
            var feedbackBtns = $$('.feedback-btn');
            var feedbackInput = $('.feedback-input');
            var feedbackSubmit = $('.feedback-submit');

            if (!feedbackBtns.length) return;

            feedbackBtns.forEach(function (btn) {
                btn.addEventListener('click', function () {
                    feedbackBtns.forEach(function (b) { b.classList.remove('active'); });
                    btn.classList.add('active');
                });
            });

            if (feedbackSubmit) {
                feedbackSubmit.addEventListener('click', function () {
                    var rating = $('.feedback-btn.active');
                    var type = rating ? rating.dataset.rating : null;
                    var text = feedbackInput ? feedbackInput.value : '';
                    // TODO: 发送反馈
                    TrackingModule.track('report_feedback', { rating: type, text: text });
                    alert('感谢您的反馈！');
                });
            }
        }
    };

    /* ----------------------------------------------------------------------
       Page Initialization
       ---------------------------------------------------------------------- */
    function initPage() {
        var body = document.body;
        var pageType = body.dataset.page || '';

        // 初始化通用模块
        TrackingModule.init();
        UIModule.init();

        // 根据页面类型初始化对应模块
        switch (pageType) {
            case 'assessment':
                AssessmentModule.init();
                AssessmentModule.updateProgress();
                break;
            case 'home':
                TrackingModule.track('page_view', { page: 'home' });
                break;
            case 'result':
                TrackingModule.track('page_view', { page: 'result' });
                break;
            case 'report':
                TrackingModule.track('page_view', { page: 'report' });
                break;
            default:
                break;
        }

        console.info('[职探] 页面初始化完成:', pageType || 'default');
    }

    /* ----------------------------------------------------------------------
       DOM Ready
       ---------------------------------------------------------------------- */
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initPage);
    } else {
        initPage();
    }

    /* ----------------------------------------------------------------------
       Export Public API
       ---------------------------------------------------------------------- */
    window.CareTest = {
        generateUUID: generateUUID,
        getLocalStorage: getLocalStorage,
        setLocalStorage: setLocalStorage,
        removeLocalStorage: removeLocalStorage,
        throttle: throttle,
        debounce: debounce,
        STORAGE_KEYS: STORAGE_KEYS,
        Assessment: AssessmentModule,
        Tracking: TrackingModule
    };

})();
