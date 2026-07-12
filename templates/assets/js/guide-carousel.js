/**
 * guide-carousel.js — 测评引导页步骤轮播
 * 支持左右切换、触摸滑动、键盘、自动进度条演示
 */
(function () {
    'use strict';

    var track = document.getElementById('guideTrack');
    if (!track) {
        return;
    }

    var slides = track.querySelectorAll('.guide-slide');
    var total = slides.length;
    var current = 0;
    var touchStartX = 0;
    var touchEndX = 0;

    var prevBtn = document.getElementById('guidePrev');
    var nextBtn = document.getElementById('guideNext');
    var dotsContainer = document.getElementById('guideDots');

    // 初始化：显示第一张
    function init() {
        slides[0].classList.add('active');
        createDots();
        updateControls();
        startProgressDemo();
    }

    // 创建圆点
    function createDots() {
        if (!dotsContainer) {
            return;
        }
        dotsContainer.innerHTML = '';
        for (var i = 0; i < total; i++) {
            (function (index) {
                var dot = document.createElement('button');
                dot.className = 'guide-carousel__dot';
                dot.setAttribute('aria-label', '第 ' + (index + 1) + ' 步');
                if (index === 0) {
                    dot.classList.add('active');
                }
                dot.addEventListener('click', function () {
                    goTo(index);
                });
                dotsContainer.appendChild(dot);
            })(i);
        }
    }

    // 更新圆点状态
    function updateDots() {
        var dots = dotsContainer.querySelectorAll('.guide-carousel__dot');
        for (var i = 0; i < dots.length; i++) {
            if (i === current) {
                dots[i].classList.add('active');
            } else {
                dots[i].classList.remove('active');
            }
        }
    }

    // 更新按钮状态
    function updateControls() {
        if (prevBtn) {
            prevBtn.disabled = (current === 0);
        }
        if (nextBtn) {
            // 最后一步时，next 按钮变为隐藏或改为完成图标
            if (current === total - 1) {
                nextBtn.style.opacity = '0.3';
                nextBtn.disabled = true;
            } else {
                nextBtn.style.opacity = '1';
                nextBtn.disabled = false;
            }
        }
    }

    // 切换到指定幻灯片
    function goTo(index) {
        if (index < 0 || index >= total) {
            return;
        }
        slides[current].classList.remove('active');
        current = index;
        slides[current].classList.add('active');
        updateDots();
        updateControls();

        // 如果是第 3 步，重新启动进度条演示
        if (current === 2) {
            startProgressDemo();
        }
    }

    function next() {
        if (current < total - 1) {
            goTo(current + 1);
        }
    }

    function prev() {
        if (current > 0) {
            goTo(current - 1);
        }
    }

    // 按钮事件
    if (nextBtn) {
        nextBtn.addEventListener('click', next);
    }
    if (prevBtn) {
        prevBtn.addEventListener('click', prev);
    }

    // 触摸滑动
    track.addEventListener('touchstart', function (e) {
        touchStartX = e.touches[0].clientX;
    }, { passive: true });

    track.addEventListener('touchmove', function (e) {
        touchEndX = e.touches[0].clientX;
    }, { passive: true });

    track.addEventListener('touchend', function () {
        var diff = touchStartX - touchEndX;
        if (Math.abs(diff) > 50) {
            if (diff > 0) {
                next();
            } else {
                prev();
            }
        }
    });

    // 键盘支持
    document.addEventListener('keydown', function (e) {
        if (e.key === 'ArrowLeft') {
            prev();
        } else if (e.key === 'ArrowRight') {
            next();
        }
    });

    // ============== 进度条演示动画 ==============
    var progressFill = document.getElementById('progressDemoFill');
    var progressPercent = document.getElementById('progressDemoPercent');
    var progressInterval = null;

    function startProgressDemo() {
        if (!progressFill || !progressPercent) {
            return;
        }
        stopProgressDemo();

        var progress = 0;
        progressFill.style.width = '0%';
        progressPercent.textContent = '0%';

        progressInterval = setInterval(function () {
            progress += 1;
            if (progress > 100) {
                progress = 0;
            }
            progressFill.style.width = progress + '%';
            progressPercent.textContent = progress + '%';
        }, 100);
    }

    function stopProgressDemo() {
        if (progressInterval) {
            clearInterval(progressInterval);
            progressInterval = null;
        }
    }

    // ============== 跳过引导选项 ==============
    var skipCheckbox = document.getElementById('skipNextTime');
    if (skipCheckbox) {
        // 读取本地存储中的偏好
        var savedPref = localStorage.getItem('career_test_skip_guide');
        if (savedPref === 'true') {
            skipCheckbox.checked = true;
        }

        skipCheckbox.addEventListener('change', function () {
            localStorage.setItem('career_test_skip_guide', skipCheckbox.checked ? 'true' : 'false');
        });
    }

    // 顶部跳过按钮
    var skipGuideBtn = document.getElementById('skipGuide');
    if (skipGuideBtn) {
        skipGuideBtn.addEventListener('click', function (e) {
            // 直接跳转到测评页（这里用首页 CTA 区作演示）
            // 实际项目中应跳转到答题页
            e.preventDefault();
            var ctaSection = document.getElementById('go');
            if (ctaSection) {
                ctaSection.scrollIntoView({ behavior: 'smooth' });
            }
        });
    }

    // 正式开始按钮
    var startTestBtn = document.getElementById('startTest');
    if (startTestBtn) {
        startTestBtn.addEventListener('click', function (e) {
            e.preventDefault();
            // 实际项目中跳转到答题页
            // window.location.href = 'question.html';
            alert('即将进入答题页（演示）');
        });
    }

    // 初始化
    init();
})();
