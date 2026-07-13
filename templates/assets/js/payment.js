/**
 * payment.js — 深度报告预览与支付页交互脚本
 * 功能：优惠券验证、支付方式切换、订单创建、支付状态轮询、跳转
 */

(function () {
    'use strict';

    // ============== 模拟数据（静态页面用，后端接入后替换为 API 返回） ==============
    var config = {
        originalPrice: 9.90,
        currentPrice: 2.99,
        // 模拟优惠券
        coupons: {
            'NEWUSER20': { discount: 20, type: 'percent', label: '8 折优惠' },
            'CAREER10':  { discount: 10, type: 'percent', label: '9 折优惠' },
            'VIP50':     { discount: 50, type: 'percent', label: '5 折优惠' }
        },
        // 轮询配置
        pollInterval: 2000,   // 2 秒
        pollMaxCount: 30,     // 最多 30 次 = 60 秒
        // 支付成功跳转
        redirectUrl: 'deep-report.html',
        // 支付 H5 跳转（模拟）
        wechatPayUrl: 'https://wx.tenpay.com/cgi-bin/mmpayweb-bin/checkmweb',
        alipayUrl: 'https://mclient.alipay.com/cashier/mobilepay.htm'
    };

    var state = {
        selectedMethod: 'wechat',
        couponCode: null,
        couponDiscount: 0,
        finalPrice: config.currentPrice,
        isPaying: false,
        pollTimer: null,
        pollCount: 0
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

    // ============== 2. 优惠券验证 ==============
    function initCoupon() {
        if (!els.couponApplyBtn) return;

        els.couponApplyBtn.addEventListener('click', function () {
            var code = els.couponInput.value.trim().toUpperCase();

            if (!code) {
                updateCouponHint('请输入优惠券码', 'error');
                return;
            }

            // 模拟验证
            var coupon = config.coupons[code];

            if (coupon) {
                state.couponCode = code;

                if (coupon.type === 'amount') {
                    state.couponDiscount = coupon.discount;
                    state.finalPrice = Math.max(0.01, config.currentPrice - coupon.discount);
                } else if (coupon.type === 'percent') {
                    state.couponDiscount = config.currentPrice * (coupon.discount / 100);
                    state.finalPrice = config.currentPrice - state.couponDiscount;
                }

                updateCouponHint('优惠券已应用：' + coupon.label, 'success');
                updatePriceDisplay();
                els.couponApplyBtn.classList.add('coupon-apply-btn--active');
                els.couponApplyBtn.textContent = '已使用';
            } else {
                state.couponCode = null;
                state.couponDiscount = 0;
                state.finalPrice = config.currentPrice;

                updateCouponHint('优惠券码无效或已过期', 'error');
                updatePriceDisplay();
                els.couponApplyBtn.classList.remove('coupon-apply-btn--active');
                els.couponApplyBtn.textContent = '使用';
            }
        });
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

            // 模拟创建订单 + 发起支付
            startPayment();
        });
    }

    function startPayment() {
        state.isPaying = true;
        els.payBtn.disabled = true;
        els.payStatus.style.display = 'flex';
        els.payStatusText.textContent = '正在创建订单…';

        // 埋点
        trackEvent('pay_click', {
            method: state.selectedMethod,
            amount: state.finalPrice,
            coupon: state.couponCode
        });

        // 模拟创建订单（1 秒后）
        setTimeout(function () {
            els.payStatusText.textContent = '正在调起' + (state.selectedMethod === 'wechat' ? '微信' : '支付宝') + '支付…';

            // 模拟跳转到支付 H5 页面
            setTimeout(function () {
                // 在真实环境中，此处应跳转到支付平台 H5
                // window.location.href = state.selectedMethod === 'wechat' ? config.wechatPayUrl : config.alipayUrl;

                // 静态页面模拟：直接进入轮询
                els.payStatusText.textContent = '支付完成？正在确认订单状态…';
                startPolling();
            }, 1500);
        }, 1000);
    }

    // ============== 4. 订单状态轮询 ==============
    function startPolling() {
        state.pollCount = 0;

        // 清除已有定时器
        if (state.pollTimer) {
            clearInterval(state.pollTimer);
        }

        state.pollTimer = setInterval(function () {
            state.pollCount++;

            // 模拟轮询：第 3 次时返回成功
            if (state.pollCount >= 3) {
                clearInterval(state.pollTimer);
                onPaySuccess();
            } else if (state.pollCount >= config.pollMaxCount) {
                // 超时
                clearInterval(state.pollTimer);
                onPayTimeout();
            } else {
                // 更新状态文字
                var dots = '.'.repeat(state.pollCount % 4);
                els.payStatusText.textContent = '等待支付确认' + dots;
            }
        }, config.pollInterval);
    }

    function onPaySuccess() {
        els.payStatusText.textContent = '支付成功！正在跳转到报告…';
        els.payStatus.style.display = 'none';

        // 显示成功提示
        showToast('支付成功！正在解锁报告…', 'success');

        // 埋点
        trackEvent('pay_success', {
            method: state.selectedMethod,
            amount: state.finalPrice,
            coupon: state.couponCode
        });

        // 延迟跳转
        setTimeout(function () {
            window.location.href = config.redirectUrl;
        }, 1500);
    }

    function onPayTimeout() {
        els.payStatus.style.display = 'none';
        els.payBtn.disabled = false;
        state.isPaying = false;

        showToast('支付超时，请重试', 'error');

        // 埋点
        trackEvent('pay_timeout', {
            method: state.selectedMethod,
            amount: state.finalPrice
        });
    }

    // ============== 工具函数 ==============
    function trackEvent(eventName, data) {
        console.log('[Track]', eventName, data);
        // 后端接入后替换为真实埋点 API
        // fetch('/api/stats/track/', { method: 'POST', body: JSON.stringify({ event: eventName, ...data }) });
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
