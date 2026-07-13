/**
 * question.js — 答题页交互逻辑（16p 风格）
 * 流程：性别选择 → 80 题 5 点李克特量表 → 完成页
 * 题项来源：IPIP-50（大五人格，公有领域）+ RIASEC-30（自主编写，基于霍兰德理论）
 */
(function () {
    'use strict';

    // ============== 题目数据（IPIP-50 大五人格 + RIASEC-30 职业兴趣） ==============
    // dimension: O=开放性, C=尽责性, E=外向性, A=宜人性, N=神经质
    //            R=现实型, I=研究型, A=艺术型, S=社会型, E=企业型, C=常规型
    // reverse: true 表示反向计分（1↔5, 2↔4, 3↔3）
    var questions = [
        // ====== IPIP-50 大五人格（1-50题） ======
        // --- 开放性 O（1-10） ---
        { text: '我喜欢思考新的想法和可能性。', dim: 'O', reverse: false },
        { text: '我对艺术和美有较强的感受力。', dim: 'O', reverse: false },
        { text: '我喜欢探索不熟悉的概念和领域。', dim: 'O', reverse: false },
        { text: '我经常反思人生的意义和价值。', dim: 'O', reverse: false },
        { text: '面对新事物，我通常充满好奇心。', dim: 'O', reverse: false },
        { text: '我更倾向于按部就班而非尝试新方法。', dim: 'O', reverse: true },
        { text: '我对讨论抽象的哲学问题不感兴趣。', dim: 'O', reverse: true },
        { text: '我认为思考理论问题是浪费时间。', dim: 'O', reverse: true },
        { text: '比起阅读，我更喜欢动手操作。', dim: 'O', reverse: true },
        { text: '我对各种创意表达形式不感兴趣。', dim: 'O', reverse: true },
        // --- 尽责性 C（11-20） ---
        { text: '我会提前制定计划并按计划执行。', dim: 'C', reverse: false },
        { text: '我做事有条不紊，不跳过任何步骤。', dim: 'C', reverse: false },
        { text: '我能有效地安排任务优先级，常在截止日期前完成。', dim: 'C', reverse: false },
        { text: '我喜欢每天都有一个待办清单。', dim: 'C', reverse: false },
        { text: '我会按时完成自己承诺的任务。', dim: 'C', reverse: false },
        { text: '我经常在最后一刻才完成任务。', dim: 'C', reverse: true },
        { text: '我的生活和工作空间比较杂乱。', dim: 'C', reverse: true },
        { text: '我难以保持一致的工作或学习计划。', dim: 'C', reverse: true },
        { text: '我经常让一天自然展开，不做任何安排。', dim: 'C', reverse: true },
        { text: '我在截止日期方面有困难。', dim: 'C', reverse: true },
        // --- 外向性 E（21-30） ---
        { text: '在社交场合中我通常是主动交谈的人。', dim: 'E', reverse: false },
        { text: '我经常主动结交新朋友。', dim: 'E', reverse: false },
        { text: '我喜欢参与团队活动和集体聚会。', dim: 'E', reverse: false },
        { text: '我能轻松与刚认识的人建立联系。', dim: 'E', reverse: false },
        { text: '我比群体活动更喜欢独处的爱好。', dim: 'E', reverse: true },
        { text: '向陌生人推广自己让我感到畏惧。', dim: 'E', reverse: true },
        { text: '在社交场合，我通常等别人先自我介绍。', dim: 'E', reverse: true },
        { text: '我喜欢一份大部分时间独自工作的工作。', dim: 'E', reverse: true },
        { text: '经历了大量社交活动后，我需要独处来恢复精力。', dim: 'E', reverse: true },
        { text: '我避免打电话。', dim: 'E', reverse: true },
        // --- 宜人性 A（31-40） ---
        { text: '即使意见不同，我也能理解对方的立场。', dim: 'A', reverse: false },
        { text: '当需要批评他人时，我会小心翼翼地维护对方的自尊。', dim: 'A', reverse: false },
        { text: '我相信大多数人本质上是善良的。', dim: 'A', reverse: false },
        { text: '我乐于帮助他人，即使需要付出额外精力。', dim: 'A', reverse: false },
        { text: '在分歧中，我优先考虑维护他人感受。', dim: 'A', reverse: false },
        { text: '在决定行动方案时，我优先考虑事实而非他人感受。', dim: 'A', reverse: true },
        { text: '我不轻易被情感论点动摇。', dim: 'A', reverse: true },
        { text: '我认为团队的和谐比任务的效率更值得优先考虑。', dim: 'A', reverse: false },
        { text: '如果某个决定感觉对，我常无需进一步证明就付诸行动。', dim: 'A', reverse: true },
        { text: '做决定时，我更关注什么最合理而非受影响的人的感受。', dim: 'A', reverse: true },
        // --- 神经质 N（41-50） ---
        { text: '我经常感到焦虑或不安。', dim: 'N', reverse: false },
        { text: '即使一个小错误也会让我怀疑自己的整体能力。', dim: 'N', reverse: false },
        { text: '我的情绪变化很快。', dim: 'N', reverse: false },
        { text: '我容易担心事情会变糟。', dim: 'N', reverse: false },
        { text: '我经常感到不堪重负。', dim: 'N', reverse: false },
        { text: '即使压力很大，我通常也能保持冷静。', dim: 'N', reverse: true },
        { text: '我很少担心自己给遇到的人留下好印象。', dim: 'N', reverse: true },
        { text: '我很少感到不安全。', dim: 'N', reverse: true },
        { text: '我相信事情会顺利解决。', dim: 'N', reverse: true },
        { text: '我对自己的判断力有十足的信心。', dim: 'N', reverse: true },

        // ====== RIASEC-30 职业兴趣（51-80题） ======
        // --- 现实型 R（51-55） ---
        { text: '我喜欢动手修理或组装物品。', dim: 'R', reverse: false },
        { text: '操作工具或机械设备让我感到自在。', dim: 'R', reverse: false },
        { text: '我喜欢户外活动或体力劳动。', dim: 'R', reverse: false },
        { text: '我倾向于通过实际操作来学习新技能。', dim: 'R', reverse: false },
        { text: '我对机械原理或工程结构有浓厚兴趣。', dim: 'R', reverse: false },
        // --- 研究型 I（56-60） ---
        { text: '我喜欢分析复杂数据寻找规律。', dim: 'I', reverse: false },
        { text: '面对难题，我会深入研究直到找到答案。', dim: 'I', reverse: false },
        { text: '我对科学发现和学术研究充满热情。', dim: 'I', reverse: false },
        { text: '我喜欢阅读专业文献或学术文章。', dim: 'I', reverse: false },
        { text: '我享受用逻辑推理解决复杂问题的过程。', dim: 'I', reverse: false },
        // --- 艺术型 A（61-65） ---
        { text: '我喜欢通过创意作品表达自我。', dim: 'A', reverse: false },
        { text: '我经常有灵感涌现，想要创作些什么。', dim: 'A', reverse: false },
        { text: '我对音乐、绘画或文学有较强的鉴赏力。', dim: 'A', reverse: false },
        { text: '比起遵循规则，我更喜欢自由发挥创意。', dim: 'A', reverse: false },
        { text: '我享受在设计中追求美感的过程。', dim: 'A', reverse: false },
        // --- 社会型 S（66-70） ---
        { text: '帮助他人成长让我感到充实。', dim: 'S', reverse: false },
        { text: '我善于倾听并理解他人的困扰。', dim: 'S', reverse: false },
        { text: '我喜欢参与志愿服务或公益活动。', dim: 'S', reverse: false },
        { text: '在团队中，我经常扮演协调者和支持者的角色。', dim: 'S', reverse: false },
        { text: '能够教导或指导他人让我有成就感。', dim: 'S', reverse: false },
        // --- 企业型 E（71-75） ---
        { text: '我喜欢带领团队达成目标。', dim: 'E', reverse: false },
        { text: '我善于说服他人接受我的观点。', dim: 'E', reverse: false },
        { text: '我对商业机会和市场趋势有敏锐的嗅觉。', dim: 'E', reverse: false },
        { text: '我喜欢承担有挑战性的领导任务。', dim: 'E', reverse: false },
        { text: '在竞争中获胜让我感到兴奋和满足。', dim: 'E', reverse: false },
        // --- 常规型 C（76-80） ---
        { text: '我喜欢整理信息让一切井井有条。', dim: 'C', reverse: false },
        { text: '我对数据和细节有较高的敏感度。', dim: 'C', reverse: false },
        { text: '我喜欢按照既定流程和规范完成任务。', dim: 'C', reverse: false },
        { text: '整理文件和归档资料让我感到满足。', dim: 'C', reverse: false },
        { text: '我擅长制定预算并严格按预算执行。', dim: 'C', reverse: false }
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
        '1': '非常不符合',
        '2': '比较不符合',
        '3': '不确定',
        '4': '比较符合',
        '5': '非常符合'
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
        // 数字键 1-5 对应量表
        if (e.key >= '1' && e.key <= '5') {
            var idx = parseInt(e.key, 10) - 1; // 1→index 0, 5→index 4
            var opts = els.scaleOptions ? els.scaleOptions.querySelectorAll('.scale-option') : [];
            opts[idx].click();
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
        var loadingTexts = ['分析中...', '计算大五人格得分...', '计算 RIASEC 兴趣码...', '匹配人格画像...', '生成报告...'];
        var loadingInterval = setInterval(function () {
            progress += 2;
            if (els.loadingFill) {
                els.loadingFill.style.width = progress + '%';
            }
            if (els.loadingText) {
                var textIndex = Math.min(Math.floor(progress / 20), loadingTexts.length - 1);
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
