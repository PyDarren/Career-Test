/* ==========================================================================
   职探 - Payment Module
   支付弹窗 · 订单创建 · 状态轮询

   职责：
   - 注入并控制支付弹窗（微信 / 支付宝）
   - 调用 /api/payment/create/ 创建订单
   - 每 2 秒轮询 /api/order/status/<order_no>/，持续 2 分钟（60 次）
   - 支付成功跳转报告页；超时 / 订单过期提示重新支付

   依赖：无（原生 fetch API）
   ========================================================================== */

(function () {
  'use strict';

  /* ----------------------------------------------------------------------
     常量定义
     ---------------------------------------------------------------------- */

  // 轮询参数
  const POLL_INTERVAL = 2000;          // 轮询间隔：2 秒
  const POLL_MAX_TIMES = 60;           // 最大轮询次数：60 次（共 2 分钟）

  // 接口地址
  const API_CREATE = '/api/payment/create/';
  const API_STATUS_PREFIX = '/api/order/status/';
  const API_STATUS_SUFFIX = '/';
  const REPORT_PREFIX = '/report/';

  // 支付方式
  const METHODS = {
    wechat: '微信支付',
    alipay: '支付宝'
  };

  /* ----------------------------------------------------------------------
     Payment 模块
     ---------------------------------------------------------------------- */

  const Payment = {
    /* ---- 状态 ---- */
    modalEl: null,            // 弹窗根元素
    assessmentId: null,       // 当前测评记录 ID
    uuid: null,               // 用户 UUID
    currentOrderNo: null,     // 当前订单号
    currentMethod: null,      // 当前支付方式
    pollTimer: null,          // 轮询定时器
    pollCount: 0,             // 已轮询次数
    isPolling: false,         // 是否正在轮询
    isCreating: false,        // 是否正在创建订单
    initialized: false,       // 是否已初始化

    /* ==================================================================
       初始化
       检测页面上是否有支付弹窗元素；若没有则注入并绑定事件。
       ================================================================== */
    init() {
      if (this.initialized) return;

      // 检测已有弹窗元素，避免重复注入
      this.modalEl = document.getElementById('payment-modal');
      if (!this.modalEl) {
        this.modalEl = this.buildModal();
        if (this.modalEl) document.body.appendChild(this.modalEl);
      }

      if (this.modalEl) this.bindEvents();
      this.initialized = true;
    },

    /* ==================================================================
       构建支付弹窗 DOM
       复用全局 .modal-overlay / .modal 样式，叠加 payment-modal BEM 类
       ================================================================== */
    buildModal() {
      const overlay = document.createElement('div');
      overlay.className = 'modal-overlay payment-modal';
      overlay.id = 'payment-modal';
      overlay.setAttribute('role', 'dialog');
      overlay.setAttribute('aria-modal', 'true');
      overlay.setAttribute('aria-labelledby', 'payment-modal-title');
      overlay.setAttribute('aria-hidden', 'true');

      overlay.innerHTML =
        '<div class="modal payment-modal__dialog">' +
          '<button type="button" class="payment-modal__close" id="payment-modal-close" ' +
            'aria-label="关闭支付弹窗">&times;</button>' +
          '<h3 class="modal-title" id="payment-modal-title">选择支付方式</h3>' +
          '<p class="modal-desc">支付 ¥2.99 解锁深度报告</p>' +

          // 支付方式选择
          '<div class="payment-modal__methods" id="payment-methods">' +
            '<button type="button" class="payment-modal__method" data-method="wechat">微信支付</button>' +
            '<button type="button" class="payment-modal__method" data-method="alipay">支付宝</button>' +
          '</div>' +

          // 二维码 / 支付信息
          '<div class="payment-modal__qr" id="payment-qr" hidden>' +
            '<div class="payment-modal__qr-box" id="payment-qr-content"></div>' +
            '<p class="payment-modal__status" id="payment-status">请扫码完成支付</p>' +
            '<p class="payment-modal__countdown" id="payment-countdown"></p>' +
          '</div>' +

          // 错误 / 超时提示
          '<p class="payment-modal__error" id="payment-error" hidden></p>' +

          // 操作按钮
          '<div class="modal-actions">' +
            '<button type="button" class="btn btn-outline btn-sm" id="payment-modal-cancel">取消</button>' +
            '<button type="button" class="btn btn-primary btn-sm" id="payment-retry" hidden>重新支付</button>' +
          '</div>' +
        '</div>';

      return overlay;
    },

    /* ==================================================================
       事件绑定
       ================================================================== */
    bindEvents() {
      // 关闭按钮
      const closeBtn = this.modalEl.querySelector('#payment-modal-close');
      if (closeBtn) {
        closeBtn.addEventListener('click', () => this.closePaymentModal());
      }

      // 取消按钮
      const cancelBtn = this.modalEl.querySelector('#payment-modal-cancel');
      if (cancelBtn) {
        cancelBtn.addEventListener('click', () => this.closePaymentModal());
      }

      // 点击遮罩关闭
      this.modalEl.addEventListener('click', (e) => {
        if (e.target === this.modalEl) this.closePaymentModal();
      });

      // 支付方式选择（事件委托）
      const methodsWrap = this.modalEl.querySelector('#payment-methods');
      if (methodsWrap) {
        methodsWrap.addEventListener('click', (e) => {
          const btn = e.target.closest('.payment-modal__method');
          if (!btn) return;
          const method = btn.dataset.method;
          if (method) this.createPayment(method);
        });
      }

      // 重新支付
      const retryBtn = this.modalEl.querySelector('#payment-retry');
      if (retryBtn) {
        retryBtn.addEventListener('click', () => this.resetToMethodSelect());
      }

      // ESC 关闭弹窗
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && this.isOpen()) this.closePaymentModal();
      });
    },

    /* ==================================================================
       显示支付弹窗
       @param {string|number} assessmentId - 测评记录 ID
       @param {string} uuid - 用户 UUID
       ================================================================== */
    showPaymentModal(assessmentId, uuid) {
      if (!this.initialized) this.init();
      if (!this.modalEl) {
        console.error('[Payment] 支付弹窗未初始化');
        return;
      }

      this.assessmentId = assessmentId;
      this.uuid = uuid;

      // 重置状态并停止可能存在的轮询
      this.stopPolling();
      this.resetToMethodSelect();
      this.open();
    },

    /* ==================================================================
       关闭支付弹窗，并停止轮询
       ================================================================== */
    closePaymentModal() {
      this.close();
      this.stopPolling();
    },

    /* ==================================================================
       创建支付订单
       POST /api/payment/create/，参数 {assessment_id, uuid, method}
       @param {string} method - 支付方式（wechat / alipay）
       ================================================================== */
    createPayment(method) {
      if (this.isCreating) return;
      if (!METHODS[method]) {
        console.warn('[Payment] 不支持的支付方式:', method);
        return;
      }
      if (!this.assessmentId || !this.uuid) {
        this.showError('支付参数缺失，请刷新页面后重试。');
        return;
      }

      this.isCreating = true;
      this.currentMethod = method;
      this.setMethodsDisabled(true);
      this.hideError();
      this.showStatus('正在创建订单...');

      fetch(API_CREATE, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCSRFToken()
        },
        body: JSON.stringify({
          assessment_id: this.assessmentId,
          uuid: this.uuid,
          method: method
        })
      })
        .then((response) => this.parseResponse(response))
        .then((data) => {
          this.isCreating = false;
          this.setMethodsDisabled(false);

          if (!data || data.error) {
            this.showError(data ? data.error : '创建订单失败，请重试。');
            return;
          }

          this.currentOrderNo = data.order_no;
          this.renderPayInfo(data.pay_info, method);
          this.startPolling(data.order_no);
        })
        .catch((err) => {
          this.isCreating = false;
          this.setMethodsDisabled(false);
          console.error('[Payment] 创建订单异常:', err);
          this.showError('网络异常，创建订单失败，请重试。');
        });
    },

    /* ==================================================================
       渲染支付信息（二维码图片 / code_url 文本）
       @param {Object} payInfo - 后端返回的支付信息
       @param {string} method - 支付方式
       ================================================================== */
    renderPayInfo(payInfo, method) {
      const methodsEl = this.modalEl.querySelector('#payment-methods');
      const qrEl = this.modalEl.querySelector('#payment-qr');
      const contentEl = this.modalEl.querySelector('#payment-qr-content');
      if (methodsEl) methodsEl.hidden = true;
      if (qrEl) qrEl.hidden = false;
      if (!contentEl) return;

      const info = payInfo || {};
      let html = '';

      // 优先展示二维码图片
      if (info.qr_url) {
        html += '<img class="payment-modal__qr-img" src="' + this.escapeAttr(info.qr_url) +
          '" alt="' + METHODS[method] + '二维码">';
      } else if (info.code_url) {
        // 无图片时展示 code_url 文本，便于测试 / 扫码工具读取
        html += '<code class="payment-modal__code-url">' + this.escapeHtml(info.code_url) + '</code>';
      } else {
        html += '<span class="payment-modal__qr-placeholder">二维码生成中</span>';
      }

      contentEl.innerHTML = html;
      this.showStatus('请使用' + METHODS[method] + '扫码完成支付');
    },

    /* ==================================================================
       开始轮询订单状态
       每 2 秒查询一次，最多 60 次（共 2 分钟）
       @param {string} orderNo - 订单号
       ================================================================== */
    startPolling(orderNo) {
      this.stopPolling();
      if (!orderNo) return;

      this.currentOrderNo = orderNo;
      this.pollCount = 0;
      this.isPolling = true;

      // 立即查询一次，随后定时轮询
      this.pollOnce();
      this.pollTimer = setInterval(() => this.pollOnce(), POLL_INTERVAL);
    },

    /* ==================================================================
       单次轮询
       GET /api/order/status/<order_no>/
       ================================================================== */
    pollOnce() {
      if (!this.isPolling || !this.currentOrderNo) {
        this.stopPolling();
        return;
      }

      this.pollCount++;

      // 超过最大次数 → 视为超时
      if (this.pollCount > POLL_MAX_TIMES) {
        this.handleTimeout();
        return;
      }

      const url = API_STATUS_PREFIX +
        encodeURIComponent(this.currentOrderNo) + API_STATUS_SUFFIX;

      fetch(url, { headers: { 'Accept': 'application/json' } })
        .then((response) => this.parseResponse(response))
        .then((data) => {
          if (!this.isPolling) return;  // 已停止
          if (!data || data.error) return;

          const status = data.status;
          this.updateCountdown(data.remaining_seconds);

          if (status === 'paid') {
            // 支付成功 → 跳转报告页
            this.handlePaid();
          } else if (status === 'expired') {
            // 订单已过期
            this.handleTimeout();
          }
          // status === 'pending' → 继续轮询
        })
        .catch((err) => {
          console.warn('[Payment] 轮询查询失败:', err);
        });
    },

    /* ==================================================================
       停止轮询
       ================================================================== */
    stopPolling() {
      this.isPolling = false;
      if (this.pollTimer) {
        clearInterval(this.pollTimer);
        this.pollTimer = null;
      }
    },

    /* ==================================================================
       支付成功处理：跳转报告页 /report/<order_no>/
       ================================================================== */
    handlePaid() {
      this.stopPolling();
      this.showStatus('支付成功，正在跳转到深度报告...');
      if (this.currentOrderNo) {
        window.location.href = REPORT_PREFIX + this.currentOrderNo + '/';
      }
    },

    /* ==================================================================
       支付超时 / 订单过期处理
       ================================================================== */
    handleTimeout() {
      this.stopPolling();
      this.showError('支付超时，请重新支付');
      const retryBtn = this.modalEl.querySelector('#payment-retry');
      if (retryBtn) retryBtn.hidden = false;
    },

    /* ==================================================================
       重置弹窗到支付方式选择状态
       ================================================================== */
    resetToMethodSelect() {
      this.stopPolling();
      this.currentOrderNo = null;
      this.hideError();

      const methodsEl = this.modalEl.querySelector('#payment-methods');
      const qrEl = this.modalEl.querySelector('#payment-qr');
      const retryBtn = this.modalEl.querySelector('#payment-retry');
      const countdownEl = this.modalEl.querySelector('#payment-countdown');

      if (methodsEl) methodsEl.hidden = false;
      if (qrEl) qrEl.hidden = true;
      if (retryBtn) retryBtn.hidden = true;
      if (countdownEl) countdownEl.textContent = '';

      this.showStatus('支付 ¥2.99 解锁深度报告');
    },

    /* ==================================================================
       弹窗显隐控制
       ================================================================== */
    open() {
      if (!this.modalEl) return;
      this.modalEl.classList.add('active');
      this.modalEl.setAttribute('aria-hidden', 'false');
    },

    close() {
      if (!this.modalEl) return;
      this.modalEl.classList.remove('active');
      this.modalEl.setAttribute('aria-hidden', 'true');
    },

    isOpen() {
      return !!(this.modalEl && this.modalEl.classList.contains('active'));
    },

    /* ==================================================================
       UI 辅助方法
       ================================================================== */
    showStatus(text) {
      const el = this.modalEl.querySelector('#payment-status');
      if (el) el.textContent = text;
    },

    showError(text) {
      const errEl = this.modalEl.querySelector('#payment-error');
      if (errEl) {
        errEl.textContent = text;
        errEl.hidden = false;
      }
    },

    hideError() {
      const errEl = this.modalEl.querySelector('#payment-error');
      if (errEl) {
        errEl.textContent = '';
        errEl.hidden = true;
      }
    },

    updateCountdown(remainingSeconds) {
      const el = this.modalEl.querySelector('#payment-countdown');
      if (!el) return;
      if (typeof remainingSeconds !== 'number' || remainingSeconds <= 0) {
        el.textContent = '';
        return;
      }
      const mins = Math.floor(remainingSeconds / 60);
      const secs = remainingSeconds % 60;
      el.textContent = '剩余支付时间 ' + mins + ':' + (secs < 10 ? '0' + secs : secs);
    },

    setMethodsDisabled(disabled) {
      const btns = this.modalEl.querySelectorAll('.payment-modal__method');
      btns.forEach((btn) => { btn.disabled = !!disabled; });
    },

    /* ==================================================================
       响应解析（统一处理非 JSON / HTTP 错误）
       ================================================================== */
    parseResponse(response) {
      if (!response.ok) {
        return response.json().catch(() => ({})).then((data) =>
          Object.assign({ error: '请求失败（HTTP ' + response.status + '）' }, data)
        );
      }
      return response.json().catch(() => ({ error: '响应解析失败' }));
    },

    /* ==================================================================
       CSRF Token 获取（cookie 或 meta tag）
       ================================================================== */
    getCSRFToken() {
      // 1. 从 cookie 获取（Django 默认 csrftoken）
      const cookieToken = this.getCookie('csrftoken');
      if (cookieToken) return cookieToken;

      // 2. 从 meta tag 获取
      const meta = document.querySelector('meta[name="csrf-token"]') ||
                   document.querySelector('meta[name="csrfmiddlewaretoken"]');
      if (meta && meta.content) return meta.content;

      // 3. 从表单隐藏域获取
      const input = document.querySelector('[name="csrfmiddlewaretoken"]');
      if (input && input.value) return input.value;

      return '';
    },

    getCookie(name) {
      const cookies = document.cookie ? document.cookie.split(';') : [];
      for (let i = 0; i < cookies.length; i++) {
        const pair = cookies[i].split('=');
        const key = pair[0].trim();
        if (key === name) {
          return decodeURIComponent(pair.slice(1).join('=').trim());
        }
      }
      return '';
    },

    /* ==================================================================
       HTML / 属性转义（防止支付信息中的特殊字符破坏 DOM）
       ================================================================== */
    escapeHtml(str) {
      return String(str == null ? '' : str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    },

    escapeAttr(str) {
      return String(str == null ? '' : str)
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    }
  };

  /* ----------------------------------------------------------------------
     自动初始化（payment.js 仅在结果页通过 extra_js 引入）
     ---------------------------------------------------------------------- */
  function autoInit() {
    Payment.init();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', autoInit);
  } else {
    autoInit();
  }

  /* ----------------------------------------------------------------------
     导出
     ---------------------------------------------------------------------- */
  window.Payment = Payment;

})();
