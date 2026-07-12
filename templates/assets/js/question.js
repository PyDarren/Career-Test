/**
 * question.js — 答题页交互逻辑（16p 风格）
 * 流程：性别选择 → 86 题 7 点量表 → 完成页
 */
(function () {
    'use strict';

    // ============== 题目数据（16p 原版 60 题中文翻译） ==============
    var questions = [
        { text: '你经常主动结交新朋友。' },
        { text: '复杂新奇的想法比简单直接的更让你兴奋。' },
        { text: '你通常更容易被情感共鸣说服，而非事实论据。' },
        { text: '你的生活和工作空间整洁有序。' },
        { text: '即使压力很大，你通常也能保持冷静。' },
        { text: '向陌生人推广自己或建立人脉让你感到畏惧。' },
        { text: '你能有效地安排任务优先级，常在截止日期前完成。' },
        { text: '人们的故事和情感比数字或数据更能打动你。' },
        { text: '你喜欢使用日程表和清单等工具来组织事务。' },
        { text: '即使一个小错误也会让你怀疑自己的整体能力和知识。' },
        { text: '你能自如地走向你感兴趣的人并主动开启对话。' },
        { text: '你对讨论创意作品的各种解读不感兴趣。' },
        { text: '在决定行动方案时，你优先考虑事实而非他人感受。' },
        { text: '你经常让一天自然展开，不做任何安排。' },
        { text: '你很少担心自己给遇到的人留下好印象。' },
        { text: '你喜欢参与团队活动。' },
        { text: '你喜欢尝试新颖且未经验证的方法。' },
        { text: '你优先考虑保持敏感，而非完全诚实。' },
        { text: '你主动寻求新的体验和知识领域来探索。' },
        { text: '你容易担心事情会变糟。' },
        { text: '你比群体活动更喜欢独处的爱好或活动。' },
        { text: '你无法想象自己以写小说为生。' },
        { text: '你倾向于高效决策，即使意味着忽略一些情感因素。' },
        { text: '你倾向于先完成琐事再放松休息。' },
        { text: '在分歧中，你优先考虑证明自己的观点，而非维护他人感受。' },
        { text: '在社交场合，你通常等别人先自我介绍。' },
        { text: '你的情绪变化很快。' },
        { text: '你不轻易被情感论点动摇。' },
        { text: '你经常在最后一刻才完成任务。' },
        { text: '你喜欢讨论伦理两难问题。' },
        { text: '你通常更喜欢和他人在一起，而非独处。' },
        { text: '当讨论变得高度理论化时，你会感到无聊或失去兴趣。' },
        { text: '当事实与情感冲突时，你通常发现自己跟随内心。' },
        { text: '你难以保持一致的工作或学习计划。' },
        { text: '你很少事后质疑自己做出的选择。' },
        { text: '你的朋友会形容你活泼外向。' },
        { text: '你被各种创意表达形式所吸引，比如写作。' },
        { text: '你通常基于客观事实而非情感印象做选择。' },
        { text: '你喜欢每天都有一个待办清单。' },
        { text: '你很少感到不安全。' },
        { text: '你避免打电话。' },
        { text: '你享受探索陌生的想法和观点。' },
        { text: '你能轻松与刚认识的人建立联系。' },
        { text: '如果计划被打断，你的首要任务是尽快回到正轨。' },
        { text: '你仍然会被很久以前犯的错误困扰。' },
        { text: '你对讨论世界未来面貌的理论不太感兴趣。' },
        { text: '你的情绪控制你，多于你控制情绪。' },
        { text: '做决定时，你更关注受影响的人可能的感觉，而非什么最合理或高效。' },
        { text: '你的个人工作风格更接近自发性的能量爆发，而非有组织的持续努力。' },
        { text: '当有人高度评价你时，你会想他们多久会对你失望。' },
        { text: '你喜欢一份大部分时间独自工作的工作。' },
        { text: '你认为思考抽象的哲学问题是浪费时间。' },
        { text: '相比安静私密的地方，你更被繁忙喧闹的氛围吸引。' },
        { text: '如果某个决定感觉对，你常无需进一步证明就付诸行动。' },
        { text: '你经常感到不堪重负。' },
        { text: '你做事有条不紊，不跳过任何步骤。' },
        { text: '你更喜欢需要创意解决方案的任务，而非遵循具体步骤的任务。' },
        { text: '做选择时，你更可能依赖情感直觉而非逻辑推理。' },
        { text: '你在截止日期方面有困难。' },
        { text: '你相信事情会顺利解决。' },
        // ====== 扩展题目（61-86，对齐算法文档 86 题结构） ======
        { text: '在团队讨论中，你通常是发言最多的人之一。' },
        { text: '你喜欢和一群人一起度过周末，而非独自在家。' },
        { text: '经历了大量社交活动后，你需要独处一段时间来恢复精力。' },
        { text: '你很容易注意到环境中的细微变化。' },
        { text: '你更相信亲眼所见的事实，而非直觉的预感。' },
        { text: '你经常沉浸在对未来的想象中，以至于忽略了眼前的事。' },
        { text: '做重大决定时，列出利弊清单比听从内心更重要。' },
        { text: '当需要批评他人时，你会小心翼翼地维护对方的自尊。' },
        { text: '你认为团队的和谐比任务的效率更值得优先考虑。' },
        { text: '旅行前，你会详细规划每一天的行程和住宿。' },
        { text: '你喜欢同时开展多个项目，在不同任务间灵活切换。' },
        { text: '你对不确定性有较高的容忍度，不需要所有事情都有明确答案。' },
        { text: '你对自己的判断力有十足的信心。' },
        { text: '在重要场合发言前，你会感到明显的心跳加速。' },
        { text: '你很少对自己的重要决策感到后悔。' },
        { text: '你常常反复检查已经完成的工作，担心出错。' },
        { text: '你认为职业成就是衡量人生价值最重要的标准。' },
        { text: '如果能选择，你更愿意拥有一份轻松、收入一般但时间自由的工作。' },
        { text: '你愿意为了职业晋升而牺牲与家人相处的时间。' },
        { text: '工作之外的兴趣爱好对你来说比职业发展更重要。' },
        { text: '你偶尔也会对朋友爽约。' },
        { text: '请在本题选择"有点同意"，以确认你在认真阅读每道题目。' },
        { text: '你有时也会为了省事而不完全遵守规则。' },
        { text: '在本次测评中你一直保持专注，认真作答。' },
        { text: '字母"S"在字母"T"之前。（请选"强烈同意"）' },
        { text: '你偶尔也会对亲近的人发脾气。' }
    ];

    var TOTAL = questions.length;

    // ============== 状态 ==============
    var currentQuestion = 0;
    var answers = new Array(TOTAL).fill(null);
    var gender = null;
    var startTime = Date.now();
    var wakeLock = null;

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
        '-3': '强烈不同意',
        '-2': '不同意',
        '-1': '有点不同意',
        '0': '既不同意也不反对',
        '1': '有点同意',
        '2': '同意',
        '3': '强烈同意'
    };

    // ============== 本地存储 — 断点续测 ==============
    var STORAGE_KEY = 'career_test_quiz_progress';

    function saveProgress() {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify({
                currentQuestion: currentQuestion,
                answers: answers,
                gender: gender,
                startTime: startTime,
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
        localStorage.removeItem(STORAGE_KEY);
    }

    // 检查断点续测
    var saved = loadProgress();
    if (saved && saved.answers && saved.answers.length === TOTAL && saved.gender) {
        currentQuestion = saved.currentQuestion || 0;
        answers = saved.answers;
        gender = saved.gender;
        startTime = saved.startTime || Date.now();
        // 直接跳到答题
        startQuiz();
    }

    // ============== 性别选择 ==============
    var genderOptions = document.querySelectorAll('.gender-option');
    genderOptions.forEach(function (opt) {
        opt.addEventListener('click', function () {
            gender = opt.getAttribute('data-gender');
            // 触觉反馈
            if (navigator.vibrate) {
                navigator.vibrate(20);
            }
            startQuiz();
        });
    });

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

        // 题干
        if (els.questionText) {
            els.questionText.textContent = q.text;
        }

        // 恢复已选状态
        clearSelection();
        if (answers[index] !== null) {
            selectOption(answers[index], false);
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
            els.nextBtn.disabled = (answers[index] === null);
        }

        saveProgress();
    }

    // ============== 7 点量表交互 ==============
    if (els.scaleOptions) {
        var options = els.scaleOptions.querySelectorAll('.scale-option');
        options.forEach(function (opt) {
            opt.addEventListener('click', function () {
                var value = parseInt(opt.getAttribute('data-value'), 10);
                selectOption(value, true);
                answers[currentQuestion] = value;

                // 触觉反馈
                if (navigator.vibrate) {
                    navigator.vibrate(15);
                }

                // 显示描述
                if (els.scaleDescription) {
                    els.scaleDescription.textContent = scaleLabels[String(value)];
                }

                saveProgress();

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

    // ============== 上一题 / 下一题 ==============
    if (els.prevBtn) {
        els.prevBtn.addEventListener('click', function () {
            if (currentQuestion > 0) {
                currentQuestion--;
                renderQuestion(currentQuestion);
            }
        });
    }

    function goNextQuestion() {
        if (currentQuestion < TOTAL - 1) {
            currentQuestion++;
            renderQuestion(currentQuestion);
        } else {
            showComplete();
        }
    }

    if (els.nextBtn) {
        els.nextBtn.addEventListener('click', function () {
            if (answers[currentQuestion] !== null && currentQuestion < TOTAL) {
                goNextQuestion();
            }
        });
    }

    // ============== 进度更新（基于已答题数 ×× 86） ==============
    function updateProgress(index) {
        var answered = answers.filter(function (a) { return a !== null; }).length;
        var percent = Math.round((answered / TOTAL) * 100);
        if (els.percentage) {
            els.percentage.textContent = percent + '%';
        }
        if (els.progressFiller) {
            els.progressFiller.style.width = percent + '%';
        }
        if (els.progressCount) {
            els.progressCount.textContent = answered + ' / ' + TOTAL;
        }
    }

    // ============== 键盘支持 ==============
    document.addEventListener('keydown', function (e) {
        if (els.stepQuestion.style.display === 'none') {
            return;
        }
        // 数字键 1-7 对应量表
        if (e.key >= '1' && e.key <= '7') {
            var value = parseInt(e.key, 10) - 4; // 1→-3, 4→0, 7→3
            var opts = els.scaleOptions ? els.scaleOptions.querySelectorAll('.scale-option') : [];
            opts[value + 3].click();
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

    // ============== 完成页 ==============
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
        var totalTime = Math.floor((Date.now() - startTime) / 1000);
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

        // 模拟加载
        var progress = 0;
        var loadingTexts = ['分析中...', '计算维度得分...', '匹配人格类型...', '生成报告...'];
        var loadingInterval = setInterval(function () {
            progress += 2;
            if (els.loadingFill) {
                els.loadingFill.style.width = progress + '%';
            }
            if (els.loadingText) {
                var textIndex = Math.min(Math.floor(progress / 25), loadingTexts.length - 1);
                els.loadingText.textContent = loadingTexts[textIndex];
            }
            if (progress >= 100) {
                clearInterval(loadingInterval);
                if (els.loadingText) {
                    els.loadingText.textContent = '完成！';
                }
                if (els.viewResultBtn) {
                    els.viewResultBtn.style.display = 'inline-flex';
                }
                clearProgress();
            }
        }, 80);
    }

    // ============== 屏幕常亮 ==============
    async function requestWakeLock() {
        try {
            if ('wakeLock' in navigator) {
                wakeLock = await navigator.wakeLock.request('screen');
            }
        } catch (e) {
            // Wake Lock 不可用时静默失败
        }
    }

    function releaseWakeLock() {
        if (wakeLock) {
            wakeLock.release().then(function () {
                wakeLock = null;
            }).catch(function () {});
        }
    }

    document.addEventListener('visibilitychange', function () {
        if (document.visibilityState === 'visible' && els.stepQuestion.style.display !== 'none') {
            requestWakeLock();
        }
    });

    // ============== 禁用浏览器返回键 ==============
    window.history.pushState(null, '', window.location.href);
    window.addEventListener('popstate', function (e) {
        e.preventDefault();
        window.history.pushState(null, '', window.location.href);
    });

})();
