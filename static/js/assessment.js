/* ==========================================================================
   职探 - Assessment Module
   MBTI 职业性格测评 · 答题页交互逻辑

   职责：
   - 解析题目数据并渲染逐题答题界面
   - 管理答题状态（当前题号、答案对象）
   - 刻度选择后延迟自动前进
   - 进度持久化（localStorage，7 天过期）
   - 提交答案至 /api/score/，失败时降级到 FallbackScoring

   依赖：window.FallbackScoring（降级评分模块，按需调用）
   ========================================================================== */

(function () {
  'use strict';

  /* ----------------------------------------------------------------------
     常量定义
     ---------------------------------------------------------------------- */

  // localStorage 键名
  const STORAGE_KEYS = {
    UUID: 'ct_uuid',                       // 用户 UUID（永久）
    PROGRESS: 'ct_assessment_progress',    // 答题进度（7 天过期）
    LAST_RESULT: 'ct_last_result'          // 上次结果（会话级）
  };

  // 行为参数
  const JUMP_DELAY = 300;                  // 选择刻度后跳转下一题的延迟（毫秒）
  const PROGRESS_SAVE_INTERVAL = 5;        // 每 5 题保存一次进度
  const PROGRESS_EXPIRY = 7 * 24 * 60 * 60 * 1000;  // 进度过期时间：7 天（毫秒）
  const DEFAULT_TOTAL = 48;               // 默认题目总数

  /* ----------------------------------------------------------------------
     Assessment 模块
     ---------------------------------------------------------------------- */

  const Assessment = {
    /* ---- 状态 ---- */
    questions: [],          // 题目列表
    questionMap: {},        // 题目索引 {id: question}
    currentIdx: 0,          // 当前题目索引（0-based）
    answers: {},            // 答案对象 {question_id: position}
    total: DEFAULT_TOTAL,   // 题目总数
    isAdvancing: false,     // 是否正在跳转（防抖，避免重复触发）
    isSubmitting: false,    // 是否正在提交
    initialized: false,     // 是否已初始化

    /* ==================================================================
       初始化
       @param {string} questionsJson - 题目 JSON 字符串（由 Django 模板传入）
       ================================================================== */
    init(questionsJson) {
      // 1. 解析题目数据
      let questions = [];
      try {
        questions = JSON.parse(questionsJson);
      } catch (e) {
        console.error('[Assessment] 题目 JSON 解析失败:', e);
        this.renderError('题目数据加载失败，请刷新页面重试。');
        return;
      }
      if (!Array.isArray(questions) || questions.length === 0) {
        console.error('[Assessment] 题目数据为空');
        this.renderError('题目数据为空，请刷新页面重试。');
        return;
      }

      // 2. 按 display_order 排序（后端已排序，此处保险）
      questions.sort((a, b) => (a.display_order || 0) - (b.display_order || 0));

      // 3. 初始化状态
      this.questions = questions;
      this.total = questions.length;
      this.currentIdx = 0;
      this.answers = {};
      this.isAdvancing = false;
      this.isSubmitting = false;
      this.initialized = true;

      // 4. 构建题目索引
      this.questionMap = {};
      questions.forEach((q) => { this.questionMap[q.id] = q; });

      // 5. 确保 UUID 存在
      this.getOrCreateUUID();

      // 6. 绑定事件 & 注入"上一题"按钮
      this.bindEvents();
      this.injectPrevButton();

      // 7. 恢复上次进度（含 7 天过期检查 & 弹窗询问）
      const restored = this.loadProgress();
      if (restored && restored.answers) {
        const answeredCount = Object.keys(restored.answers).length;
        const continueAssessment = window.confirm(
          '检测到上次未完成的测评进度（已完成 ' + answeredCount + '/' + this.total + ' 题）。\n' +
          '是否继续上次测评？\n' +
          '点击"取消"将开始全新测评。'
        );
        if (continueAssessment) {
          // 仅保留当前题目列表中存在的题目作答
          const valid = {};
          Object.keys(restored.answers).forEach((qid) => {
            if (this.questionMap[qid]) {
              valid[qid] = restored.answers[qid];
            }
          });
          this.answers = valid;

          let idx = restored.currentIdx || 0;
          if (idx < 0) idx = 0;
          if (idx > this.total - 1) idx = this.total - 1;
          this.currentIdx = idx;
        } else {
          localStorage.removeItem(STORAGE_KEYS.PROGRESS);
        }
      }

      // 8. 页面卸载时保存进度（保险措施）
      window.addEventListener('beforeunload', () => {
        if (Object.keys(this.answers).length > 0 && !this.isSubmitting) {
          this.saveProgress();
        }
      });

      // 9. 渲染首题
      this.renderQuestion();

      console.info('[Assessment] 初始化完成, 共 ' + this.total + ' 题');
    },

    /* ==================================================================
       选择刻度位置
       记录答案，每 5 题保存进度，300ms 后跳转下一题。
       @param {number} position - 刻度位置 (1-6)
       ================================================================== */
    selectPosition(position) {
      // 跳转过程或提交中，忽略重复触发
      if (this.isAdvancing || this.isSubmitting) return;

      const q = this.questions[this.currentIdx];
      if (!q) return;
      if (position < 1 || position > 6) return;

      // 记录答案
      this.answers[q.id] = position;
      this.markDotSelected(position);

      // 每 5 题保存一次进度
      if (Object.keys(this.answers).length % PROGRESS_SAVE_INTERVAL === 0) {
        this.saveProgress();
      }

      // 300ms 后跳转到下一题
      this.isAdvancing = true;
      setTimeout(() => {
        this.isAdvancing = false;
        this.next();
      }, JUMP_DELAY);
    },

    /* ==================================================================
       跳转到下一题；若为最后一题则提交
       ================================================================== */
    next() {
      if (this.currentIdx >= this.total - 1) {
        // 最后一题，保存进度并提交
        this.saveProgress();
        this.submit();
        return;
      }
      this.currentIdx++;
      this.renderQuestion();
    },

    /* ==================================================================
       返回上一题（如果有答题历史）
       ================================================================== */
    prev() {
      if (this.currentIdx <= 0) return;
      this.currentIdx--;
      this.renderQuestion();
    },

    /* ==================================================================
       渲染当前题目（题号、text_a、text_b），更新进度条
       ================================================================== */
    renderQuestion() {
      const q = this.questions[this.currentIdx];
      if (!q) return;

      // 题号与提示
      const questionText = document.getElementById('question-text');
      if (questionText) {
        questionText.textContent = '第 ' + (this.currentIdx + 1) + ' 题 · 下面哪一项更符合你？';
      }

      // A / B 选项文本
      const labelA = document.querySelector('.scale-label-a');
      const labelB = document.querySelector('.scale-label-b');
      if (labelA) labelA.textContent = q.text_a || '';
      if (labelB) labelB.textContent = q.text_b || '';

      // 底部提示文案
      const hintSpans = document.querySelectorAll('.scale-hint span');
      if (hintSpans.length >= 2) {
        hintSpans[0].textContent = '← ' + (q.text_a || 'A');
        hintSpans[1].textContent = (q.text_b || 'B') + ' →';
      }

      // 清除刻度选中状态
      this.clearDotSelection();

      // 若该题已答，恢复选中
      if (this.answers[q.id] !== undefined) {
        this.markDotSelected(this.answers[q.id]);
      }

      // 更新进度条
      this.updateProgress();

      // 更新"上一题"按钮状态
      this.updateBackButton();
    },

    /* ==================================================================
       更新进度条：显示"当前题号/48"和百分比
       ================================================================== */
    updateProgress() {
      const current = this.currentIdx + 1;
      const percent = Math.round((current / this.total) * 100);

      const curEl = document.querySelector('.progress-current');
      const pctEl = document.querySelector('.progress-percent');
      const fillEl = document.querySelector('.progress-bar-fill');

      if (curEl) curEl.textContent = current;
      if (pctEl) pctEl.textContent = percent + '%';
      if (fillEl) fillEl.style.width = percent + '%';
    },

    /* ==================================================================
       保存进度到 localStorage
       含 timestamp 和 answers（同时保存 currentIdx 便于恢复）
       ================================================================== */
    saveProgress() {
      const data = {
        answers: this.answers,
        currentIdx: this.currentIdx,
        timestamp: Date.now()
      };
      try {
        localStorage.setItem(STORAGE_KEYS.PROGRESS, JSON.stringify(data));
      } catch (e) {
        console.warn('[Assessment] 进度保存失败:', e);
      }
    },

    /* ==================================================================
       从 localStorage 读取进度（含 7 天过期检查）
       @returns {Object|null} 进度对象 {answers, currentIdx, timestamp}
       ================================================================== */
    loadProgress() {
      let data = null;
      try {
        const raw = localStorage.getItem(STORAGE_KEYS.PROGRESS);
        if (!raw) return null;
        data = JSON.parse(raw);
      } catch (e) {
        console.warn('[Assessment] 进度读取失败:', e);
        return null;
      }

      if (!data || typeof data !== 'object' || !data.answers) return null;

      // 7 天过期检查
      const timestamp = data.timestamp || 0;
      if (Date.now() - timestamp > PROGRESS_EXPIRY) {
        localStorage.removeItem(STORAGE_KEYS.PROGRESS);
        return null;
      }

      return data;
    },

    /* ==================================================================
       提交测评答案
       所有题目答完后，组装 answers 数组 POST 到 /api/score/
       ================================================================== */
    submit() {
      // 校验是否全部答完
      const answeredCount = Object.keys(this.answers).length;
      if (answeredCount < this.total) {
        // 定位到第一个未答题目
        const firstUnanswered = this.questions.findIndex(
          (q) => this.answers[q.id] === undefined
        );
        if (firstUnanswered >= 0) {
          this.currentIdx = firstUnanswered;
          this.renderQuestion();
        }
        alert('还有 ' + (this.total - answeredCount) + ' 题未完成，请答完所有题目后再提交。');
        return;
      }

      const uuid = this.getOrCreateUUID();

      // 组装 answers 数组 [{question_id, position}]
      const answersArray = this.questions.map((q) => ({
        question_id: q.id,
        position: this.answers[q.id]
      }));

      this.setSubmitting(true);

      fetch('/api/score/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCSRFToken()
        },
        body: JSON.stringify({
          uuid: uuid,
          answers: answersArray
        })
      })
        .then((response) => {
          if (!response.ok) {
            throw new Error('HTTP ' + response.status);
          }
          return response.json();
        })
        .then((data) => {
          // 提交成功，清除答题进度
          localStorage.removeItem(STORAGE_KEYS.PROGRESS);
          // 保存结果（会话级，含时间戳供复测提醒使用）
          try {
            data.timestamp = Date.now();
            localStorage.setItem(STORAGE_KEYS.LAST_RESULT, JSON.stringify(data));
          } catch (e) {
            console.warn('[Assessment] 结果保存失败:', e);
          }
          // 跳转到结果页 /result/<uuid>/
          window.location.href = '/result/' + uuid + '/';
        })
        .catch((err) => {
          // 提交失败，启用降级评分
          console.warn('[Assessment] 提交失败，启用降级评分:', err);
          this.setSubmitting(false);
          this.handleFallback(answersArray, uuid);
        });
    },

    /* ==================================================================
       降级评分处理（提交失败时调用 FallbackScoring）
       ================================================================== */
    handleFallback(answersArray, uuid) {
      let result = null;
      try {
        if (window.FallbackScoring) {
          // 注入题目元数据，供降级评分查表
          if (typeof window.FallbackScoring.setQuestions === 'function') {
            window.FallbackScoring.setQuestions(this.questions);
          }
          result = window.FallbackScoring.calculate(answersArray);
        } else {
          console.error('[Assessment] FallbackScoring 模块未加载');
        }
      } catch (e) {
        console.error('[Assessment] 降级评分出错:', e);
      }

      if (!result) {
        alert('提交失败，请检查网络连接后重试。');
        return;
      }

      result.uuid = uuid;
      result.timestamp = Date.now();

      // 保存降级结果（会话级）
      try {
        localStorage.setItem(STORAGE_KEYS.LAST_RESULT, JSON.stringify(result));
      } catch (e) {
        console.warn('[Assessment] 降级结果保存失败:', e);
      }

      // 显示降级结果
      this.showDegradedResult(result);
    },

    /* ==================================================================
       显示降级评分结果（内联渲染，保证用户可见）
       ================================================================== */
    showDegradedResult(result) {
      const container = document.querySelector('.assessment-content') ||
                        document.querySelector('.assessment-page');
      if (!container) {
        alert('网络异常，已使用本地降级评分。\n你的性格类型：' + result.mbti_type);
        return;
      }

      // 注入降级结果样式（仅一次）
      this.injectDegradedStyles();

      const dims = result.dimensions || {};
      const dimensionOrder = ['EI', 'SN', 'TF', 'JP'];
      const dimensionLabels = {
        EI: '外向 / 内向',
        SN: '实感 / 直觉',
        TF: '思考 / 情感',
        JP: '判断 / 感知'
      };

      const dimHtml = dimensionOrder.map((dim) => {
        const d = dims[dim] || {};
        const pct = d.percentage || 0;
        const label = d.label || 'X';
        return (
          '<div class="ct-degraded-dim">' +
            '<div class="ct-degraded-dim-head">' +
              '<span class="ct-degraded-dim-name">' + dimensionLabels[dim] + '</span>' +
              '<span class="ct-degraded-dim-value">' + label + ' · ' + pct + '%</span>' +
            '</div>' +
            '<div class="ct-degraded-dim-bar">' +
              '<div class="ct-degraded-dim-fill" style="width:' + pct + '%"></div>' +
            '</div>' +
          '</div>'
        );
      }).join('');

      container.innerHTML =
        '<div class="ct-degraded-result">' +
          '<p class="ct-degraded-badge">本地降级评分</p>' +
          '<h2 class="ct-degraded-type">' + (result.mbti_type || '----') + '</h2>' +
          '<p class="ct-degraded-desc">由于网络异常，已使用本地简化算法完成评分。' +
          '该结果为简化版本，建议网络恢复后重新测评以获取完整报告。</p>' +
          '<div class="ct-degraded-dims">' + dimHtml + '</div>' +
          '<div class="ct-degraded-actions">' +
            '<button type="button" class="btn btn-outline btn-sm" id="ct-degraded-retry">重新提交</button>' +
            '<a href="/result/' + (result.uuid || '') + '/" class="btn btn-accent btn-sm">查看结果页</a>' +
          '</div>' +
        '</div>';

      // 绑定"重新提交"按钮：直接再次提交（答案仍在内存中）
      const retryBtn = document.getElementById('ct-degraded-retry');
      if (retryBtn) {
        retryBtn.addEventListener('click', () => {
          localStorage.removeItem(STORAGE_KEYS.LAST_RESULT);
          this.submit();
        });
      }
    },

    /* ==================================================================
       注入降级结果样式（仅一次）
       ================================================================== */
    injectDegradedStyles() {
      if (document.getElementById('ct-degraded-styles')) return;
      const style = document.createElement('style');
      style.id = 'ct-degraded-styles';
      style.textContent = [
        '.ct-degraded-result{max-width:640px;margin:0 auto;padding:24px;text-align:center;}',
        '.ct-degraded-badge{display:inline-block;padding:4px 12px;background:#FEF3C7;color:#92400E;border-radius:999px;font-size:13px;margin:0 0 16px;}',
        '.ct-degraded-type{font-size:48px;font-weight:700;color:#4D3E8C;margin:8px 0;letter-spacing:4px;}',
        '.ct-degraded-desc{color:#6B7280;font-size:14px;line-height:1.6;margin:12px 0 24px;}',
        '.ct-degraded-dims{display:flex;flex-direction:column;gap:16px;margin:24px 0;text-align:left;}',
        '.ct-degraded-dim-head{display:flex;justify-content:space-between;font-size:13px;margin-bottom:6px;}',
        '.ct-degraded-dim-name{color:#6B7280;}',
        '.ct-degraded-dim-value{font-weight:600;color:#4D3E8C;}',
        '.ct-degraded-dim-bar{height:8px;background:#E5E7EB;border-radius:4px;overflow:hidden;}',
        '.ct-degraded-dim-fill{height:100%;background:linear-gradient(90deg,#8B5CF6,#06B6D4);border-radius:4px;transition:width .4s;}',
        '.ct-degraded-actions{display:flex;gap:12px;justify-content:center;margin-top:24px;}'
      ].join('');
      document.head.appendChild(style);
    },

    /* ==================================================================
       事件绑定
       ================================================================== */
    bindEvents() {
      // 刻度选择（事件委托，兼容已存在的 .scale-dot 绑定）
      const scaleContainer = document.querySelector('[data-scale-selector]') ||
                             document.querySelector('.scale-container');
      if (scaleContainer) {
        scaleContainer.addEventListener('click', (e) => {
          const dot = e.target.closest('.scale-dot');
          if (!dot) return;
          const value = parseInt(dot.dataset.value, 10);
          if (!isNaN(value)) this.selectPosition(value);
        });
      }

      // 兼容 main.js 的 window.onScaleSelect 回调
      window.onScaleSelect = (value) => this.selectPosition(value);

      // 键盘支持：1-6 数字键选择，左方向键回到上一题
      document.addEventListener('keydown', (e) => {
        if (this.isAdvancing || this.isSubmitting) return;
        if (e.ctrlKey || e.metaKey || e.altKey) return;
        if (e.key >= '1' && e.key <= '6') {
          this.selectPosition(parseInt(e.key, 10));
        } else if (e.key === 'ArrowLeft') {
          this.prev();
        }
      });
    },

    /* ==================================================================
       注入"上一题"按钮
       ================================================================== */
    injectPrevButton() {
      const backWrap = document.querySelector('.assessment-back');
      if (!backWrap) return;
      // 避免重复注入
      if (document.querySelector('.prev-question-btn')) return;

      const prevBtn = document.createElement('button');
      prevBtn.type = 'button';
      prevBtn.className = 'btn btn-outline btn-sm prev-question-btn';
      prevBtn.style.marginRight = '8px';
      prevBtn.textContent = '上一题';
      prevBtn.addEventListener('click', () => this.prev());
      backWrap.insertBefore(prevBtn, backWrap.firstChild);
    },

    /* ==================================================================
       更新"上一题"按钮可用状态（无答题历史时禁用）
       ================================================================== */
    updateBackButton() {
      const prevBtn = document.querySelector('.prev-question-btn');
      if (!prevBtn) return;
      const disabled = this.currentIdx <= 0;
      prevBtn.disabled = disabled;
      prevBtn.style.opacity = disabled ? '0.4' : '';
      prevBtn.style.cursor = disabled ? 'not-allowed' : '';
    },

    /* ==================================================================
       刻度选中状态管理
       ================================================================== */
    markDotSelected(position) {
      const dots = document.querySelectorAll('.scale-dot');
      dots.forEach((dot) => {
        const v = parseInt(dot.dataset.value, 10);
        const selected = v === position;
        dot.classList.toggle('selected', selected);
        dot.setAttribute('aria-checked', selected ? 'true' : 'false');
      });
      const input = document.querySelector('[data-scale-input]');
      if (input) input.value = position;
    },

    clearDotSelection() {
      const dots = document.querySelectorAll('.scale-dot');
      dots.forEach((dot) => {
        dot.classList.remove('selected');
        dot.setAttribute('aria-checked', 'false');
      });
      const input = document.querySelector('[data-scale-input]');
      if (input) input.value = '';
    },

    /* ==================================================================
       提交状态切换（提交中禁用刻度）
       ================================================================== */
    setSubmitting(flag) {
      this.isSubmitting = flag;
      const dots = document.querySelectorAll('.scale-dot');
      dots.forEach((dot) => { dot.disabled = flag; });
    },

    /* ==================================================================
       UUID 管理（永久存储于 localStorage['ct_uuid']）
       ================================================================== */
    getOrCreateUUID() {
      let uuid = null;
      try {
        uuid = localStorage.getItem(STORAGE_KEYS.UUID);
      } catch (e) {
        uuid = null;
      }
      if (!uuid) {
        uuid = this.generateUUID();
        try {
          localStorage.setItem(STORAGE_KEYS.UUID, uuid);
        } catch (e) {
          console.warn('[Assessment] UUID 保存失败:', e);
        }
      }
      return uuid;
    },

    generateUUID() {
      // 优先使用原生 crypto.randomUUID
      if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
        return crypto.randomUUID();
      }
      // 回退：手动生成 UUID v4
      return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
        const r = (Math.random() * 16) | 0;
        const v = c === 'x' ? r : (r & 0x3) | 0x8;
        return v.toString(16);
      });
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
       错误渲染
       ================================================================== */
    renderError(message) {
      const questionText = document.getElementById('question-text');
      if (questionText) {
        questionText.textContent = message;
      }
    }
  };

  /* ----------------------------------------------------------------------
     自动初始化
     当页面为测评页（body[data-page="assessment"]）且题目数据可用时自动启动。
     题目数据来源（任选其一）：
       1. 全局变量 window.QUESTIONS_JSON（JSON 字符串）
       2. <script type="application/json" id="ct-questions-data"> 元素内容
     也可在外部直接调用 Assessment.init(questionsJson) 显式初始化。
     ---------------------------------------------------------------------- */
  function autoInit() {
    if (document.body.dataset.page !== 'assessment') return;
    if (Assessment.initialized) return;

    let questionsJson = null;

    if (typeof window.QUESTIONS_JSON === 'string') {
      questionsJson = window.QUESTIONS_JSON;
    } else {
      const dataEl = document.getElementById('ct-questions-data');
      if (dataEl) {
        questionsJson = dataEl.textContent.trim();
      }
    }

    if (questionsJson) {
      Assessment.init(questionsJson);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', autoInit);
  } else {
    autoInit();
  }

  /* ----------------------------------------------------------------------
     导出
     ---------------------------------------------------------------------- */
  window.Assessment = Assessment;

})();
