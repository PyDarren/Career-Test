/* ==========================================================================
   职探 - Result Module
   结果页渲染 · 支付墙 · 分享

   职责：
   - 从 URL 获取 uuid，检测服务端渲染或 localStorage 结果
   - 渲染人格认证卡 / 四维度进度条 / 职业推荐
   - 控制支付墙显隐，调起 Payment 弹窗
   - 初始化分享（Web Share API + 复制链接）

   依赖：window.Payment（支付模块）
   数据来源：Django 模板变量（服务端渲染）或 localStorage['ct_last_result']
   ========================================================================== */

(function () {
  'use strict';

  /* ----------------------------------------------------------------------
     常量定义
     ---------------------------------------------------------------------- */

  // localStorage 键名（与 assessment.js 保持一致）
  const STORAGE_KEYS = {
    UUID: 'ct_uuid',
    LAST_RESULT: 'ct_last_result'
  };

  // 四维度渲染顺序
  const DIMENSION_ORDER = ['EI', 'SN', 'TF', 'JP'];

  /* ----------------------------------------------------------------------
     Result 模块
     ---------------------------------------------------------------------- */

  const Result = {
    /* ---- 状态 ---- */
    uuid: null,               // 用户 UUID（来自 URL）
    assessmentId: null,       // 测评记录 ID（来自 data 属性或 localStorage）
    hasPaid: false,           // 是否已购买报告
    reportUrl: '',            // 报告地址（已购买时存在）
    resultData: null,         // 客户端渲染时从 localStorage 读取的结果
    serverRendered: false,    // 是否由 Django 模板服务端渲染
    initialized: false,       // 是否已初始化
    _toastTimer: null,        // toast 计时器

    /* ==================================================================
       初始化
       从 URL 获取 uuid，检查服务端渲染或 localStorage 上次结果。
       ================================================================== */
    init() {
      if (this.initialized) return;

      // 1. 从 URL 获取 uuid
      this.uuid = this.getUUIDFromURL();

      // 2. 读取容器数据属性（服务端渲染时由模板写入）
      const container = document.querySelector('.result-page');
      if (container) {
        this.assessmentId = container.dataset.assessmentId || null;
        this.hasPaid = container.dataset.hasPaid === 'true';
        this.reportUrl = container.dataset.reportUrl || '';
      }

      // 3. 判断渲染模式：存在 .cert-card 表示服务端已渲染
      this.serverRendered = !!document.querySelector('.cert-card');

      if (!this.serverRendered) {
        // 客户端渲染：从 localStorage 加载上次结果
        this.resultData = this.loadLastResult();
        if (this.resultData) {
          this.renderCertCard();
          this.renderDimensions();
          this.renderCareers();
          this.showPaywall();
        } else {
          this.renderEmpty();
        }
      }

      // 4. 初始化支付与分享
      this.initPayment();
      this.setupShare();

      // 5. 检查复测提醒（距上次测评超过 30 天）
      this.checkRetestReminder();

      this.initialized = true;
      console.info('[Result] 初始化完成, serverRendered=' + this.serverRendered);
    },

    /* ==================================================================
       从 URL 路径获取 uuid（/result/<uuid>/）
       ================================================================== */
    getUUIDFromURL() {
      const m = window.location.pathname.match(/\/result\/([^/]+)\/?/);
      if (m && m[1]) return decodeURIComponent(m[1]);

      // 回退：URL 查询参数
      const params = new URLSearchParams(window.location.search);
      return params.get('uuid') || '';
    },

    /* ==================================================================
       从 localStorage 读取上次结果
       ================================================================== */
    loadLastResult() {
      try {
        const raw = localStorage.getItem(STORAGE_KEYS.LAST_RESULT);
        if (!raw) return null;
        const data = JSON.parse(raw);
        // 校验：至少包含 mbti_type 或 type_info
        if (!data || (!data.type_info && !data.mbti_type)) return null;
        return data;
      } catch (e) {
        console.warn('[Result] localStorage 结果读取失败:', e);
        return null;
      }
    },

    /* ==================================================================
       渲染人格认证卡（客户端渲染分支）
       内容：类型代码、类型名称、标语、人偶图片、稀有度、代表人物
       ================================================================== */
    renderCertCard() {
      const container = document.getElementById('cert-card-container');
      if (!container) return;

      const info = this.getTypeInfo();
      if (!info) return;

      const roleGroup = this.resultData.role_group || info.role_group || 'analyst';
      const mascotUrl = info.mascot_url || '';
      const famous = info.famous_people || [];

      container.innerHTML =
        '<article class="cert-card" data-role="' + this.escapeAttr(roleGroup) + '">' +
          '<div class="cert-card__mascot">' +
            (mascotUrl
              ? '<img src="' + this.escapeAttr(mascotUrl) + '" alt="' +
                this.escapeAttr(info.type_code) + '" loading="lazy">'
              : '<span class="cert-card__mascot-placeholder">3D 吉祥物</span>') +
          '</div>' +
          '<div class="cert-card__body">' +
            '<h2 class="cert-card__type-code">' + this.escapeHtml(info.type_code) + '</h2>' +
            '<p class="cert-card__type-name">' + this.escapeHtml(info.type_name) + '</p>' +
            '<p class="cert-card__slogan">' + this.escapeHtml(info.type_slogan) + '</p>' +
            '<div class="cert-card__meta">' +
              '<span class="cert-card__rarity">稀有度: ' +
              this.escapeHtml(String(info.rarity)) + '% (' +
              this.escapeHtml(info.rarity_label || '') + ')</span>' +
            '</div>' +
            (famous.length
              ? '<div class="cert-card__famous">代表人物: ' +
                this.escapeHtml(famous.join(', ')) + '</div>'
              : '') +
          '</div>' +
          '<div class="cert-card__actions">' +
            '<button type="button" class="btn btn-outline btn-sm js-btn-share">分享</button>' +
            (this.hasPaid
              ? '<a href="' + this.escapeAttr(this.reportUrl || '#') +
                '" class="btn btn-primary btn-sm">查看报告</a>'
              : '<button type="button" class="btn btn-primary btn-sm js-btn-unlock">' +
                '解锁深度报告 ¥2.99</button>') +
          '</div>' +
        '</article>';

      // 客户端渲染后，绑定新生成的按钮
      this.bindActionButtons(container);
    },

    /* ==================================================================
       渲染四维度进度条（客户端渲染分支）
       ================================================================== */
    renderDimensions() {
      const container = document.getElementById('dimension-bars-container');
      if (!container) return;

      const dims = this.getDimensions();
      if (!dims) {
        container.innerHTML = '<p class="text-muted">暂无维度数据</p>';
        return;
      }

      let html = '<section class="dimension-bars" aria-label="性格维度倾向">';
      DIMENSION_ORDER.forEach((dimKey) => {
        const d = dims[dimKey];
        if (!d) return;
        const pct = typeof d.percentage === 'number' ? d.percentage : 50;
        const poleA = d.pole_a || '?';
        const poleB = d.pole_b || '?';

        html +=
          '<div class="dimension-bar">' +
            '<div class="dimension-bar__labels">' +
              '<span class="dimension-bar__label-a">' + this.escapeHtml(poleA) + '</span>' +
              '<span class="dimension-bar__label-b">' + this.escapeHtml(poleB) + '</span>' +
            '</div>' +
            '<div class="dimension-bar__track">' +
              '<div class="dimension-bar__fill" role="progressbar" ' +
                'aria-valuenow="' + pct + '" aria-valuemin="0" aria-valuemax="100" ' +
                'style="width: ' + pct + '%;"></div>' +
            '</div>' +
            '<span class="dimension-bar__percent">' + pct + '%</span>' +
          '</div>';
      });
      html += '</section>';

      container.innerHTML = html;
    },

    /* ==================================================================
       渲染职业推荐列表（客户端渲染分支）
       ================================================================== */
    renderCareers() {
      const container = document.getElementById('career-list-container');
      if (!container) return;

      const careers = this.getCareers();
      if (!careers || !careers.length) {
        container.innerHTML = '<p class="text-muted">暂无职业推荐数据</p>';
        return;
      }

      let html = '<div class="career-list">';
      careers.forEach((career) => {
        const name = career.career_name || '—';
        const score = (career.match_score != null) ? career.match_score : '—';
        const category = career.category || '';
        const careerId = career.id || '';

        html +=
          '<article class="career-item" data-career-id="' + this.escapeAttr(String(careerId)) + '">' +
            '<div class="career-item-icon" aria-hidden="true">' +
              '<svg width="20" height="20" viewBox="0 0 20 20" fill="none">' +
                '<rect x="3" y="3" width="14" height="14" rx="2" stroke="currentColor" stroke-width="1.5"/>' +
                '<path d="M7 10L9 12L13 8" stroke="currentColor" stroke-width="1.5" ' +
                  'stroke-linecap="round" stroke-linejoin="round"/>' +
              '</svg>' +
            '</div>' +
            '<div class="career-item-main">' +
              '<div class="career-item-name">' + this.escapeHtml(name) + '</div>' +
              (category
                ? '<div class="career-item-category">' + this.escapeHtml(category) + '</div>'
                : '') +
            '</div>' +
            '<div class="career-item-match">匹配度 ' + this.escapeHtml(String(score)) + '%</div>' +
            '<button type="button" class="career-feedback__btn js-career-feedback" ' +
              'data-career-id="' + this.escapeAttr(String(careerId)) + '">推荐不准</button>' +
          '</article>';
      });
      html += '</div>';

      container.innerHTML = html;
    },

    /* ==================================================================
       显示支付墙（2.99 元解锁深度报告按钮）
       ================================================================== */
    showPaywall() {
      const paywall = document.getElementById('paywall-container');
      if (!paywall) return;

      // 已购买则隐藏支付墙
      if (this.hasPaid) {
        paywall.hidden = true;
        return;
      }

      paywall.hidden = false;
      paywall.innerHTML =
        '<h2 class="paywall-title">解锁深度报告</h2>' +
        '<p class="paywall-desc">12 章深度解析你的性格优势、职业路径、人际关系与发展建议</p>' +
        '<p class="paywall-price">2.99<small>元</small></p>' +
        '<button type="button" class="btn btn-accent btn-lg btn-block js-btn-unlock">立即解锁</button>' +
        '<p class="paywall-note">一次性付费 · 永久查看 · 无需注册</p>';

      this.bindActionButtons(paywall);
    },

    /* ==================================================================
       初始化支付模块，并绑定解锁按钮
       ================================================================== */
    initPayment() {
      // 初始化支付弹窗（payment.js 已自动初始化，此处保险调用）
      if (window.Payment && typeof window.Payment.init === 'function') {
        window.Payment.init();
      }
      // 绑定服务端渲染的解锁按钮（#btn-unlock）
      this.bindUnlockButtons(document);
    },

    /* ==================================================================
       初始化分享功能（分享卡片生成 + 复制链接）
       ================================================================== */
    setupShare() {
      // 绑定服务端渲染的分享按钮（#btn-share）
      this.bindShareButtons(document);
    },

    /* ==================================================================
       检查复测提醒
       读取 localStorage['ct_last_result'] 中的 timestamp，
       如果距上次测评已超过 30 天，弹窗提示重新测评。
       ================================================================== */
    checkRetestReminder() {
      // 避免同一会话内重复弹窗
      if (sessionStorage.getItem('ct_retest_reminder_shown') === '1') return;

      let data;
      try {
        const raw = localStorage.getItem(STORAGE_KEYS.LAST_RESULT);
        if (!raw) return;
        data = JSON.parse(raw);
      } catch (e) {
        return;
      }

      if (!data || !data.timestamp) return;

      const THIRTY_DAYS_MS = 30 * 24 * 60 * 60 * 1000;
      const elapsed = Date.now() - data.timestamp;

      if (elapsed < THIRTY_DAYS_MS) return;

      // 标记本次会话已提示
      sessionStorage.setItem('ct_retest_reminder_shown', '1');

      this.showRetestModal();
    },

    /* ==================================================================
       显示复测提醒弹窗
       ================================================================== */
    showRetestModal() {
      // 避免重复创建
      if (document.getElementById('retest-modal')) return;

      const overlay = document.createElement('div');
      overlay.id = 'retest-modal';
      overlay.className = 'modal-overlay active';
      overlay.setAttribute('role', 'dialog');
      overlay.setAttribute('aria-modal', 'true');
      overlay.setAttribute('aria-labelledby', 'retest-modal-title');

      overlay.innerHTML =
        '<div class="modal">' +
          '<div class="modal-icon" aria-hidden="true">' +
            '<svg width="28" height="28" viewBox="0 0 28 28" fill="none">' +
              '<circle cx="14" cy="14" r="12" stroke="currentColor" stroke-width="2"/>' +
              '<path d="M14 8V14M14 17V19" stroke="currentColor" stroke-width="2" ' +
                'stroke-linecap="round"/>' +
            '</svg>' +
          '</div>' +
          '<h3 class="modal-title" id="retest-modal-title">距上次测评已 30 天</h3>' +
          '<p class="modal-desc">要不要再测一次？性格可能随时间和经历有所变化。</p>' +
          '<div class="modal-actions">' +
            '<button class="btn btn-outline" id="retest-view-btn">查看上次结果</button>' +
            '<button class="btn btn-primary" id="retest-retake-btn">重新测评</button>' +
          '</div>' +
        '</div>';

      document.body.appendChild(overlay);

      // 关闭弹窗
      const close = () => {
        if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
      };

      const viewBtn = overlay.querySelector('#retest-view-btn');
      if (viewBtn) {
        viewBtn.addEventListener('click', close);
      }

      const retakeBtn = overlay.querySelector('#retest-retake-btn');
      if (retakeBtn) {
        retakeBtn.addEventListener('click', () => {
          window.location.href = '/assessment/';
        });
      }

      overlay.addEventListener('click', (e) => {
        if (e.target === overlay) close();
      });
    },

    /* ==================================================================
       发起支付：调用 Payment.showPaymentModal()
       ================================================================== */
    startPayment() {
      const assessmentId = this.assessmentId || this.getAssessmentIdFromResult();
      const uuid = this.uuid ||
        (this.resultData && this.resultData.uuid) ||
        this.getUUIDFromStorage();

      if (!assessmentId) {
        alert('未找到测评记录，请先完成测评。');
        return;
      }
      if (!uuid) {
        alert('用户标识缺失，请刷新页面后重试。');
        return;
      }

      if (window.Payment && typeof window.Payment.showPaymentModal === 'function') {
        window.Payment.showPaymentModal(assessmentId, uuid);
      } else {
        console.error('[Result] Payment 模块未加载');
        alert('支付模块未就绪，请刷新页面后重试。');
      }
    },

    /* ==================================================================
       处理分享：优先 Web Share API，否则复制链接
       ================================================================== */
    handleShare() {
      const info = this.getTypeInfo();
      const card = this.generateShareCard(info);
      const shareUrl = window.location.href;

      // 优先使用原生分享 API
      if (navigator.share) {
        navigator.share({
          title: card.title,
          text: card.text,
          url: shareUrl
        }).catch(() => {
          // 用户取消或失败 → 回退到复制链接
          this.copyLink(shareUrl, card);
        });
        return;
      }

      // 回退：复制链接
      this.copyLink(shareUrl, card);
    },

    /* ==================================================================
       生成分享卡片文案
       ================================================================== */
    generateShareCard(info) {
      if (!info || !info.type_code) {
        return {
          title: '我的 MBTI 职业性格',
          text: '快来测测你的职业性格吧！'
        };
      }
      const code = info.type_code || '';
      const name = info.type_name || '';
      const slogan = info.type_slogan || '';
      return {
        title: '我的 MBTI 职业性格 - ' + code + ' ' + name,
        text: '我的性格类型是 ' + code + ' ' + name +
          (slogan ? '（' + slogan + '）' : '') + '，快来测测你的吧！'
      };
    },

    /* ==================================================================
       复制链接到剪贴板
       ================================================================== */
    copyLink(url, card) {
      const text = (card && card.text ? card.text + '\n' : '') + url;

      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => {
          this.showToast('链接已复制，快去分享吧！');
        }).catch(() => {
          this.fallbackCopy(text);
        });
      } else {
        this.fallbackCopy(text);
      }
    },

    /* ==================================================================
       兼容性复制方案（execCommand）
       ================================================================== */
    fallbackCopy(text) {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      try {
        document.execCommand('copy');
        this.showToast('链接已复制，快去分享吧！');
      } catch (e) {
        this.showToast('复制失败，请手动复制链接');
      }
      document.body.removeChild(ta);
    },

    /* ==================================================================
       轻量提示（toast）
       ================================================================== */
    showToast(message) {
      let toast = document.getElementById('ct-toast');
      if (!toast) {
        toast = document.createElement('div');
        toast.id = 'ct-toast';
        toast.className = 'ct-toast';
        toast.setAttribute('role', 'status');
        toast.setAttribute('aria-live', 'polite');
        document.body.appendChild(toast);
      }
      toast.textContent = message;
      toast.classList.add('ct-toast--visible');
      clearTimeout(this._toastTimer);
      this._toastTimer = setTimeout(() => {
        toast.classList.remove('ct-toast--visible');
      }, 2200);
    },

    /* ==================================================================
       空状态渲染（无结果数据时）
       ================================================================== */
    renderEmpty() {
      const main = document.querySelector('.result-page');
      if (!main) return;
      main.innerHTML =
        '<div class="result-empty">' +
          '<p class="result-empty__text">暂无测评结果</p>' +
          '<p class="result-empty__hint text-muted">请先完成测评再查看结果</p>' +
          '<a href="/assessment/" class="btn btn-primary">开始测评</a>' +
        '</div>';
    },

    /* ==================================================================
       按钮绑定（解锁 / 分享），含重复绑定保护
       ================================================================== */
    bindUnlockButtons(scope) {
      const root = scope || document;
      const btns = root.querySelectorAll('#btn-unlock, .js-btn-unlock');
      btns.forEach((btn) => {
        if (btn.dataset.boundUnlock === '1') return;
        btn.dataset.boundUnlock = '1';
        btn.addEventListener('click', () => this.startPayment());
      });
    },

    bindShareButtons(scope) {
      const root = scope || document;
      const btns = root.querySelectorAll('#btn-share, .js-btn-share');
      btns.forEach((btn) => {
        if (btn.dataset.boundShare === '1') return;
        btn.dataset.boundShare = '1';
        btn.addEventListener('click', () => this.handleShare());
      });
    },

    // 同时绑定解锁与分享按钮
    bindActionButtons(scope) {
      this.bindUnlockButtons(scope);
      this.bindShareButtons(scope);
    },

    /* ==================================================================
       数据获取辅助
       ================================================================== */
    getTypeInfo() {
      // 标准评分结果：type_info 为完整类型配置
      if (this.resultData && this.resultData.type_info) {
        return this.resultData.type_info;
      }
      // 兼容降级评分结果（仅 mbti_type，无 type_info）
      if (this.resultData && this.resultData.mbti_type) {
        return {
          type_code: this.resultData.mbti_type,
          type_name: '',
          type_slogan: '',
          role_group: this.resultData.role_group || 'analyst',
          rarity: '',
          rarity_label: '',
          famous_people: [],
          mascot_url: ''
        };
      }
      return null;
    },

    getDimensions() {
      if (this.resultData && this.resultData.dimensions) {
        return this.resultData.dimensions;
      }
      return null;
    },

    getCareers() {
      if (this.resultData && this.resultData.recommended_careers) {
        return this.resultData.recommended_careers;
      }
      return [];
    },

    getAssessmentIdFromResult() {
      if (this.resultData && this.resultData.assessment_id) {
        return this.resultData.assessment_id;
      }
      return null;
    },

    getUUIDFromStorage() {
      try {
        return localStorage.getItem(STORAGE_KEYS.UUID) || '';
      } catch (e) {
        return '';
      }
    },

    /* ==================================================================
       HTML / 属性转义
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
     自动初始化（result.js 仅在结果页引入）
     ---------------------------------------------------------------------- */
  function autoInit() {
    if (document.body.dataset.page !== 'result') return;
    Result.init();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', autoInit);
  } else {
    autoInit();
  }

  /* ----------------------------------------------------------------------
     导出
     ---------------------------------------------------------------------- */
  window.Result = Result;

})();
