/**
 * result-free.js — 免费结果页交互脚本
 * 功能：雷达图绘制、昵称同步、模板切换、卡片保存、分享埋点
 */

(function () {
    'use strict';

    // ============== 模拟数据（静态页面用，后端接入后替换为 API 返回） ==============
    var resultData = {
        code: 'INTJ-A-C',
        title: '战略师',
        slogan: '智慧的先锋 · 未来的建筑师',
        summary: '你是一个拥有深远洞察力的战略思考者，能够将抽象概念转化为系统化行动方案，在复杂环境中始终保持冷静与方向感。',
        dimensions: [
            { label: '外倾 (E)', value: 32, color: '#5a96b1' },
            { label: '直觉 (N)', value: 78, color: '#87699a' },
            { label: '思考 (T)', value: 85, color: '#deb45c' },
            { label: '判断 (J)', value: 71, color: '#5ea67e' }
        ],
        rarity: '2.70%',
        rarityLabel: '超稀有',
        famousPeople: '马斯克 · 尼采',
        bestPartners: ['ENFP', 'ENTP']
    };

    // ============== DOM 元素引用 ==============
    var els = {
        radarCanvas: document.getElementById('radarCanvas'),
        nicknameInput: document.getElementById('nicknameInput'),
        cardNickname: document.getElementById('cardNickname'),
        templatePicker: document.getElementById('templatePicker'),
        certCard: document.getElementById('certCard'),
        saveCardBtn: document.getElementById('saveCardBtn'),
        shareBtns: document.querySelectorAll('.share-btn')
    };

    // ============== 1. 雷达图绘制 ==============
    function drawRadar() {
        var canvas = els.radarCanvas;
        if (!canvas) return;

        var ctx = canvas.getContext('2d');
        var dpr = window.devicePixelRatio || 1;
        var size = 320;
        canvas.width = size * dpr;
        canvas.height = size * dpr;
        canvas.style.width = size + 'px';
        canvas.style.height = size + 'px';
        ctx.scale(dpr, dpr);

        var cx = size / 2;
        var cy = size / 2;
        var maxRadius = 110;
        var sides = 4;
        var angleStep = (Math.PI * 2) / sides;
        var startAngle = -Math.PI / 2;

        // 背景网格（4 层同心多边形）
        ctx.strokeStyle = '#e7eae8';
        ctx.lineWidth = 1;
        for (var layer = 1; layer <= 4; layer++) {
            var r = (maxRadius / 4) * layer;
            ctx.beginPath();
            for (var i = 0; i <= sides; i++) {
                var angle = startAngle + angleStep * i;
                var x = cx + Math.cos(angle) * r;
                var y = cy + Math.sin(angle) * r;
                if (i === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            }
            ctx.stroke();
        }

        // 轴线
        ctx.strokeStyle = '#e7eae8';
        for (var j = 0; j < sides; j++) {
            var a = startAngle + angleStep * j;
            ctx.beginPath();
            ctx.moveTo(cx, cy);
            ctx.lineTo(cx + Math.cos(a) * maxRadius, cy + Math.sin(a) * maxRadius);
            ctx.stroke();
        }

        // 数据填充
        ctx.beginPath();
        for (var k = 0; k < sides; k++) {
            var dataAngle = startAngle + angleStep * k;
            var dataRadius = (resultData.dimensions[k].value / 100) * maxRadius;
            var px = cx + Math.cos(dataAngle) * dataRadius;
            var py = cy + Math.sin(dataAngle) * dataRadius;
            if (k === 0) ctx.moveTo(px, py);
            else ctx.lineTo(px, py);
        }
        ctx.closePath();

        // 渐变填充
        var gradient = ctx.createLinearGradient(cx - maxRadius, cy - maxRadius, cx + maxRadius, cy + maxRadius);
        gradient.addColorStop(0, 'rgba(155, 126, 216, 0.25)');
        gradient.addColorStop(1, 'rgba(90, 150, 177, 0.25)');
        ctx.fillStyle = gradient;
        ctx.fill();

        // 数据边线
        ctx.strokeStyle = '#9B7ED8';
        ctx.lineWidth = 2;
        ctx.stroke();

        // 数据点
        for (var m = 0; m < sides; m++) {
            var ptAngle = startAngle + angleStep * m;
            var ptRadius = (resultData.dimensions[m].value / 100) * maxRadius;
            var ptX = cx + Math.cos(ptAngle) * ptRadius;
            var ptY = cy + Math.sin(ptAngle) * ptRadius;

            ctx.beginPath();
            ctx.arc(ptX, ptY, 5, 0, Math.PI * 2);
            ctx.fillStyle = resultData.dimensions[m].color;
            ctx.fill();
            ctx.strokeStyle = '#fff';
            ctx.lineWidth = 2;
            ctx.stroke();
        }

        // 标签
        ctx.font = '600 13px Inter, "PingFang SC", sans-serif';
        ctx.fillStyle = '#2d2d3a';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        for (var n = 0; n < sides; n++) {
            var lblAngle = startAngle + angleStep * n;
            var lblRadius = maxRadius + 25;
            var lblX = cx + Math.cos(lblAngle) * lblRadius;
            var lblY = cy + Math.sin(lblAngle) * lblRadius;
            ctx.fillText(resultData.dimensions[n].label, lblX, lblY);
        }
    }

    // ============== 2. 昵称同步 ==============
    function initNicknameSync() {
        if (!els.nicknameInput || !els.cardNickname) return;

        els.nicknameInput.addEventListener('input', function () {
            var val = els.nicknameInput.value.trim() || '匿名用户001';
            els.cardNickname.textContent = val;
        });
    }

    // ============== 3. 模板切换 ==============
    function initTemplateSwitch() {
        if (!els.templatePicker || !els.certCard) return;

        els.templatePicker.addEventListener('click', function (e) {
            var btn = e.target.closest('.template-btn');
            if (!btn) return;

            // 更新按钮状态
            els.templatePicker.querySelectorAll('.template-btn').forEach(function (b) {
                b.classList.remove('template-btn--active');
            });
            btn.classList.add('template-btn--active');

            // 更新卡片模板
            var template = btn.getAttribute('data-template');
            els.certCard.setAttribute('data-template', template);
        });
    }

    // ============== 4. 保存卡片（html2canvas 方式，此处用 Canvas 重绘） ==============
    function initSaveCard() {
        if (!els.saveCardBtn) return;

        els.saveCardBtn.addEventListener('click', function () {
            // 生成高分辨率卡片图片
            var canvas = document.createElement('canvas');
            var W = 1080;
            var H = 1620; // 3:4.5 竖版
            canvas.width = W;
            canvas.height = H;
            var ctx = canvas.getContext('2d');

            // 背景
            var template = els.certCard.getAttribute('data-template') || 'lavender';
            var bgColors = {
                lavender: ['#E8E0F0', '#FAF8FC', '#F5F0FA'],
                ocean: ['#D0E8F0', '#F0F8FA', '#E8F4F8'],
                sunset: ['#FDE8D0', '#FFF8F0', '#FFF4E8']
            };
            var colors = bgColors[template] || bgColors.lavender;
            var bgGrad = ctx.createLinearGradient(0, 0, W, H);
            bgGrad.addColorStop(0, colors[0]);
            bgGrad.addColorStop(0.5, colors[1]);
            bgGrad.addColorStop(1, colors[2]);
            ctx.fillStyle = bgGrad;
            ctx.fillRect(0, 0, W, H);

            // 圆角遮罩
            ctx.save();
            ctx.beginPath();
            var radius = 80;
            ctx.moveTo(radius, 0);
            ctx.arcTo(W, 0, W, H, radius);
            ctx.arcTo(W, H, 0, H, radius);
            ctx.arcTo(0, H, 0, 0, radius);
            ctx.arcTo(0, 0, W, 0, radius);
            ctx.closePath();
            ctx.clip();
            ctx.restore();

            // 缎带
            var ribbonColors = {
                lavender: '#9B7ED8',
                ocean: '#4A6FA5',
                sunset: '#E0A93A'
            };
            ctx.fillStyle = ribbonColors[template] || ribbonColors.lavender;
            ctx.fillRect(W / 2 - 60, 0, 50, 80);
            ctx.fillStyle = '#7DD3C0';
            ctx.fillRect(W / 2 + 10, 0, 50, 80);

            // 标题
            ctx.fillStyle = '#2D2D3A';
            ctx.font = '700 42px "Nunito", "PingFang SC", sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('我的人格认证卡', W / 2, 160);

            // 已认证徽章
            ctx.fillStyle = '#F5D547';
            ctx.font = '700 24px "Nunito", sans-serif';
            ctx.fillText('✓ 已认证', W / 2, 210);

            // 人格编码
            ctx.font = '600 110px "Montserrat", sans-serif';
            ctx.fillStyle = ribbonColors[template] || ribbonColors.lavender;
            ctx.fillText(resultData.code, W / 2, 360);

            // 口号
            ctx.font = '400 36px "Nunito", "PingFang SC", sans-serif';
            ctx.fillStyle = '#636e72';
            ctx.fillText(resultData.slogan, W / 2, 430);

            // 分割线
            ctx.strokeStyle = 'rgba(155, 126, 216, 0.2)';
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(100, 500);
            ctx.lineTo(W - 100, 500);
            ctx.stroke();

            // 信息区
            ctx.textAlign = 'left';
            ctx.font = '400 28px "Inter", "PingFang SC", sans-serif';
            ctx.fillStyle = '#9B9BAB';
            ctx.fillText('人格稀有度', 120, 580);
            ctx.font = '700 48px "Montserrat", sans-serif';
            ctx.fillStyle = '#2D2D3A';
            ctx.fillText(resultData.rarity, 120, 640);

            ctx.font = '400 28px "Inter", "PingFang SC", sans-serif';
            ctx.fillStyle = '#9B9BAB';
            ctx.fillText('相同人格名人', 120, 730);
            ctx.font = '600 32px "Inter", "PingFang SC", sans-serif';
            ctx.fillStyle = '#2D2D3A';
            ctx.fillText(resultData.famousPeople, 120, 780);

            ctx.font = '400 28px "Inter", "PingFang SC", sans-serif';
            ctx.fillStyle = '#9B9BAB';
            ctx.fillText('最佳搭子', 120, 870);
            ctx.font = '600 28px "Montserrat", sans-serif';
            ctx.fillStyle = '#fff';
            resultData.bestPartners.forEach(function (partner, idx) {
                ctx.fillStyle = ribbonColors[template] || ribbonColors.lavender;
                ctx.beginPath();
                ctx.roundRect(120 + idx * 160, 900, 140, 50, 25);
                ctx.fill();
                ctx.fillStyle = '#fff';
                ctx.textAlign = 'center';
                ctx.fillText(partner, 120 + idx * 160 + 70, 932);
                ctx.textAlign = 'left';
            });

            // 昵称
            var nickname = els.nicknameInput ? els.nicknameInput.value.trim() : '匿名用户001';
            ctx.font = '400 30px "Nunito", "PingFang SC", sans-serif';
            ctx.fillStyle = '#636e72';
            ctx.textAlign = 'left';
            ctx.fillText(nickname, 120, 1050);

            // 底部信息
            ctx.font = '400 22px "Inter", "PingFang SC", sans-serif';
            ctx.fillStyle = '#9B9BAB';
            ctx.fillText('扫描二维码查看完整报告', 120, 1500);

            // 下载
            var link = document.createElement('a');
            link.download = 'CareerTest-' + resultData.code + '-' + nickname + '.png';
            link.href = canvas.toDataURL('image/png');
            link.click();

            // 埋点
            trackEvent('card_save', { template: template, code: resultData.code });
        });
    }

    // ============== 5. 分享按钮埋点 ==============
    function initShare() {
        if (!els.shareBtns.length) return;

        els.shareBtns.forEach(function (btn) {
            btn.addEventListener('click', function () {
                var channel = btn.getAttribute('data-channel');

                // 埋点追踪
                trackEvent('share_click', {
                    channel: channel,
                    code: resultData.code
                });

                // 微信 SDK 调起（模拟）
                if (channel === 'wechat_friend' || channel === 'wechat_moments') {
                    if (typeof wx !== 'undefined' && wx.miniProgram) {
                        // 微信环境内调用 SDK
                        console.log('[Share] WeChat SDK:', channel);
                    } else {
                        // 非微信环境提示
                        showToast('请在微信中打开以分享给好友');
                    }
                } else if (channel === 'weibo') {
                    var shareUrl = encodeURIComponent(window.location.href);
                    var shareText = encodeURIComponent('我的职业人格类型是 ' + resultData.code + ' ' + resultData.title + '！来测测你的吧～');
                    window.open('https://service.weibo.com/share/share.php?url=' + shareUrl + '&title=' + shareText, '_blank');
                }
            });
        });
    }

    // ============== 工具函数 ==============
    function trackEvent(eventName, data) {
        console.log('[Track]', eventName, data);
        // 后端接入后替换为真实埋点 API
        // fetch('/api/stats/track/', { method: 'POST', body: JSON.stringify({ event: eventName, ...data }) });
    }

    function showToast(message) {
        var toast = document.createElement('div');
        toast.style.cssText = 'position:fixed;bottom:30%;left:50%;transform:translateX(-50%);background:rgba(0,0,0,0.75);color:#fff;padding:12px 24px;border-radius:24px;font-size:14px;z-index:9999;pointer-events:none;animation:fadeInUp 0.3s ease;';
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
        drawRadar();
        initNicknameSync();
        initTemplateSwitch();
        initSaveCard();
        initShare();

        // 页面加载埋点
        trackEvent('result_page_view', { code: resultData.code });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
