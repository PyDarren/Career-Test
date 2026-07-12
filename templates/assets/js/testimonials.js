/**
 * testimonials.js — 首页用户评价轮播
 * 适配 16personalities 的 testimonial-carousel 结构
 * 支持自动播放、手动滑动、触摸滑动
 */
(function () {
    'use strict';

    var carousel = document.querySelector('testimonial-carousel.testimonials__carousel');
    if (!carousel) {
        return;
    }

    var testimonials = carousel.querySelectorAll('.testimonial');
    if (testimonials.length === 0) {
        return;
    }

    var total = testimonials.length;
    var current = 0;
    var autoplayInterval = null;
    var autoplayDelay = 5000;
    var touchStartX = 0;
    var touchEndX = 0;

    // 为每张卡片设置 flex 布局以支持轮播
    carousel.style.display = 'flex';
    carousel.style.overflow = 'hidden';
    carousel.style.position = 'relative';
    carousel.style.scrollSnapType = 'x mandatory';
    carousel.style.webkitOverflowScrolling = 'touch';

    testimonials.forEach(function (t) {
        t.style.flex = '0 0 100%';
        t.style.minWidth = '100%';
        t.style.scrollSnapAlign = 'start';
        t.style.transition = 'opacity 0.5s ease-in-out';
    });

    // 创建控制按钮容器
    var controls = document.createElement('div');
    controls.style.cssText = 'display:flex;justify-content:center;align-items:center;gap:12px;margin-top:24px;';

    // 上一条按钮
    var prevBtn = document.createElement('button');
    prevBtn.setAttribute('aria-label', '上一条评价');
    prevBtn.innerHTML = '&lsaquo;';
    prevBtn.style.cssText = 'width:40px;height:40px;border-radius:50%;border:2px solid #e7eae8;background:#fff;color:#6b7770;font-size:20px;cursor:pointer;display:flex;align-items:center;justify-content:center;line-height:1;transition:all 0.2s;';

    // 圆点容器
    var dotsContainer = document.createElement('div');
    dotsContainer.style.cssText = 'display:flex;gap:8px;';

    // 下一条按钮
    var nextBtn = document.createElement('button');
    nextBtn.setAttribute('aria-label', '下一条评价');
    nextBtn.innerHTML = '&rsaquo;';
    nextBtn.style.cssText = 'width:40px;height:40px;border-radius:50%;border:2px solid #e7eae8;background:#fff;color:#6b7770;font-size:20px;cursor:pointer;display:flex;align-items:center;justify-content:center;line-height:1;transition:all 0.2s;';

    controls.appendChild(prevBtn);
    controls.appendChild(dotsContainer);
    controls.appendChild(nextBtn);
    carousel.parentNode.insertBefore(controls, carousel.nextSibling);

    // 创建圆点
    function createDots() {
        dotsContainer.innerHTML = '';
        for (var i = 0; i < total; i++) {
            (function (index) {
                var dot = document.createElement('button');
                dot.setAttribute('aria-label', '第 ' + (index + 1) + ' 条评价');
                dot.style.cssText = 'width:10px;height:10px;border-radius:50%;border:0;background:#e7eae8;cursor:pointer;padding:0;transition:all 0.2s;';
                if (index === 0) {
                    dot.style.background = '#7559C3';
                    dot.style.width = '28px';
                    dot.style.borderRadius = '5px';
                }
                dot.addEventListener('click', function () {
                    goTo(index);
                    resetAutoplay();
                });
                dotsContainer.appendChild(dot);
            })(i);
        }
    }

    function updateDots() {
        var dots = dotsContainer.children;
        for (var i = 0; i < dots.length; i++) {
            if (i === current) {
                dots[i].style.background = '#7559C3';
                dots[i].style.width = '28px';
                dots[i].style.borderRadius = '5px';
            } else {
                dots[i].style.background = '#e7eae8';
                dots[i].style.width = '10px';
                dots[i].style.borderRadius = '50%';
            }
        }
    }

    function goTo(index) {
        current = (index + total) % total;
        carousel.scrollTo({
            left: current * carousel.offsetWidth,
            behavior: 'smooth'
        });
        updateDots();
    }

    function next() {
        goTo(current + 1);
    }

    function prev() {
        goTo(current - 1);
    }

    function startAutoplay() {
        stopAutoplay();
        autoplayInterval = setInterval(next, autoplayDelay);
    }

    function stopAutoplay() {
        if (autoplayInterval) {
            clearInterval(autoplayInterval);
            autoplayInterval = null;
        }
    }

    function resetAutoplay() {
        stopAutoplay();
        startAutoplay();
    }

    // 按钮事件
    nextBtn.addEventListener('click', function () {
        next();
        resetAutoplay();
    });

    prevBtn.addEventListener('click', function () {
        prev();
        resetAutoplay();
    });

    // 按钮悬停效果
    [prevBtn, nextBtn].forEach(function (btn) {
        btn.addEventListener('mouseenter', function () {
            btn.style.borderColor = '#7559C3';
            btn.style.color = '#7559C3';
        });
        btn.addEventListener('mouseleave', function () {
            btn.style.borderColor = '#e7eae8';
            btn.style.color = '#6b7770';
        });
    });

    // 触摸滑动
    carousel.addEventListener('touchstart', function (e) {
        touchStartX = e.touches[0].clientX;
        stopAutoplay();
    }, { passive: true });

    carousel.addEventListener('touchmove', function (e) {
        touchEndX = e.touches[0].clientX;
    }, { passive: true });

    carousel.addEventListener('touchend', function () {
        var diff = touchStartX - touchEndX;
        if (Math.abs(diff) > 50) {
            if (diff > 0) {
                next();
            } else {
                prev();
            }
        }
        // 根据滚动位置更新当前索引
        current = Math.round(carousel.scrollLeft / carousel.offsetWidth);
        updateDots();
        startAutoplay();
    });

    // 鼠标悬停暂停
    carousel.addEventListener('mouseenter', stopAutoplay);
    carousel.addEventListener('mouseleave', startAutoplay);

    // 键盘支持
    document.addEventListener('keydown', function (e) {
        if (e.key === 'ArrowLeft') {
            prev();
            resetAutoplay();
        } else if (e.key === 'ArrowRight') {
            next();
            resetAutoplay();
        }
    });

    // 滚动同步圆点
    var scrollTimer = null;
    carousel.addEventListener('scroll', function () {
        if (scrollTimer) {
            clearTimeout(scrollTimer);
        }
        scrollTimer = setTimeout(function () {
            current = Math.round(carousel.scrollLeft / carousel.offsetWidth);
            updateDots();
        }, 150);
    });

    // 初始化
    createDots();

    // 仅在可见时启动自动播放
    if ('IntersectionObserver' in window) {
        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    startAutoplay();
                } else {
                    stopAutoplay();
                }
            });
        }, { threshold: 0.3 });
        observer.observe(carousel);
    } else {
        startAutoplay();
    }
})();
