/**
 * payment.js — 深度报告预览与支付页交互脚本
 * 功能：优惠券验证、支付方式切换、订单创建、支付状态轮询、跳转
 */

(function () {
    'use strict';

    // ============== 配置 ==============
    var config = {
        originalPrice: 9.90,
        currentPrice: 2.99,
        // 轮询配置
        pollInterval: 2000,   // 2 秒
        pollMaxCount: 30,     // 最多 30 次 = 60 秒
        // 支付成功跳转
        redirectUrl: '/deep-report/'
    };

    var state = {
        selectedMethod: 'wechat',
        couponCode: null,
        couponDiscount: 0,
        finalPrice: config.currentPrice,
        isPaying: false,
        pollTimer: null,
        pollCount: 0,
        orderId: null,
        assessmentId: null
    };

    // ============== DOM 元素引用 ==============
    var els = {
        payBtn: document.getElementById('payBtn'),
        payBtnText: document.getElementById('payBtnText'),
        payStatus: document.getElementById('payStatus'),
        payStatusText: document.getElementById('payStatusText'),
        priceAmount: document.getElementById('priceAmount'),
        discountDisplay: document.getElementById('discountDisplay'),
        couponInput: document.getElementById('couponInput'),
        couponApplyBtn: document.getElementById('couponApplyBtn'),
        couponHint: document.getElementById('couponHint'),
        payMethods: document.querySelectorAll('.pay-method')
    };

    // ============== 1. 支付方式切换 ==============
    function initPayMethodSwitch() {
        if (!els.payMethods.length) return;

        els.payMethods.forEach(function (method) {
            method.addEventListener('click', function () {
                els.payMethods.forEach(function (m) { m.classList.remove('pay-method--active'); });
                method.classList.add('pay-method--active');

                var radio = method.querySelector('input[type="radio"]');
                if (radio) {
                    radio.checked = true;
                    state.selectedMethod = radio.value;
                }
            });
        });
    }

    // ============== 2. 优惠券验证（后端验证） ==============
    function initCoupon() {
        if (!els.couponApplyBtn) return;

        els.couponApplyBtn.addEventListener('click', function () {
            var code = els.couponInput.value.trim().toUpperCase();

            if (!code) {
                updateCouponHint('请输入优惠券码', 'error');
                return;
            }

            // 禁用按钮，防止重复提交
            els.couponApplyBtn.disabled = true;
            els.couponApplyBtn.textContent = '验证中…';
            updateCouponHint('正在验证优惠券…', '');

            API.validateCoupon(code).then(function (res) {
                els.couponApplyBtn.disabled = false;

                if (res && res.valid) {
                    state.couponCode = code;
                    state.couponDiscount = res.discount || 0;
                    // 使用后端返回的最终价格，但确保显示为 2.99 体系
                    state.finalPrice = res.final_price !== undefined
                        ? res.final_price
                        : Math.max(0.01, config.currentPrice - state.couponDiscount);

                    var label = state.couponDiscount > 0
                        ? '优惠 ¥' + state.couponDiscount.toFixed(2)
                        : '优惠券已应用';
                    updateCouponHint('优惠券已应用：' + label, 'success');
                    updatePriceDisplay();
                    els.couponApplyBtn.classList.add('coupon-apply-btn--active');
                    els.couponApplyBtn.textContent = '已使用';

                    trackEvent('coupon_apply', {
                        code: code,
                        discount: state.couponDiscount,
                        final_price: state.finalPrice
                    });
                } else {
                    resetCoupon('优惠券码无效或已过期');
                }
            }).catch(function (err) {
                els.couponApplyBtn.disabled = false;
                resetCoupon(err.message || '优惠券验证失败，请重试');
            });
        });
    }

    function resetCoupon(message) {
        state.couponCode = null;
        state.couponDiscount = 0;
        state.finalPrice = config.currentPrice;

        updateCouponHint(message, 'error');
        updatePriceDisplay();
        els.couponApplyBtn.classList.remove('coupon-apply-btn--active');
        els.couponApplyBtn.textContent = '使用';
    }

    function updateCouponHint(message, type) {
        els.couponHint.textContent = message;
        els.couponHint.className = 'coupon-hint';

        if (type === 'success') {
            els.couponHint.classList.add('coupon-hint--success');
        } else if (type === 'error') {
            els.couponHint.classList.add('coupon-hint--error');
        }
    }

    function updatePriceDisplay() {
        // 更新价格
        els.priceAmount.textContent = state.finalPrice.toFixed(2);

        // 更新折扣显示
        if (state.couponDiscount > 0) {
            els.discountDisplay.textContent = '-¥' + state.couponDiscount.toFixed(2);
            els.discountDisplay.classList.add('price-display__discount--active');
        } else {
            els.discountDisplay.textContent = '无';
            els.discountDisplay.classList.remove('price-display__discount--active');
        }

        // 更新按钮文字
        els.payBtnText.textContent = '解锁完整报告 · ¥' + state.finalPrice.toFixed(2);
    }

    // ============== 3. 支付流程 ==============
    function initPayment() {
        if (!els.payBtn) return;

        els.payBtn.addEventListener('click', function () {
            if (state.isPaying) return;
            startPayment();
        });
    }

    // 从 URL 参数或 localStorage 获取 assessment_id
    function getAssessmentId() {
        // 优先从 URL 参数获取
        var params = new URLSearchParams(window.location.search);
        var id = params.get('assessment_id') || params.get('session_token') || '';
        if (id) return id;

        // 从 localStorage 获取（测评提交后存储的 session_token）
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

    function startPayment() {
        state.isPaying = true;
        els.payBtn.disabled = true;
        els.payStatus.style.display = 'flex';
        els.payStatusText.textContent = '正在创建订单…';

        // 获取测评 ID
        state.assessmentId = getAssessmentId();
        if (!state.assessmentId) {
            showToast('未找到测评记录，请先完成测评', 'error');
            resetPayState();
            return;
        }

        // 埋点
        trackEvent('pay_click', {
            method: state.selectedMethod,
            amount: state.finalPrice,
            coupon: state.couponCode
        });

        // 构建订单数据
        var orderData = {
            payment_channel: state.selectedMethod,
            assessment_id: state.assessmentId
        };
        if (state.couponCode) {
            orderData.coupon_code = state.couponCode;
        }

        // 调用 API 创建订单
        API.createOrder(orderData).then(function (res) {
            state.orderId = res.order_id;

            // 存储 order_id 以备后用
            try {
                localStorage.setItem('current_order_id', res.order_id);
            } catch (e) {}

            els.payStatusText.textContent = '正在调起' + (state.selectedMethod === 'wechat' ? '微信' : '支付宝') + '支付…';

            // 根据返回的支付参数调起支付
            if (res.pay_url) {
                // 生产环境：有支付跳转 URL
                // 开发环境模拟：创建订单后直接进入轮询（模拟支付成功）
                // 如需启用真实跳转，取消下面一行的注释
                // window.location.href = res.pay_url;
            }

            // 进入轮询（开发环境直接轮询，模拟支付成功）
            setTimeout(function () {
                els.payStatusText.textContent = '正在确认订单状态…';
                startPolling(state.orderId);
            }, 1000);
        }).catch(function (err) {
            showToast('创建订单失败：' + (err.message || '请重试'), 'error');
            resetPayState();
        });
    }

    function resetPayState() {
        state.isPaying = false;
        state.orderId = null;
        els.payBtn.disabled = false;
        els.payStatus.style.display = 'none';
    }

    // ============== 4. 订单状态轮询（调用 API） ==============
    function startPolling(orderId) {
        state.pollCount = 0;

        // 清除已有定时器
        if (state.pollTimer) {
            clearTimeout(state.pollTimer);
        }

        function pollOnce() {
            state.pollCount++;

            API.getOrderStatus(orderId).then(function (res) {
                if (res && res.status === 'paid') {
                    clearPollTimer();
                    onPaySuccess(res);
                    return;
                }

                if (res && (res.status === 'expired' || res.status === 'failed')) {
                    clearPollTimer();
                    onPayError(res.status);
                    return;
                }

                // 继续轮询
                if (state.pollCount >= config.pollMaxCount) {
                    clearPollTimer();
                    onPayTimeout();
                } else {
                    // 更新状态文字
                    var dots = '.'.repeat(state.pollCount % 4);
                    els.payStatusText.textContent = '等待支付确认' + dots;
                    state.pollTimer = setTimeout(pollOnce, config.pollInterval);
                }
            }).catch(function () {
                // 网络错误时继续轮询（不消耗次数）
                if (state.pollCount >= config.pollMaxCount) {
                    clearPollTimer();
                    onPayTimeout();
                } else {
                    state.pollTimer = setTimeout(pollOnce, config.pollInterval);
                }
            });
        }

        // 首次轮询
        state.pollTimer = setTimeout(pollOnce, config.pollInterval);
    }

    function clearPollTimer() {
        if (state.pollTimer) {
            clearTimeout(state.pollTimer);
            state.pollTimer = null;
        }
    }

    function onPayError(status) {
        els.payStatus.style.display = 'none';
        resetPayState();

        var msg = status === 'expired' ? '订单已过期，请重新支付' : '支付失败，请重试';
        showToast(msg, 'error');

        trackEvent('pay_error', {
            method: state.selectedMethod,
            amount: state.finalPrice,
            status: status
        });
    }

    function onPaySuccess(payRes) {
        els.payStatusText.textContent = '支付成功！正在跳转到报告…';
        els.payStatus.style.display = 'none';

        // 显示成功提示
        showToast('支付成功！正在解锁报告…', 'success');

        // 埋点
        trackEvent('pay_success', {
            method: state.selectedMethod,
            amount: state.finalPrice,
            coupon: state.couponCode,
            order_id: state.orderId
        });

        // 延迟跳转，携带 assessment_id
        setTimeout(function () {
            var redirectUrl = config.redirectUrl;
            if (state.assessmentId) {
                redirectUrl += '?assessment_id=' + encodeURIComponent(state.assessmentId);
            }
            window.location.href = redirectUrl;
        }, 1500);
    }

    function onPayTimeout() {
        els.payStatus.style.display = 'none';
        resetPayState();

        showToast('支付超时，如已扣款请联系客服', 'error');

        // 埋点
        trackEvent('pay_timeout', {
            method: state.selectedMethod,
            amount: state.finalPrice,
            order_id: state.orderId
        });
    }

    // ============== 工具函数 ==============
    function trackEvent(eventName, data) {
        if (typeof API !== 'undefined' && API.trackEvent) {
            API.trackEvent(eventName, data, 'payment');
        }
    }

    function showToast(message, type) {
        var toast = document.createElement('div');
        var bg = type === 'success' ? 'rgba(94, 166, 126, 0.9)' : type === 'error' ? 'rgba(225, 112, 85, 0.9)' : 'rgba(0, 0, 0, 0.75)';
        toast.style.cssText = 'position:fixed;bottom:30%;left:50%;transform:translateX(-50%);background:' + bg + ';color:#fff;padding:14px 28px;border-radius:24px;font-size:14px;z-index:9999;pointer-events:none;animation:fadeInUp 0.3s ease;max-width:80%;text-align:center;';
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(function () {
            toast.style.opacity = '0';
            toast.style.transition = 'opacity 0.3s';
            setTimeout(function () { toast.remove(); }, 300);
        }, 2500);
    }

    // ============== 初始化 ==============
    function init() {
        initPayMethodSwitch();
        initCoupon();
        initPayment();

        // 页面加载埋点
        trackEvent('payment_page_view', {
            originalPrice: config.originalPrice,
            currentPrice: config.currentPrice
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
