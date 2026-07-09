/* ==========================================================================
   职探 - Tracking SDK
   前端埋点系统，17 个事件覆盖用户全流程行为。
   批量上报：每 5 条或页面隐藏时发送，使用 sendBeacon。
   ========================================================================== */

(function () {
    'use strict';

    /* ----------------------------------------------------------------------
       Storage Keys (统一 localStorage 键名规范)
       ---------------------------------------------------------------------- */
    var STORAGE_KEYS = {
        CT_UUID: 'ct_uuid',                    // 永久 - 匿名用户标识
        CT_ASSESSMENT_PROGRESS: 'ct_assessment_progress',  // 7 天 - 测评进度
        CT_LAST_RESULT: 'ct_last_result',      // 会话级 - 最近测评结果
        CT_PAID_REPORTS: 'ct_paid_reports',    // 90 天 - 已购买报告
        CT_REFERRER_TYPE: 'ct_referrer_type',  // 会话级 - 分享来源
        CT_SETTINGS: 'ct_settings'             // 永久 - 用户偏好
    };

    /* ----------------------------------------------------------------------
       Event Names (17 个事件)
       ---------------------------------------------------------------------- */
    var EVENTS = {
        PAGE_VIEW: 'page_view',
        ASSESSMENT_START: 'assessment_start',
        ASSESSMENT_ANSWER: 'assessment_answer',
        ASSESSMENT_PAUSE: 'assessment_pause',
        ASSESSMENT_RESUME: 'assessment_resume',
        ASSESSMENT_SUBMIT: 'assessment_submit',
        RESULT_VIEW: 'result_view',
        CAREER_CLICK: 'career_click',
        CAREER_FEEDBACK: 'career_feedback',
        SHARE_CLICK: 'share_click',
        SHARE_SUCCESS: 'share_success',
        PAYMENT_CLICK: 'payment_click',
        PAYMENT_SUCCESS: 'payment_success',
        PAYMENT_FAIL: 'payment_fail',
        REPORT_VIEW: 'report_view',
        REPORT_SCROLL: 'report_scroll',
        REPORT_FEEDBACK: 'report_feedback',
        REFERRAL_LANDING: 'referral_landing'
    };

    /* ----------------------------------------------------------------------
       Tracker Module
       ---------------------------------------------------------------------- */
    var Tracker = {
        // 批量上报队列
        queue: [],
        // 批量上报阈值
        batchSize: 5,
        // 上报接口
        endpoint: '/api/track/',
        // 用户 UUID
        uuid: null,
        // 是否已初始化
        initialized: false,

        /**
         * 初始化 Tracker
         */
        init: function () {
            if (this.initialized) return;

            // 获取或生成 UUID
            this.uuid = this._getUUID();

            // 注册页面卸载事件（使用 sendBeacon 发送剩余事件）
            this._registerVisibilityChange();
            this._registerBeforeUnload();

            this.initialized = true;
            console.info('[职探] Tracker 已初始化, UUID:', this.uuid);
        },

        /**
         * 追踪事件
         * @param {string} eventName - 事件名称（使用 EVENTS 常量）
         * @param {Object} [eventData] - 事件数据
         */
        track: function (eventName, eventData) {
            if (!eventName) return;

            var event = {
                event_name: eventName,
                uuid: this.uuid,
                event_data: eventData || {},
                timestamp: Date.now()
            };

            this.queue.push(event);

            // 达到批量阈值时发送
            if (this.queue.length >= this.batchSize) {
                this.flush();
            }
        },

        /**
         * 立即发送所有排队的事件
         */
        flush: function () {
            if (this.queue.length === 0) return;

            var eventsToSend = this.queue.splice(0);

            // 优先使用 sendBeacon（页面卸载时仍可发送）
            if (navigator.sendBeacon) {
                var blob = new Blob(
                    [JSON.stringify(eventsToSend)],
                    { type: 'application/json' }
                );
                var success = navigator.sendBeacon(this.endpoint, blob);
                if (success) return;
            }

            // Fallback: 使用 fetch
            fetch(this.endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this._getCSRFToken()
                },
                body: JSON.stringify(eventsToSend),
                keepalive: true
            }).catch(function (e) {
                console.warn('[职探] 埋点上报失败:', e);
            });
        },

        /**
         * 获取或生成 UUID
         * @returns {string}
         */
        _getUUID: function () {
            try {
                var stored = localStorage.getItem(STORAGE_KEYS.CT_UUID);
                if (stored) return stored;
            } catch (e) {}

            var uuid;
            if (typeof crypto !== 'undefined' && crypto.randomUUID) {
                uuid = crypto.randomUUID();
            } else {
                uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
                    var r = (Math.random() * 16) | 0;
                    var v = c === 'x' ? r : (r & 0x3) | 0x8;
                    return v.toString(16);
                });
            }

            try {
                localStorage.setItem(STORAGE_KEYS.CT_UUID, uuid);
            } catch (e) {}

            return uuid;
        },

        /**
         * 获取 CSRF Token
         * @returns {string}
         */
        _getCSRFToken: function () {
            var match = document.cookie.match(/csrftoken=([^;]+)/);
            return match ? match[1] : '';
        },

        /**
         * 注册页面可见性变化事件
         */
        _registerVisibilityChange: function () {
            var self = this;
            document.addEventListener('visibilitychange', function () {
                if (document.visibilityState === 'hidden') {
                    self.flush();
                }
            });
        },

        /**
         * 注册页面卸载事件
         */
        _registerBeforeUnload: function () {
            var self = this;
            window.addEventListener('beforeunload', function () {
                self.flush();
            });
        }
    };

    /* ----------------------------------------------------------------------
       Convenience Methods (快捷追踪方法)
       ---------------------------------------------------------------------- */

    /**
     * 追踪页面浏览
     * @param {string} pageName - 页面名称
     */
    Tracker.trackPageView = function (pageName) {
        this.track(EVENTS.PAGE_VIEW, { page: pageName });
    };

    /**
     * 追踪测评开始
     */
    Tracker.trackAssessmentStart = function () {
        this.track(EVENTS.ASSESSMENT_START);
    };

    /**
     * 追踪答题
     * @param {number} questionIndex - 题目索引
     * @param {number} position - 刻度位置 (1-6)
     */
    Tracker.trackAssessmentAnswer = function (questionIndex, position) {
        this.track(EVENTS.ASSESSMENT_ANSWER, {
            question_index: questionIndex,
            position: position
        });
    };

    /**
     * 追踪测评提交
     * @param {string} mbtiType - MBTI 类型
     */
    Tracker.trackAssessmentSubmit = function (mbtiType) {
        this.track(EVENTS.ASSESSMENT_SUBMIT, { mbti_type: mbtiType });
    };

    /**
     * 追踪结果页查看
     * @param {string} mbtiType - MBTI 类型
     */
    Tracker.trackResultView = function (mbtiType) {
        this.track(EVENTS.RESULT_VIEW, { mbti_type: mbtiType });
    };

    /**
     * 追踪职业点击
     * @param {string} careerId - 职业 ID
     * @param {string} careerName - 职业名称
     */
    Tracker.trackCareerClick = function (careerId, careerName) {
        this.track(EVENTS.CAREER_CLICK, {
            career_id: careerId,
            career_name: careerName
        });
    };

    /**
     * 追踪职业反馈
     * @param {string} careerId - 职业 ID
     * @param {string} feedbackType - 反馈类型
     */
    Tracker.trackCareerFeedback = function (careerId, feedbackType) {
        this.track(EVENTS.CAREER_FEEDBACK, {
            career_id: careerId,
            feedback_type: feedbackType
        });
    };

    /**
     * 追踪分享点击
     */
    Tracker.trackShareClick = function () {
        this.track(EVENTS.SHARE_CLICK);
    };

    /**
     * 追踪分享成功
     * @param {string} platform - 分享平台
     */
    Tracker.trackShareSuccess = function (platform) {
        this.track(EVENTS.SHARE_SUCCESS, { platform: platform });
    };

    /**
     * 追踪支付点击
     * @param {string} paymentMethod - 支付方式
     */
    Tracker.trackPaymentClick = function (paymentMethod) {
        this.track(EVENTS.PAYMENT_CLICK, { payment_method: paymentMethod });
    };

    /**
     * 追踪支付成功
     * @param {string} orderNo - 订单号
     */
    Tracker.trackPaymentSuccess = function (orderNo) {
        this.track(EVENTS.PAYMENT_SUCCESS, { order_no: orderNo });
    };

    /**
     * 追踪支付失败
     * @param {string} reason - 失败原因
     */
    Tracker.trackPaymentFail = function (reason) {
        this.track(EVENTS.PAYMENT_FAIL, { reason: reason });
    };

    /**
     * 追踪报告查看
     * @param {string} mbtiType - MBTI 类型
     */
    Tracker.trackReportView = function (mbtiType) {
        this.track(EVENTS.REPORT_VIEW, { mbti_type: mbtiType });
    };

    /**
     * 追踪报告滚动
     * @param {number} chapter - 章节号
     * @param {number} scrollPercent - 滚动百分比
     */
    Tracker.trackReportScroll = function (chapter, scrollPercent) {
        this.track(EVENTS.REPORT_SCROLL, {
            chapter: chapter,
            scroll_percent: scrollPercent
        });
    };

    /**
     * 追踪报告反馈
     * @param {string} rating - up/down
     */
    Tracker.trackReportFeedback = function (rating) {
        this.track(EVENTS.REPORT_FEEDBACK, { rating: rating });
    };

    /**
     * 追踪分享回流落地
     * @param {string} refType - 分享者 MBTI 类型
     */
    Tracker.trackReferralLanding = function (refType) {
        this.track(EVENTS.REFERRAL_LANDING, { ref_type: refType });
    };

    // Export
    window.Tracker = Tracker;
    window.TRACKER_EVENTS = EVENTS;
    window.TRACKER_STORAGE_KEYS = STORAGE_KEYS;

})();
