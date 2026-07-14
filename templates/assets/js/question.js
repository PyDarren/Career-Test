/**
 * question.js — 答题页交互逻辑（对接后端 API）
 * 流程：加载题目 → 性别选择 → 80 题 5 点李克特量表 → 提交 → 跳转结果页
 * 题项来源：GET /api/questions/ (IPIP-50 大五人格 + RIASEC-30 职业兴趣)
 * 提交接口：POST /api/assessments/
 * 依赖：api.js
 */
(function () {
    'use strict';

    // ============== 题目数据（从 API 加载） ==============
    var questions = [];
    var TOTAL = 0;

    // ============== 状态 ==============
    var currentQuestion = 0;
    var answers = [];           // [{question_id, scale_value, response_duration_ms}, ...]
    var gender = null;
    var startedAt = null;       // ISO 字符串，用于 API 提交
    var startTimeMs = 0;        // 毫秒时间戳，用于内部计时
    var questionShowTime = 0;   // 当前题目展示时间戳
    var wakeLock = null;
    var questionsLoaded = false;
    var isSubmitting = false;

    // DOM
    var els = {
        stepGender: document.getElementById('stepGender'),
        stepQuestion: document.getElementById('stepQuestion'),
        stepComplete: document.getElementById('stepComplete'),
        questionNumber: document.getElementById('questionNumber'),
        questionText: document.getElementById('questionText'),
        scaleOptions: document.getElementById('scaleOptions'),
        scaleDescription: document.getElementById('scaleDescription'),
        prevBtn: document.getElementById('prevBtn'),
        nextBtn: document.getElementById('nextBtn'),
        progressWrapper: document.getElementById('progressWrapper'),
        progressCount: document.getElementById('progressCount'),
        percentage: document.getElementById('percentage'),
        progressFiller: document.getElementById('progressFiller'),
        completeTime: document.getElementById('completeTime'),
        loadingFill: document.getElementById('loadingFill'),
        loadingText: document.getElementById('loadingText'),
        viewResultBtn: document.getElementById('viewResultBtn'),
        quizWrapper: document.getElementById('quizWrapper')
    };

    // 量表选项描述
    var scaleLabels = {
        '1': '非常不符合',
        '2': '比较不符合',
        '3': '不确定',
        '4': '比较符合',
        '5': '非常符合'
    };

    // 量表选项颜色（用于粒子动画）
    var scaleColors = {
        '1': '#e17055',
        '2': '#f0867f',
        '3': '#b2bec3',
        '4': '#5ea67e',
        '5': '#3d8b5e'
    };

    // ============== 本地存储 — 断点续测 ==============
    var STORAGE_KEY = 'career_test_answers';

    function saveProgress() {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify({
                answers: answers,
                currentIndex: currentQuestion,
                startedAt: startedAt,
                questions: questions,
                gender: gender,
                timestamp: Date.now()
            }));
        } catch (e) {
            // 存储不可用时静默失败
        }
    }

    function loadProgress() {
        try {
            var saved = localStorage.getItem(STORAGE_KEY);
            if (saved) {
                return JSON.parse(saved);
            }
        } catch (e) {
            // 读取失败时静默
        }
        return null;
    }

    function clearProgress() {
        try {
            localStorage.removeItem(STORAGE_KEY);
        } catch (e) {
            // 静默失败
        }
    }

    // ============== API：加载题目 ==============
    function loadQuestions() {
        return API.getQuestions().then(function (data) {
            var list = (data && data.list) || [];
            // 按 order 排序
            list.sort(function (a, b) {
                return (a.order || 0) - (b.order || 0);
            });
            questions = list;
            TOTAL = questions.length;
            questionsLoaded = true;
            return questions;
        });
    }

    // ============== 工具函数 ==============
    function getAnswerValue(index) {
        if (answers[index] != null) {
            return answers[index].scale_value;
        }
        return null;
    }

    function getAnsweredCount() {
        return answers.filter(function (a) { return a != null; }).length;
    }

    // ============== 性别选择 ==============
    function initGenderSelection() {
        var genderOptions = document.querySelectorAll('.gender-option');
        genderOptions.forEach(function (opt) {
            opt.addEventListener('click', function () {
                gender = opt.getAttribute('data-gender');
                if (navigator.vibrate) {
                    navigator.vibrate(20);
                }
                // 记录开始时间
                if (!startedAt) {
                    startedAt = new Date().toISOString();
                    startTimeMs = Date.now();
                }
                saveProgress();
                startQuiz();
            });
        });
    }

    // ============== 开始答题 ==============
    function startQuiz() {
        if (els.stepGender) {
            els.stepGender.style.display = 'none';
        }
        if (els.stepQuestion) {
            els.stepQuestion.style.display = 'block';
        }
        if (els.stepComplete) {
            els.stepComplete.style.display = 'none';
        }
        if (els.progressWrapper) {
            els.progressWrapper.style.display = 'block';
            // 设置进度条颜色渐变（绿→黄→红）
            if (els.progressFiller) {
                els.progressFiller.style.background =
                    'linear-gradient(90deg, #5ea67e 0%, #deb45c 50%, #e17055 100%)';
            }
        }
        renderQuestion(currentQuestion);
        requestWakeLock();
    }

    // ============== 渲染题目 ==============
    function renderQuestion(index) {
        var q = questions[index];
        if (!q) {
            return;
        }

        // 题号
        if (els.questionNumber) {
            els.questionNumber.textContent = '第 ' + (index + 1) + ' 题 / 共 ' + TOTAL + ' 题';
        }

        // 题干（API 字段 question_text）
        if (els.questionText) {
            els.questionText.textContent = q.question_text || q.text || '';
        }

        // 记录题目展示时间（用于计算响应时长）
        questionShowTime = Date.now();

        // 恢复已选状态
        clearSelection();
        var savedValue = getAnswerValue(index);
        if (savedValue !== null) {
            selectOption(savedValue, false);
        }

        // 清空描述
        if (els.scaleDescription) {
            els.scaleDescription.textContent = '';
        }

        // 更新进度
        updateProgress(index);

        // 上一题 / 下一题按钮
        if (els.prevBtn) {
            els.prevBtn.disabled = (index === 0);
        }
        if (els.nextBtn) {
            els.nextBtn.disabled = (getAnswerValue(index) === null);
        }

        saveProgress();
    }

    // ============== 5 点量表交互 ==============
    function initScaleOptions() {
        if (!els.scaleOptions) return;

        var options = els.scaleOptions.querySelectorAll('.scale-option');
        options.forEach(function (opt) {
            opt.addEventListener('click', function () {
                var value = parseInt(opt.getAttribute('data-value'), 10);

                // 计算响应时长
                var responseDuration = Date.now() - questionShowTime;

                // 粒子动画
                createParticleBurst(opt, scaleColors[String(value)] || '#9B7ED8');

                // 触觉反馈
                if (navigator.vibrate) {
                    navigator.vibrate(15);
                }

                // 选中视觉
                selectOption(value, true);

                // 记录答案（含响应时长）
                answers[currentQuestion] = {
                    question_id: questions[currentQuestion].id,
                    scale_value: value,
                    response_duration_ms: responseDuration
                };

                // 显示描述
                if (els.scaleDescription) {
                    els.scaleDescription.textContent = scaleLabels[String(value)];
                }

                // 更新下一题按钮状态
                if (els.nextBtn) {
                    els.nextBtn.disabled = false;
                }

                saveProgress();
                updateProgress(currentQuestion);

                // 延迟后自动进入下一题
                setTimeout(function () {
                    goNextQuestion();
                }, 350);
            });
        });
    }

    function selectOption(value, animate) {
        var opts = els.scaleOptions ? els.scaleOptions.querySelectorAll('.scale-option') : [];
        opts.forEach(function (opt) {
            var optValue = parseInt(opt.getAttribute('data-value'), 10);
            if (optValue === value) {
                opt.classList.add('selected');
            }
        });
    }

    function clearSelection() {
        var opts = els.scaleOptions ? els.scaleOptions.querySelectorAll('.scale-option') : [];
        opts.forEach(function (opt) {
            opt.classList.remove('selected');
        });
    }

    // ============== 粒子动画反馈 ==============
    function createParticleBurst(element, color) {
        var rect = element.getBoundingClientRect();
        var centerX = rect.left + rect.width / 2;
        var centerY = rect.top + rect.height / 2;
        var particleCount = 8;

        for (var i = 0; i < particleCount; i++) {
            (function (index) {
                var particle = document.createElement('div');
                particle.style.cssText =
                    'position:fixed;left:' + centerX + 'px;top:' + centerY + 'px;' +
                    'width:6px;height:6px;border-radius:50%;background:' + color + ';' +
                    'pointer-events:none;z-index:99999;' +
                    'transition:all 0.6s cubic-bezier(0.25,0.46,0.45,0.94);' +
                    'opacity:1;';
                document.body.appendChild(particle);

                var angle = (Math.PI * 2 * index) / particleCount;
                var distance = 25 + Math.random() * 25;
                var dx = Math.cos(angle) * distance;
                var dy = Math.sin(angle) * distance;

                requestAnimationFrame(function () {
                    particle.style.transform =
                        'translate(' + dx + 'px,' + dy + 'px) scale(0)';
                    particle.style.opacity = '0';
                });

                setTimeout(function () {
                    if (particle.parentNode) particle.remove();
                }, 600);
            })(i);
        }
    }

    // ============== 上一题 / 下一题 ==============
    function initNavButtons() {
        if (els.prevBtn) {
            els.prevBtn.addEventListener('click', function () {
                if (currentQuestion > 0) {
                    currentQuestion--;
                    renderQuestion(currentQuestion);
                }
            });
        }

        if (els.nextBtn) {
            els.nextBtn.addEventListener('click', function () {
                if (getAnswerValue(currentQuestion) !== null && currentQuestion < TOTAL) {
                    goNextQuestion();
                }
            });
        }
    }

    function goNextQuestion() {
        if (currentQuestion < TOTAL - 1) {
            currentQuestion++;
            renderQuestion(currentQuestion);
        } else {
            showComplete();
        }
    }

    // ============== 进度更新 ==============
    function updateProgress(index) {
        var answered = getAnsweredCount();
        var percent = TOTAL > 0 ? Math.round((answered / TOTAL) * 100) : 0;

        if (els.percentage) {
            els.percentage.textContent = percent + '%';
        }
        if (els.progressFiller) {
            els.progressFiller.style.width = percent + '%';
        }
        if (els.progressCount) {
            els.progressCount.textContent = answered + ' / ' + TOTAL;
        }

        // 更新剩余时间估算
        updateTimeEstimate(answered);
    }

    // ============== 剩余时间估算 ==============
    function updateTimeEstimate(answered) {
        // 计算已答题的平均响应时间
        var totalDuration = 0;
        var validCount = 0;
        for (var i = 0; i < answers.length; i++) {
            if (answers[i] && answers[i].response_duration_ms) {
                totalDuration += answers[i].response_duration_ms;
                validCount++;
            }
        }

        var estimateEl = document.getElementById('timeEstimate');
        if (!estimateEl) {
            // 动态创建时间估算元素
            estimateEl = document.createElement('div');
            estimateEl.id = 'timeEstimate';
            estimateEl.style.cssText =
                'margin-top:6px;text-align:right;font-size:12px;color:#9B9BAB;' +
                'font-family:Inter,"PingFang SC",sans-serif;';
            if (els.progressWrapper) {
                var percentEl = els.progressWrapper.querySelector('.progress-percent');
                if (percentEl && percentEl.parentNode) {
                    percentEl.parentNode.appendChild(estimateEl);
                }
            }
        }

        if (validCount > 0 && answered < TOTAL) {
            var avgMs = totalDuration / validCount;
            var remainingMs = avgMs * (TOTAL - answered);
            var remainingMin = Math.ceil(remainingMs / 60000);
            estimateEl.textContent = '预计剩余约 ' + remainingMin + ' 分钟';
        } else if (answered >= TOTAL) {
            estimateEl.textContent = '已完成全部题目';
        } else {
            estimateEl.textContent = '预计剩余约 10 分钟';
        }
    }

    // ============== 键盘支持 ==============
    function initKeyboard() {
        document.addEventListener('keydown', function (e) {
            if (!els.stepQuestion || els.stepQuestion.style.display === 'none') {
                return;
            }
            // 数字键 1-5 对应量表
            if (e.key >= '1' && e.key <= '5') {
                var idx = parseInt(e.key, 10) - 1;
                var opts = els.scaleOptions ? els.scaleOptions.querySelectorAll('.scale-option') : [];
                if (opts[idx]) {
                    opts[idx].click();
                }
            } else if (e.key === 'Backspace' && currentQuestion > 0) {
                e.preventDefault();
                if (els.prevBtn && !els.prevBtn.disabled) {
                    els.prevBtn.click();
                }
            } else if (e.key === 'ArrowRight' || e.key === 'Enter') {
                e.preventDefault();
                if (els.nextBtn && !els.nextBtn.disabled) {
                    els.nextBtn.click();
                }
            }
        });
    }

    // ============== 完成页 + 提交 ==============
    function showComplete() {
        if (els.stepQuestion) {
            els.stepQuestion.style.display = 'none';
        }
        if (els.stepComplete) {
            els.stepComplete.style.display = 'block';
        }
        if (els.progressWrapper) {
            els.progressWrapper.style.display = 'none';
        }

        // 计算用时
        var totalTime = Math.floor((Date.now() - startTimeMs) / 1000);
        var mins = Math.floor(totalTime / 60);
        var secs = totalTime % 60;
        if (els.completeTime) {
            els.completeTime.textContent = mins + ':' + String(secs).padStart(2, '0');
        }

        // 更新进度到 100%
        if (els.percentage) {
            els.percentage.textContent = '100%';
        }
        if (els.progressFiller) {
            els.progressFiller.style.width = '100%';
        }

        releaseWakeLock();
        clearProgress();

        // 提交测评答案到后端
        submitAssessment();
    }

    function submitAssessment() {
        if (isSubmitting) return;
        isSubmitting = true;

        // 构建提交数据
        var submitAnswers = answers
            .filter(function (a) { return a != null; })
            .map(function (a) {
                return {
                    question_id: a.question_id,
                    scale_value: a.scale_value,
                    response_duration_ms: a.response_duration_ms
                };
            });

        var submittedAt = new Date().toISOString();

        // 加载动画
        var progress = 0;
        var loadingTexts = [
            '分析中...',
            '计算大五人格得分...',
            '计算 RIASEC 兴趣码...',
            '匹配人格画像...',
            '生成报告...'
        ];
        var loadingInterval = setInterval(function () {
            progress += 2;
            if (progress > 90) progress = 90; // 等待 API 返回后再到 100%
            if (els.loadingFill) {
                els.loadingFill.style.width = progress + '%';
            }
            if (els.loadingText) {
                var textIndex = Math.min(Math.floor(progress / 20), loadingTexts.length - 1);
                els.loadingText.textContent = loadingTexts[textIndex];
            }
        }, 80);

        API.submitAssessment(submitAnswers, startedAt, submittedAt)
            .then(function (data) {
                clearInterval(loadingInterval);

                // 完成 loading 动画
                if (els.loadingFill) {
                    els.loadingFill.style.width = '100%';
                }
                if (els.loadingText) {
                    els.loadingText.textContent = '完成！';
                }

                // 保存 session_token
                if (data && data.session_token) {
                    API.setSessionToken(data.session_token);
                }

                // 显示查看结果按钮（带 session_token）
                if (els.viewResultBtn) {
                    var token = (data && data.session_token) || '';
                    els.viewResultBtn.href =
                        '/result-free/?session_token=' + encodeURIComponent(token);
                    els.viewResultBtn.style.display = 'inline-flex';
                }

                // 自动跳转（1.5 秒后）
                setTimeout(function () {
                    var token = (data && data.session_token) || '';
                    window.location.href =
                        '/result-free/?session_token=' + encodeURIComponent(token);
                }, 1500);
            })
            .catch(function (err) {
                clearInterval(loadingInterval);
                isSubmitting = false;

                if (els.loadingText) {
                    els.loadingText.textContent = '提交失败：' + (err.message || '未知错误');
                    els.loadingText.style.color = '#e17055';
                }
                if (els.loadingFill) {
                    els.loadingFill.style.width = '100%';
                    els.loadingFill.style.background = '#e17055';
                }

                // 显示重试按钮
                if (els.viewResultBtn) {
                    els.viewResultBtn.style.display = 'inline-flex';
                    els.viewResultBtn.querySelector('.button__text').textContent = '重试提交';
                    els.viewResultBtn.href = 'javascript:void(0);';
                    els.viewResultBtn.addEventListener('click', function retryClick(e) {
                        e.preventDefault();
                        els.viewResultBtn.removeEventListener('click', retryClick);
                        els.viewResultBtn.style.display = 'none';
                        if (els.loadingText) {
                            els.loadingText.style.color = '';
                        }
                        if (els.loadingFill) {
                            els.loadingFill.style.background = '';
                            els.loadingFill.style.width = '0%';
                        }
                        isSubmitting = false;
                        submitAssessment();
                    });
                }
            });
    }

    // ============== 屏幕常亮 ==============
    function requestWakeLock() {
        if ('wakeLock' in navigator) {
            navigator.wakeLock.request('screen').then(function (lock) {
                wakeLock = lock;
            }).catch(function () {
                // Wake Lock 不可用时静默失败
            });
        }
    }

    function releaseWakeLock() {
        if (wakeLock) {
            wakeLock.release().then(function () {
                wakeLock = null;
            }).catch(function () {});
        }
    }

    function initWakeLockVisibility() {
        document.addEventListener('visibilitychange', function () {
            if (document.visibilityState === 'visible' &&
                els.stepQuestion && els.stepQuestion.style.display !== 'none') {
                requestWakeLock();
            }
        });
    }

    // ============== 禁用浏览器返回键 ==============
    function preventBackButton() {
        window.history.pushState(null, '', window.location.href);
        window.addEventListener('popstate', function (e) {
            e.preventDefault();
            window.history.pushState(null, '', window.location.href);
        });
    }

    // ============== 错误提示 ==============
    function showError(message) {
        if (els.quizWrapper) {
            var errorEl = document.createElement('div');
            errorEl.style.cssText =
                'max-width:700px;margin:40px auto;padding:40px 24px;text-align:center;' +
                'background:#fff;border-radius:16px;box-shadow:0 2px 12px rgba(0,0,0,0.04);';
            errorEl.innerHTML =
                '<div style="font-size:48px;margin-bottom:16px;">!</div>' +
                '<h2 style="font-size:20px;font-weight:700;color:#2d2d3a;margin-bottom:12px;">加载失败</h2>' +
                '<p style="font-size:14px;color:#636e72;margin-bottom:24px;">' +
                (message || '无法加载题目，请检查网络后重试') + '</p>' +
                '<button onclick="location.reload()" style="padding:12px 32px;border:none;' +
                'border-radius:24px;background:linear-gradient(135deg,#9B7ED8,#B8A4E0);' +
                'color:#fff;font-size:15px;font-weight:700;cursor:pointer;">重新加载</button>';
            els.quizWrapper.innerHTML = '';
            els.quizWrapper.appendChild(errorEl);
        }
    }

    // ============== 初始化 ==============
    function init() {
        // 初始化交互事件
        initGenderSelection();
        initScaleOptions();
        initNavButtons();
        initKeyboard();
        initWakeLockVisibility();
        preventBackButton();

        // 尝试从缓存恢复
        var saved = loadProgress();
        if (saved && saved.questions && saved.questions.length > 0 && saved.gender) {
            // 有缓存：直接恢复
            questions = saved.questions;
            TOTAL = questions.length;
            currentQuestion = saved.currentIndex || 0;
            answers = saved.answers || new Array(TOTAL).fill(null);
            gender = saved.gender;
            startedAt = saved.startedAt || null;
            startTimeMs = startedAt ? new Date(startedAt).getTime() : Date.now();
            questionsLoaded = true;
            startQuiz();
            return;
        }

        // 无缓存或无 gender：从 API 加载题目
        if (saved && saved.questions && saved.questions.length > 0) {
            // 有题目缓存但没选性别
            questions = saved.questions;
            TOTAL = questions.length;
            questionsLoaded = true;
            return;
        }

        // 从 API 加载
        loadQuestions().then(function () {
            // 题目加载完成，等待用户选择性别
            // 缓存题目到 localStorage
            saveProgress();
        }).catch(function (err) {
            showError(err.message || '无法连接到服务器');
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
